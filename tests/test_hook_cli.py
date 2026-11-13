import io
import os
import queue
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from hook_cli import command,parse_line,verify_cli,CliSession,MAX_LINE
from hook_processes import ProcessIdentity,identity
from core import ReaderError

class HookCliTests(unittest.TestCase):
 def test_commands_have_fixed_verbs_and_integer_pid(self):
  self.assertEqual(command('attach',123),'attach -P123\n')
  for verb,pid in [('shell',1),('attach','1\ndetach -P2'),('attach',True),('detach',0)]:
   with self.assertRaises(ReaderError):command(verb,pid)
 def test_native_hex_pid_candidates_and_console_filter(self):
  line='[A:7B:1234:0:0:TextOutW:HW0@1234] 明日、また会おう。\r\n'
  self.assertEqual(parse_line(line,123),('10_4660','明日、また会おう。'))
  self.assertIsNone(parse_line(line,124));self.assertIsNone(parse_line('[0:0:0:0:0:Console:] secret',123))
  self.assertIsNone(parse_line('continuation without metadata',123))
 def test_oversized_output_rejected(self):
  with self.assertRaises(ReaderError):parse_line('x'*(MAX_LINE+1),123)
 def test_unknown_engine_never_runs(self):
  with tempfile.TemporaryDirectory() as d:
   for name in ('TextractorCLI.exe','texthook.dll'):Path(d,name).write_bytes(b'unknown')
   with self.assertRaises(ReaderError):verify_cli(Path(d),'x64')
 def test_no_consent_never_launches(self):
  with patch('hook_cli.sys.platform','win32'),patch('hook_cli.subprocess.Popen') as run:
   with self.assertRaises(ReaderError):CliSession().connect('unused',None,None)
   run.assert_not_called()
 def test_pid_reuse_blocks_launch(self):
  a=ProcessIdentity(123,1,'game.exe','x64');b=ProcessIdentity(123,2,'game.exe','x64')
  with patch('hook_cli.sys.platform','win32'),patch('hook_cli.verify_cli',return_value=Path('/fake/CLI.exe')),patch('hook_cli.subprocess.Popen') as run:
   with self.assertRaises(ReaderError):CliSession().connect('/fake',a,lambda _:b,True)
   run.assert_not_called()
 def test_bounded_preview_and_process_exit(self):
  c=CliSession();c.process=Mock();c.target=ProcessIdentity(123,1,'game.exe','x64');c.identity=lambda _:c.target
  c.started=time.monotonic();c.received=False;c.candidates.start(True)
  c.events.put(('a','明日、また会おう。'));self.assertTrue(c.drain());self.assertEqual(len(c.candidates.candidates),1)
  c.identity=lambda _:None
  with self.assertRaises(ReaderError):c.drain()
 def test_reader_overflow_is_failure_without_unbounded_queue(self):
  c=CliSession();c.target=ProcessIdentity(123,1,'game.exe','x64')
  c.process=Mock(stdout=io.StringIO('[A:7B:1234:0:0:T:H] 明日。\n'*100))
  c._read();self.assertIsNotNone(c.failure);self.assertLessEqual(c.events.qsize(),64)
 def test_close_sends_only_detach_to_owned_pid_and_clears(self):
  c=CliSession();c.target=ProcessIdentity(123,1,'game.exe','x64');p=Mock();p.poll.return_value=None;c.process=p
  c.candidates.start(True);c.candidates.ingest(c.candidates.generation,'a','明日。')
  message=c.close();p.stdin.write.assert_called_once_with('detach -P123\n');self.assertIsNone(c.process)
  self.assertFalse(c.candidates.active);self.assertIn('확인할 수 없습니다',message)
 def test_confirmation_rechecks_candidate_after_dialog(self):
  c=CliSession();c.drain=Mock();token=c.candidates.start(True)
  c.candidates.ingest(token,'a','明日。');c.candidates.select('a')
  self.assertEqual(c.confirmed_text('a','明日。'),'明日。')
  c.candidates.ingest(token,'a','今日は。')
  with self.assertRaises(ReaderError):c.confirmed_text('a','明日。')

 @unittest.skipUnless(os.name=='nt','Windows process APIs')
 def test_current_process_identity_is_stable(self):
  a=identity(os.getpid());self.assertEqual(identity(os.getpid()),a);self.assertIn(a.arch,('x64','x86'))
