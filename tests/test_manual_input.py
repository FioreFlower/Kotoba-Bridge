import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from app import App
from core import ReaderError

class ManualInputTests(unittest.TestCase):
    def app(self,consent=True):
        a=App.__new__(App);a.busy=False;a.running=False;a.generation=0
        a.stop_event=threading.Event();a.results=queue.Queue();a.bridge=Mock()
        a.bridge.call.return_value={};a.consent=Mock();a.consent.get.return_value=consent
        a.key=Mock();a.key.get.return_value='test-only-key';a.pro=Mock();a.pro.get.return_value=False
        a.status=Mock();a.translator=None
        return a
    def test_no_consent_never_calls_core(self):
        a=self.app(False)
        with self.assertRaises(ReaderError):a.translate_input('こんにちは。')
        a.bridge.call.assert_not_called()
    def test_busy_never_calls_core(self):
        a=self.app();a.busy=True
        with self.assertRaises(ReaderError):a.translate_input('こんにちは。')
        a.bridge.call.assert_not_called()
    def run_now(self,**kwargs):
        return SimpleNamespace(start=kwargs['target'])
    def test_exact_reviewed_text_once_no_capture(self):
        a=self.app();translator=Mock();translator.translate.return_value='안녕하세요.'
        with patch('app.GoTranslator',return_value=translator),patch('app.threading.Thread',side_effect=self.run_now),patch('app.ocr_region') as capture:
            a.translate_input('こんにちは。')
        capture.assert_not_called();translator.translate.assert_called_once_with('こんにちは。')
        self.assertEqual(a.results.get()[1: ],('text','こんにちは。\n\n안녕하세요.'))
        self.assertEqual(a.results.get()[1],'done')
        self.assertFalse(a.running)
        self.assertEqual([c.args[0] for c in a.bridge.call.call_args_list],['configure','clear'])
    def test_stop_during_request_discards_response(self):
        a=self.app();translator=Mock()
        def reply(_):a.pause();return 'late'
        translator.translate.side_effect=reply
        with patch('app.GoTranslator',return_value=translator),patch('app.threading.Thread',side_effect=self.run_now):a.translate_input('こんにちは。')
        self.assertEqual(a.results.qsize(),1);self.assertEqual(a.results.get()[1],'done')
    def test_failure_no_retry(self):
        a=self.app();translator=Mock();translator.translate.side_effect=ReaderError('failure')
        with patch('app.GoTranslator',return_value=translator),patch('app.threading.Thread',side_effect=self.run_now):a.translate_input('こんにちは。')
        self.assertEqual(translator.translate.call_count,1)
        self.assertEqual(a.results.get()[1],'error')

    def test_source_switch_clears_manual_context_without_reconfigure(self):
        a=self.app();a.manual_context=True
        a.reset_manual_context()
        a.bridge.call.assert_called_once_with('clear')
        self.assertFalse(a.manual_context)
        a.reset_manual_context()
        self.assertEqual(a.bridge.call.call_count,1)
    def test_failed_source_clear_keeps_boundary_closed(self):
        a=self.app();a.manual_context=True;a.bridge.call.side_effect=ReaderError('closed')
        with self.assertRaises(ReaderError):a.reset_manual_context()
        self.assertTrue(a.manual_context)
