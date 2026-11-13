import unittest
from pathlib import Path
from bridge import GoBridge, GoTranslator, GoStable
from core import ReaderError

@unittest.skipUnless((Path(__file__).resolve().parents[1]/'kotoba-core').is_file() or (Path(__file__).resolve().parents[1]/'kotoba-core.exe').is_file(),'Build Go core to run IPC integration')
class BridgeTests(unittest.TestCase):
    def setUp(self):self.bridge=GoBridge()
    def tearDown(self):self.bridge.close()
    def test_demo_roundtrip(self):
        self.bridge.call('configure',demo=True)
        translator=GoTranslator(self.bridge)
        self.assertEqual(translator.translate('こんにちは。'),'안녕하세요.')
        self.assertEqual(translator.budget.calls,1)
        self.bridge.call('clear')
        self.assertEqual(self.bridge.call('status')['calls'],1)
    def test_configure_preserves_budget(self):
        self.bridge.call('configure',demo=True)
        self.bridge.call('translate',text='こんにちは。')
        self.bridge.call('configure',demo=True)
        self.assertEqual(self.bridge.call('status')['calls'],1)
    def test_missing_live_key(self):
        with self.assertRaises(ReaderError):self.bridge.call('configure',demo=False,key='')
    def test_bad_ocr_payload(self):
        with self.assertRaises(ReaderError):self.bridge.call('ocr',image='not a PNG',tesseract='missing')
    def test_death_fails_closed(self):
        self.bridge.process.terminate();self.bridge.process.wait(timeout=5)
        with self.assertRaises(ReaderError):self.bridge.call('status')
