import hashlib,io,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch,Mock
import local_models as m
from core import ReaderError
class ModelsTests(unittest.TestCase):
 def test_consent_before_network(self):
  with patch('urllib.request.build_opener') as net:
   with self.assertRaises(ReaderError):m.install_model()
   net.assert_not_called()
 def test_pinned_catalog(self):
  self.assertEqual(len(m.MODELS),2)
  for item in m.MODELS.values():
   self.assertEqual(len(item['sha256']),64);self.assertEqual(len(item['revision']),40)
 def test_install_verify_corruption_cancel(self):
  data=b'GGUF synthetic';item=dict(m.MODELS['qwen25-1.5b'],bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
  with tempfile.TemporaryDirectory() as d,patch.dict(m.MODELS,{'qwen25-1.5b':item}):
   target=Path(d)/'model.gguf'
   def response():
    f=io.BytesIO(data);f.status=200;f.headers={};return f
   opener=Mock();opener.open.side_effect=lambda *a,**k:response()
   with patch('urllib.request.build_opener',return_value=opener):
    m.install_model(accepted=True,destination=target);self.assertTrue(m.verify_model(target))
    target.unlink();event=threading.Event();event.set()
    with self.assertRaises(ReaderError):m.install_model(accepted=True,destination=target,cancel=event)
    self.assertEqual(list(Path(d).iterdir()),[])
    target.write_bytes(b'bad')
    with self.assertRaises(ReaderError):m.install_model(accepted=True,destination=target)
    self.assertEqual(target.read_bytes(),b'bad')
 def test_delete_only_known_model_install_and_portable_roots(self):
  for kind in ['installed','portable']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d,patch('local_models.data_folder',return_value=Path(d)/kind):
    p=m.model_path();p.parent.mkdir(parents=True);p.write_bytes(b'fixture');key=p.parent.parent/'deepl-key.dpapi';key.write_bytes(b'ciphertext')
    with self.assertRaises(ReaderError):m.delete_model('qwen25-1.5b',in_use=True)
    self.assertTrue(p.exists());m.delete_model('qwen25-1.5b');self.assertFalse(p.exists());self.assertTrue(key.exists())
    with self.assertRaises(ReaderError):m.delete_model('../other')
 def test_symlink_never_follows(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);outside=root/'outside';outside.mkdir();link=root/'link'
   try:link.symlink_to(outside,target_is_directory=True)
   except OSError:self.skipTest('symlink permission unavailable')
   with patch('local_models.data_folder',return_value=link):
    with self.assertRaises(ReaderError):m.delete_model('qwen25-1.5b')
 def test_local_never_reads_cloud_key(self):
  from app import App
  a=App.__new__(App);a.provider=Mock();a.provider.get.return_value='로컬 llama.cpp';a.local_consent=Mock();a.local_consent.get.return_value=True
  a.local_port=Mock();a.local_port.get.return_value='8087';a.local_model=Mock();a.local_model.get.return_value='kotoba-local';a.bridge=Mock();a.key_store=Mock();a.key=Mock();a.credentials_blocked=True
  a.configure_credentials(False,False);a.key_store.load.assert_not_called();a.key.get.assert_not_called()
  self.assertEqual(a.bridge.call.call_args.kwargs['key'],'')

 def test_uninstall_manager_close_exits_hidden_app(self):
  from local_ui import LocalWindow
  window=LocalWindow.__new__(LocalWindow);window.cancel=Mock();window.window=Mock();window.app=Mock()
  window.app.manage_models_only=True;window.app.local_window=window
  window.close()
  window.cancel.set.assert_called_once();window.window.destroy.assert_called_once()
  window.app.close.assert_called_once();self.assertIsNone(window.app.local_window)
  self.assertFalse(window.app.manage_models_only)

 def test_locked_model_delete_reports_failure_and_preserves_cards(self):
  with tempfile.TemporaryDirectory() as d,patch('local_models.data_folder',return_value=Path(d)):
   p=m.model_path();p.parent.mkdir();p.write_bytes(b'model')
   card=Path(d)/'cards.json';card.write_text('[]')
   with patch.object(Path,'unlink',side_effect=PermissionError()):
    with self.assertRaises(ReaderError):m.delete_model('qwen25-1.5b')
   self.assertTrue(p.exists());self.assertEqual(card.read_text(),'[]')

 def test_listening_server_blocks_deletion_gate(self):
  import socket
  server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1)
  try:self.assertTrue(m.local_server_present(server.getsockname()[1]))
  finally:server.close()
  self.assertTrue(m.local_server_present('invalid'))
