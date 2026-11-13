import queue
import threading
import unittest
from unittest.mock import patch
from app import App
from core import Region, Translator, Demo

class Ready:
    def feed(self, text, now): return text

class PipelineTests(unittest.TestCase):
    def app(self):
        app=App.__new__(App)
        app.region=Region(0,0,100,100); app.target=None
        app.results=queue.Queue(); app.stable=Ready()
        return app
    def events(self,app):
        values=[]
        while not app.results.empty(): values.append(app.results.get())
        return values
    def test_changed_frame_discards_late_result(self):
        a=self.app()
        with patch('app.ocr_region',side_effect=['こんにちは。','次の台詞']):
            a.worker(1,False,threading.Event(),Translator(Demo()))
        self.assertEqual([e[1] for e in self.events(a)],['done'])
    def test_same_frame_emits(self):
        a=self.app()
        with patch('app.ocr_region',return_value='こんにちは。'):
            a.worker(2,False,threading.Event(),Translator(Demo()))
        self.assertEqual([e[1] for e in self.events(a)],['text','done'])
    def test_stop_before_capture(self):
        a=self.app(); stop=threading.Event(); stop.set()
        with patch('app.ocr_region') as capture:
            a.worker(1,False,stop,Translator(Demo()))
            capture.assert_not_called()
        self.assertEqual([e[1] for e in self.events(a)],['done'])
    def test_stop_during_request(self):
        a=self.app(); stop=threading.Event()
        class Provider:
            def translate(self,*args): stop.set(); return '결과'
        with patch('app.ocr_region',return_value='こんにちは。'):
            a.worker(1,False,stop,Translator(Provider()))
        self.assertEqual([e[1] for e in self.events(a)],['done'])
    def test_focus_failure_prevents_capture(self):
        from core import ReaderError
        a=self.app()
        with patch('app.check_target',side_effect=ReaderError('포커스 변경')), patch('app.ocr_region') as capture:
            a.worker(1,False,threading.Event(),Translator(Demo()))
            capture.assert_not_called()
        self.assertEqual([e[1] for e in self.events(a)],['error','done'])
