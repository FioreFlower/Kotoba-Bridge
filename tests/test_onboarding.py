import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from core import Region,ReaderError
from onboarding import region_from_drag,load_settings,save_settings,inspect_engine

class SetupTests(unittest.TestCase):
    def test_drag_maps_negative_monitor_and_reverse(self):
        m={'left':-1920,'top':0,'width':1920,'height':1080}
        self.assertEqual(region_from_drag((900,500),(100,400),(960,540),m),Region(-1720,800,1600,200))
    def test_drag_clamps_and_small_rejected(self):
        m={'left':0,'top':0,'width':1000,'height':600}
        self.assertEqual(region_from_drag((-10,-10),(600,400),(500,300),m),Region(0,0,1000,600))
        with self.assertRaises(ReaderError):region_from_drag((1,1),(2,2),(500,300),m)
    def test_settings_allowlist(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'settings.json';save_settings(p,Region(-10,0,400,100),'日本語/path')
            data=json.loads(p.read_text(encoding='utf-8'))
            self.assertEqual(set(data),{'version','region','tesseract'})
            region,engine=load_settings(p)
            self.assertEqual(region,Region(-10,0,400,100));self.assertEqual(engine,'日本語/path')
            data['key']='not-a-real-key';p.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ReaderError):load_settings(p)
    def test_settings_invalid_numeric_type(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'settings.json'
            p.write_text(json.dumps({'version':1,'tesseract':'','region':{'left':True,'top':0,'width':100,'height':100}}),encoding='utf-8')
            with self.assertRaises(ReaderError):load_settings(p)
    def test_engine_missing_model(self):
        with patch('onboarding.find_tesseract',return_value='/mock/ocr'),patch('onboarding.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=b'eng\nosd\n')):
            self.assertFalse(inspect_engine()['ok'])
    def test_engine_jpn_detected(self):
        with patch('onboarding.find_tesseract',return_value='/mock/ocr'),patch('onboarding.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=b'langs\neng\njpn\n')):
            self.assertTrue(inspect_engine()['ok'])
    def test_preview_uses_only_local_ocr(self):
        from app import ocr_region
        class Bridge:
            def __init__(self):self.calls=[]
            def call(self,method,**kw):self.calls.append((method,kw));return {'text':'こんにちは。'}
        b=Bridge()
        with patch('app.find_tesseract',return_value='/mock/ocr'),patch('app.capture_region',return_value='image-bytes'):
            self.assertEqual(ocr_region(Region(0,0,100,100),b),'こんにちは。')
        self.assertEqual([c[0] for c in b.calls],['ocr'])
        self.assertEqual(b.calls[0][1]['scope'],'0,0,100,100')
