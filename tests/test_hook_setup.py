"""Offline engine folder resolution; synthetic binaries are never executed."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from core import ReaderError
from hook_cli import resolve_cli_folder
from hook_ui import HookWindow

class SetupTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)
  self.digests={'TextractorCLI.exe':hashlib.sha256(b'cli').hexdigest(),'texthook.dll':hashlib.sha256(b'hook').hexdigest()}
  self.pins=patch('hook_cli.PINNED',{'x64':self.digests,'x86':self.digests});self.pins.start();self.addCleanup(self.pins.stop)
  self.dll=patch('hook_cli.DLL_HASHES',{'x64':{'texthook.dll':self.digests['texthook.dll']},'x86':{'texthook.dll':self.digests['texthook.dll']}});self.dll.start();self.addCleanup(self.dll.stop)
 def engine(self,path):
  path.mkdir(exist_ok=True);(path/'TextractorCLI.exe').write_bytes(b'cli');(path/'texthook.dll').write_bytes(b'hook')
 def test_root_resolves_exact_game_arch_without_execution(self):
  self.engine(self.root/'x86');self.engine(self.root/'x64')
  with patch('hook_cli.subprocess.Popen') as launch:
   self.assertEqual(resolve_cli_folder(self.root,'x86'),self.root/'x86')
   self.assertEqual(resolve_cli_folder(self.root,'x64'),self.root/'x64')
   launch.assert_not_called()
 def test_direct_folder_supported(self):
  self.engine(self.root);self.assertEqual(resolve_cli_folder(self.root,'x64'),self.root)
 def test_no_wrong_arch_or_recursive_fallback(self):
  self.engine(self.root/'x86')
  with self.assertRaises(ReaderError):resolve_cli_folder(self.root,'x64')
 def test_tampered_direct_folder_cannot_fall_back(self):
  self.engine(self.root);self.engine(self.root/'x64');(self.root/'TextractorCLI.exe').write_bytes(b'bad')
  with self.assertRaises(ReaderError):resolve_cli_folder(self.root,'x64')
 def test_missing_relative_unknown_and_extra_dll_fail_closed(self):
  for path,arch in [(self.root/'absent','x64'),(Path('relative'),'x64'),(self.root,'arm64')]:
   with self.assertRaises(ReaderError):resolve_cli_folder(path,arch)
  self.engine(self.root);(self.root/'extra.dll').write_bytes(b'unknown')
  with self.assertRaises(ReaderError):resolve_cli_folder(self.root,'x64')
 def test_failed_disconnect_keeps_window_and_owned_client(self):
  w=HookWindow.__new__(HookWindow);w.closed=False;w.app=Mock();w.app.input_window=w
  w.client=Mock();w.client.close.side_effect=ReaderError('종료 미확인')
  w.consent=Mock();w.status=Mock();w.window=Mock()
  self.assertFalse(w.close());self.assertIs(w.app.input_window,w);self.assertFalse(w.closed)
  w.window.destroy.assert_not_called();w.app.pause.assert_called_once()
