import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from app import App,CaptureTarget,check_target
from core import Region,ReaderError

class GuardTests(unittest.TestCase):
 def make_app(self):
  a=App.__new__(App);a.generation=5;a.root=Mock();a.subtitle=Mock();a.subtitle.mode.return_value=True
  a.status=Mock();a.busy=True;a.running=False;a.pause=Mock();return a
 def test_wait_for_foreground_without_capture_or_translate(self):
  a=self.make_app();target=CaptureTarget(17,22,(0,0,500,500))
  with patch('app.time.monotonic',return_value=0),patch('app.target_window',return_value=target),patch('app.check_target',side_effect=ReaderError('focus')),patch('app.ocr_region') as capture:
   a.arm_game(5,Region(20,20,100,100),15)
   capture.assert_not_called();a.subtitle.mode.assert_not_called();self.assertFalse(a.running)
   a.root.after.assert_called_once()
 def test_bound_candidate_never_reselected_after_focus_loss(self):
  a=self.make_app();target=CaptureTarget(17,22,(0,0,500,500))
  with patch('app.time.monotonic',return_value=2),patch('app.target_window') as resolve,patch('app.check_target',side_effect=ReaderError('focus')):
   a.arm_game(5,Region(20,20,100,100),15,target,True,1)
   resolve.assert_not_called();self.assertFalse(a.running)
 def test_stable_target_arms_without_capturing(self):
  a=self.make_app();target=CaptureTarget(17,22,(0,0,500,500))
  with patch('app.time.monotonic',return_value=2),patch('app.check_target'),patch('app.ocr_region') as capture:
   a.arm_game(5,Region(20,20,100,100),15,target,True,1)
   self.assertTrue(a.running);self.assertEqual(a.target,target);self.assertFalse(a.busy);capture.assert_not_called()
 def test_timeout_and_stale_generation_never_start(self):
  for generation,now in [(5,16),(4,0)]:
   a=self.make_app()
   with patch('app.time.monotonic',return_value=now),patch('app.target_window') as resolve:
    a.arm_game(generation,Region(20,20,100,100),15)
    self.assertFalse(a.running);self.assertFalse(a.busy);resolve.assert_not_called()
 def test_geometry_or_pid_change_is_blocked(self):
  target=CaptureTarget(17,22,(0,0,500,500));api=Mock();api.GetForegroundWindow.return_value=17
  for changed in [CaptureTarget(17,22,(1,0,501,500)),CaptureTarget(17,23,(0,0,500,500))]:
   with patch('app.foreground_handle',return_value=17),patch('app.target_window',return_value=changed):
    with self.assertRaises(ReaderError):check_target(target,Region(20,20,100,100))
 def test_play_style_is_set_before_showing_window(self):
  from study_ui import Subtitle
  sub=Subtitle.__new__(Subtitle);sub.window=Mock();sub.background=None;sub._queue_sync=Mock();order=[]
  sub.window.deiconify.side_effect=lambda:order.append('show')
  def style(*args):order.append('style');return True
  with patch('study_ui.sys.platform','win32'),patch('study_ui.click_through',side_effect=style):self.assertTrue(sub.mode(False))
  self.assertEqual(order[:2],['style','show'])

class StopAccessTests(unittest.TestCase):
 def app(self):
  import threading
  a=App.__new__(App);a.root=Mock();a.root.state.return_value='normal'
  a.running=True;a.arming=False;a.mode=(False,False);a.generation=7
  a.stop_event=threading.Event();a.status=Mock();a.start=Mock()
  return a
 def test_restoring_controls_stops_and_does_not_reminimize(self):
  a=self.app();a.control_restored(SimpleNamespace(widget=a.root))
  self.assertFalse(a.running);self.assertTrue(a.stop_event.is_set());self.assertEqual(a.generation,8)
  a.root.iconify.assert_not_called();a.start.assert_not_called()
 def test_restoring_during_arming_cancels_wait(self):
  a=self.app();a.running=False;a.arming=True;a.control_restored()
  self.assertFalse(a.arming);self.assertTrue(a.stop_event.is_set())
 def test_child_map_and_iconic_controls_do_not_stop_game(self):
  a=self.app();a.control_restored(SimpleNamespace(widget=Mock()))
  self.assertTrue(a.running)
  a.root.state.return_value='iconic';a.control_restored();self.assertTrue(a.running)
 def test_demo_remains_visible_without_auto_pause(self):
  a=self.app();a.mode=(True,False);a.control_restored();self.assertTrue(a.running)
 def test_stale_environment_callback_cannot_restart_after_stop(self):
  a=self.app();a.pause();a.start_if_current(7);a.start.assert_not_called()
  a.start_if_current(8);a.start.assert_called_once()
