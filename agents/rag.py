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

def load_chunks(folder):
    chunks = []
    paths = sorted(path for path in Path(folder).rglob('*') if path.suffix.lower() in {'.md', '.jsonl'})
    for path in paths:
        if path.is_symlink():
            continue
        for passage in passages(path, Path(folder)):
            terms = Counter(tokens(passage['text']))
            keyword_line = next(
                (line.removeprefix('關鍵詞：') for line in passage['text'].splitlines() if line.startswith('關鍵詞：')),
                '',
            )
            terms.update({term: 2 for term in tokens(keyword_line)})
            chunks.append(dict(passage, terms=terms))
    document_frequency = Counter()
    for chunk in chunks:
        document_frequency.update(chunk['terms'].keys())
    return chunks, document_frequency

def retrieve_from_chunks(question, chunks, document_frequency, limit=4):
    query = set(tokens(question)); scored = []
    for chunk in chunks:
        score = sum(
            (1 + math.log(chunk['terms'][term]))
            * math.log(1 + len(chunks) / (1 + document_frequency[term]))
            for term in query
            if term in chunk['terms']
        )
        if score > 0:
            scored.append((score, chunk))
    hits = sorted(scored, key=lambda item: (-item[0], item[1]['source'], item[1]['line']))[:limit]
    return [
        {**{key: value for key, value in chunk.items() if key != 'terms'}, 'score': score}
        for score, chunk in hits
    ]

def retrieve(question, folder, limit=4):
    chunks, document_frequency = load_chunks(folder)
    return retrieve_from_chunks(question, chunks, document_frequency, limit)

def answer(question, folder):
    hits=retrieve(question,folder)
    return {'mode':'local-extractive', 'question':question, 'answer':'以下為文件檢索摘錄，非模型生成答案。' if hits else '找不到足夠文件依據；請補充資料。', 'citations':hits}

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('question'); p.add_argument('--knowledge',default='agents/knowledge'); a=p.parse_args()
    print(json.dumps(answer(a.question,a.knowledge),ensure_ascii=False,indent=2))
