import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agents.rag import answer
from agents.foundry import run
from agents.evaluate_rag import evaluate

class AgentTests(unittest.TestCase):
    def test_cited_retrieval_and_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'policy.md').write_text('胸徑誤差分析 DBH MAE needs manual measurements.', encoding='utf-8')
            result=answer('DBH 誤差',d)
            self.assertEqual(result['citations'][0]['source'],'policy.md')
            self.assertEqual(answer('zzzzzz',d)['citations'],[])
    def test_default_never_cloud(self):
        with patch.dict(os.environ,{'ARBOR_ALLOW_BILLABLE_CLOUD':'NO'}):
            result=run('DBH','agents/knowledge')
            self.assertFalse(result['cloud_called'])
            with self.assertRaises(ValueError): run('DBH','agents/knowledge',True)
    def test_jsonl_knowledge_is_searchable(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'qa.jsonl').write_text(json.dumps({
                'id':'Q-1','category':'RAG','question':'RAG 如何引用資料？',
                'answer':'回答要列出檔名與行號。','keywords':['RAG','引用']
            }, ensure_ascii=False) + '\n', encoding='utf-8')
            result=answer('RAG 引用',d)
            self.assertEqual(result['citations'][0]['source'],'qa.jsonl')
    def test_leave_one_out_rag_evaluation(self):
        with tempfile.TemporaryDirectory() as d:
            rows = [
                {'id':'A-1','category':'胸徑','question':'胸徑怎麼量？','answer':'離地 1.3 公尺。','keywords':['胸徑','1.3公尺']},
                {'id':'A-2','category':'胸徑','question':'DBH 的標準高度？','answer':'標準高度為 1.3 公尺。','keywords':['DBH','1.3公尺']},
            ]
            corpus = Path(d,'qa.jsonl')
            corpus.write_text('\n'.join(json.dumps(row,ensure_ascii=False) for row in rows)+'\n',encoding='utf-8')
            result=evaluate(d,corpus,1)
            self.assertEqual(result['questions'],2)
            self.assertEqual(result['model_called'],False)
