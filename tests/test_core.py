import io
import json
import unittest
import urllib.error
from core import *

class Fake:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {'translations':[{'text':'안녕하세요.'}]}
        self.error = error
        self.request = None
    def open(self, request, timeout):
        self.request, self.timeout = request, timeout
        if self.error: raise self.error
        return io.BytesIO(json.dumps(self.payload).encode())

class Tests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize('  こんにちは。\n  '), 'こんにちは。')
    def test_stability(self):
        s=StableText()
        self.assertIsNone(s.feed('こ',0))
        self.assertIsNone(s.feed('こんにちは。',.5))
        self.assertIsNone(s.feed('こんにちは。',1))
        self.assertEqual(s.feed('こんにちは。',1.5),'こんにちは。')
        self.assertIsNone(s.feed('こんにちは。',9))
    def test_blank_resets(self):
        s=StableText(); s.feed('a',0); s.feed('a',1); s.feed('',2); s.feed('a',3)
        self.assertEqual(s.feed('a',4),'a')
    def test_region(self):
        with self.assertRaises(ReaderError): Region(0,0,0,100)
        self.assertTrue(Region(-100,0,100,100).overlaps(Region(-50,0,100,100)))
        self.assertFalse(Region(0,0,100,100).overlaps(Region(100,0,100,100)))
    def test_budget(self):
        b=Budget(chars=4,calls=2,interval=3); b.reserve('ab',0)
        with self.assertRaises(ReaderError): b.reserve('a',1)
        b.reserve('cd',3)
        with self.assertRaises(ReaderError): b.reserve('x',6)
        self.assertEqual((b.chars,b.calls),(4,2))
    def test_payload(self):
        f=Fake(); d=DeepL('test-not-a-real-key', opener=f)
        self.assertEqual(d.translate('こんにちは。','前の台詞'),'안녕하세요.')
        p=json.loads(f.request.data)
        self.assertEqual(p['source_lang'],'JA'); self.assertEqual(p['target_lang'],'KO')
        self.assertEqual(p['context'],'前の台詞'); self.assertNotIn('image',p)
        self.assertEqual(f.timeout,15)
        self.assertEqual(f.request.full_url,'https://api-free.deepl.com/v2/translate')
    def test_http_errors_redacted(self):
        for status in [403,429,456,500,302]:
            f=Fake(error=urllib.error.HTTPError('secret-url',status,'secret-body',{},None))
            with self.assertRaises(ReaderError) as cm: DeepL('secret-key',opener=f).translate('x','')
            self.assertNotIn('secret',str(cm.exception))
    def test_malformed(self):
        with self.assertRaises(ReaderError): DeepL('test',opener=Fake({'wrong':True})).translate('x','')
    def test_timeout_reserved(self):
        t=Translator(DeepL('test',opener=Fake(error=TimeoutError())))
        with self.assertRaises(ReaderError): t.translate('hello',now=0)
        self.assertEqual((t.budget.calls,t.budget.chars),(1,5))
    def test_context_and_cache(self):
        t=Translator(Demo()); t.translate('こんにちは。',0)
        self.assertEqual(t.history,['こんにちは。'])
        t.history=[]
        self.assertEqual(t.translate('こんにちは。',1),'안녕하세요.')
        self.assertEqual(t.budget.calls,1)
    def test_length(self):
        t=Translator(Demo())
        for text in ['', 'x'*2001]:
            with self.assertRaises(ReaderError): t.translate(text,0)
        self.assertEqual(t.budget.calls,0)
    def test_key_missing(self):
        with self.assertRaises(ReaderError): DeepL(' ')

if __name__=='__main__': unittest.main()
