import unittest
from hook_stream import HookStream
from core import ReaderError
class StreamTests(unittest.TestCase):
 def test_stability_duplicates_and_spacing_preserved(self):
  s=HookStream();s.start('a','猫 と犬',0)
  self.assertIsNone(s.ready(.5,True,False));self.assertEqual(s.ready(.7,True,False),'猫 と犬')
  for t in [1,4,50]:self.assertIsNone(s.ready(t,True,False))
 def test_latest_only_during_slow_request_and_rate_limit(self):
  s=HookStream();s.start('a','最初',0);s.ready(1,True,False)
  s.update('a','二番',1.1);s.update('a','最後',1.2)
  self.assertIsNone(s.ready(2,True,False));self.assertIsNone(s.ready(4,True,True))
  self.assertEqual(s.ready(5,True,False),'最後');self.assertFalse(s.accepts('最初'))
 def test_focus_wait_loss_and_no_auto_resume(self):
  s=HookStream();s.start('a','猫',0);self.assertIsNone(s.ready(2,False,False));s.ready(3,True,False)
  with self.assertRaises(ReaderError):s.ready(4,False,False)
  self.assertIsNone(s.ready(5,True,False));self.assertFalse(s.active)
 def test_timeout_stop_and_candidate_switch(self):
  s=HookStream();s.start('a','猫',0)
  with self.assertRaises(ReaderError):s.ready(16,False,False)
  s.start('a','猫',20)
  with self.assertRaises(ReaderError):s.update('b','犬',21)
  self.assertFalse(s.active);s.stop();self.assertFalse(s.accepts('猫'))

class StreamAppIntegrationTests(unittest.TestCase):
 def test_main_pause_disables_continuous_and_invalidates_response(self):
  import threading
  from unittest.mock import Mock
  from app import App
  a=App.__new__(App);a.input_window=Mock();a.running=True;a.stop_event=threading.Event();a.generation=4;a.status=Mock()
  a.pause();a.input_window.on_app_pause.assert_called_once();self.assertEqual(a.generation,5);self.assertTrue(a.stop_event.is_set())
 def test_internal_candidate_update_invalidates_without_disabling_stream(self):
  import threading
  from unittest.mock import Mock
  from app import App
  a=App.__new__(App);a.input_window=Mock();a.running=False;a.stop_event=threading.Event();a.generation=4;a.status=Mock()
  a.pause(notify_input=False);a.input_window.on_app_pause.assert_not_called();self.assertEqual(a.generation,5)
 def test_obsolete_request_error_still_stops_current_continuous_mode(self):
  import queue,threading
  from unittest.mock import Mock
  from app import App
  a=App.__new__(App);a.root=Mock();a.input_window=Mock();a.running=False;a.stop_event=threading.Event();a.generation=8;a.status=Mock()
  a.results=queue.Queue();a.results.put((7,'hook_error','합성 API 오류'))
  a.poll();a.input_window.on_app_pause.assert_called_once();self.assertEqual(a.generation,9)
 def test_result_requires_current_candidate_and_live_identity(self):
  from unittest.mock import Mock,patch
  from hook_ui import HookWindow
  from hook_cli import CliSession
  from hook_processes import ProcessIdentity
  w=HookWindow.__new__(HookWindow);w.client=CliSession();w.client.drain=Mock();w.stream=HookStream();w.client.target=ProcessIdentity(123,1,'synthetic','x64')
  token=w.client.candidates.start(True);w.client.candidates.ingest(token,'a','最初');w.client.candidates.select('a')
  w.stream.start('a','最初',0);w.stream.ready(1,True,False)
  with patch('hook_ui.identity',return_value=w.client.target),patch('hook_ui.foreground_pid',return_value=123):
   self.assertTrue(w.accept_result('最初'))
   w.client.candidates.ingest(token,'a','最新');self.assertFalse(w.accept_result('最初'))
