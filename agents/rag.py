"""Local extractive retrieval. No network, embeddings service or generated claims."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

def tokens(text):
    # Latin words plus CJK bigrams work without a language model or paid API.
    result = re.findall(r'[a-z0-9_]+', text.lower())
    for segment in re.findall(r'[\u3400-\u9fff]+', text):
        result.extend(segment[i:i+2] for i in range(max(1, len(segment)-1)))
    return result

def passages(path, folder):
    raw = path.read_text(encoding='utf-8')
    digest = hashlib.sha256(raw.encode()).hexdigest()
    if path.suffix.lower() == '.jsonl':
        for index, line in enumerate(raw.splitlines(), 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record.get('question'), str) or not isinstance(record.get('answer'), str):
                continue
            keywords = '、'.join(value for value in record.get('keywords', []) if isinstance(value, str))
            text = '\n'.join(filter(None, [
                f"編號：{record.get('id', '')}",
                f"分類：{record.get('category', '')}",
                f"題目：{record['question']}",
                f"參考答案：{record['answer']}",
                f"關鍵詞：{keywords}" if keywords else '',
            ]))
            yield {'source': str(path.relative_to(folder)), 'line': index, 'sha256': digest, 'text': text}
        return
    lines = raw.splitlines()
    for start in range(0, len(lines), 16):
        passage = '\n'.join(lines[start:start+20])
        if passage.strip():
            yield {'source': str(path.relative_to(folder)), 'line': start+1, 'sha256': digest, 'text': passage}

def retrieve(question, folder, limit=4):
    query = set(tokens(question)); chunks = []
    paths = sorted(path for path in Path(folder).rglob('*') if path.suffix.lower() in {'.md', '.jsonl'})
    for path in paths:
        if path.is_symlink():
            continue
        for passage in passages(path, Path(folder)):
            chunks.append(dict(passage, terms=Counter(tokens(passage['text']))))
    for chunk in chunks:
        chunk['score'] = sum((1+math.log(chunk['terms'][t])) * math.log(1+len(chunks)/(1+sum(t in c['terms'] for c in chunks))) for t in query if t in chunk['terms'])
    hits = sorted((c for c in chunks if c['score'] > 0), key=lambda c: (-c['score'],c['source'],c['line']))[:limit]
    return [{k:v for k,v in c.items() if k != 'terms'} for c in hits]

def answer(question, folder):
    hits=retrieve(question,folder)
    return {'mode':'local-extractive', 'question':question, 'answer':'以下為文件檢索摘錄，非模型生成答案。' if hits else '找不到足夠文件依據；請補充資料。', 'citations':hits}

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('question'); p.add_argument('--knowledge',default='agents/knowledge'); a=p.parse_args()
    print(json.dumps(answer(a.question,a.knowledge),ensure_ascii=False,indent=2))
