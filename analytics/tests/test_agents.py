import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agents.rag import answer
from agents.foundry import run

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
