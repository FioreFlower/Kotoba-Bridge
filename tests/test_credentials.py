import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
from credentials import KeyStore,DPAPI,remove_legacy_keys,MAGIC
from core import ReaderError,Region
from onboarding import save_settings,load_settings

class FakeProtection:
    """Opaque test double; no claim of encryption on Linux."""
    def __init__(self):self.payloads={}
    def protect(self,data):
        token=os.urandom(32);self.payloads[token]=data;return token
    def unprotect(self,data):
        if data not in self.payloads:raise ReaderError('TEST decryption failed')
        return self.payloads[data]

class KeyStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'deepl-key.dpapi'
        self.protection=FakeProtection();self.store=KeyStore(self.path,self.protection)
    def tearDown(self):self.tmp.cleanup()
    def test_save_reload_replace_delete(self):
        self.store.save('synthetic-fixture-one',False)
        self.assertNotIn(b'synthetic-fixture-one',self.path.read_bytes())
        self.assertEqual(KeyStore(self.path,self.protection).load(),('synthetic-fixture-one',False))
        self.store.save('synthetic-fixture-two',True)
        self.assertEqual(self.store.load(),('synthetic-fixture-two',True))
        self.store.delete();self.store.delete();self.assertIsNone(self.store.load())
    def test_failed_encrypt_never_writes(self):
        self.protection.protect=Mock(side_effect=ReaderError('failed'))
        with self.assertRaises(ReaderError):self.store.save('synthetic-fixture')
        self.assertEqual(list(self.path.parent.iterdir()),[])
    def test_atomic_replace_failure_preserves_old(self):
        self.store.save('synthetic-old');old=self.path.read_bytes()
        with patch('credentials.os.replace',side_effect=OSError('private detail')):
            with self.assertRaises(ReaderError) as caught:self.store.save('synthetic-new')
        self.assertNotIn('private detail',str(caught.exception))
        self.assertEqual(self.path.read_bytes(),old)
        self.assertEqual(list(self.path.parent.iterdir()),[self.path])
    def test_delete_failure_does_not_claim_success(self):
        self.store.save('synthetic-key')
        with patch('credentials.Path.unlink',side_effect=PermissionError('private')):
            with self.assertRaisesRegex(ReaderError,'남아'):self.store.delete()
        self.assertTrue(self.path.exists())
    def test_corrupt_plaintext_and_oversized_rejected(self):
        for raw in [b'{"key":"synthetic-private-value"}',MAGIC+b'broken',b'x'*32769]:
            self.path.write_bytes(raw)
            with self.assertRaises(ReaderError) as caught:self.store.load()
            self.assertNotIn('synthetic-private-value',str(caught.exception))
    def test_invalid_key_never_written(self):
        for key in ['', 'x\ny', 'a'*4097, '日本語']:
            with self.assertRaises(ReaderError):self.store.save(key)
        self.assertFalse(self.path.exists())
    @unittest.skipIf(sys.platform=='win32','Non-Windows fail-closed check')
    def test_no_plaintext_fallback(self):
        with self.assertRaises(ReaderError):KeyStore(self.path).save('synthetic-key')
        self.assertFalse(self.path.exists())
    def test_legacy_removed_without_import_or_backup(self):
        p=self.path.parent/'settings.json';save_settings(p,Region(0,0,100,100),'engine')
        value=json.loads(p.read_text(encoding='utf-8'));value['api_key']='synthetic-legacy-key'
        p.write_text(json.dumps(value),encoding='utf-8')
        self.assertTrue(remove_legacy_keys(p));self.assertFalse(remove_legacy_keys(p))
        self.assertNotIn('synthetic-legacy-key',p.read_text(encoding='utf-8'))
        self.assertEqual(load_settings(p)[1],'engine');self.assertEqual(list(p.parent.iterdir()),[p])
    def test_legacy_cleanup_failure_preserves_file_and_redacts(self):
        p=self.path.parent/'settings.json';save_settings(p,Region(0,0,100,100),'')
        v=json.loads(p.read_text(encoding='utf-8'));v['key']='synthetic-private-legacy';p.write_text(json.dumps(v),encoding='utf-8')
        before=p.read_bytes()
        with patch('onboarding.os.replace',side_effect=PermissionError('synthetic-private-legacy')):
            with self.assertRaises(ReaderError) as caught:remove_legacy_keys(p)
        self.assertNotIn('synthetic-private-legacy',str(caught.exception));self.assertEqual(p.read_bytes(),before)

@unittest.skipUnless(sys.platform=='win32','Requires real Windows DPAPI')
class NativeDPAPITests(unittest.TestCase):
    def test_native_restart_tamper_and_delete(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'key.dpapi';store=KeyStore(path)
            store.save('synthetic-dpapi-fixture-only',True)
            first=path.read_bytes();self.assertNotIn(b'synthetic-dpapi-fixture-only',first)
            # New Python process, same Windows user, no key in args/env/stdout.
            code="from credentials import KeyStore; import sys; assert KeyStore(sys.argv[1]).load()==('synthetic-dpapi-fixture-only',True)"
            child=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True,timeout=15)
            self.assertEqual(child.returncode,0,'DPAPI child round trip failed')
            self.assertEqual(child.stdout,b'');self.assertEqual(child.stderr,b'')
            store.save('synthetic-dpapi-fixture-only',True);self.assertNotEqual(path.read_bytes(),first)
            broken=bytearray(path.read_bytes());broken[-1]^=1;path.write_bytes(broken)
            with self.assertRaises(ReaderError):store.load()
            store.delete();self.assertFalse(path.exists())

class CredentialFlowTests(unittest.TestCase):
    def app(self):
        from app import App
        a=App.__new__(App);a.key=Mock();a.key.get.return_value='';a.bridge=Mock()
        a.key_store=Mock();a.key_store.load.return_value=('synthetic-saved',False)
        a.credentials_blocked=False
        return a
    def test_reload_never_repopulates_field(self):
        a=self.app();a.configure_credentials(False,False)
        a.bridge.call.assert_called_once_with('configure',key='synthetic-saved',pro=False,demo=False)
        a.key.insert.assert_not_called();a.key.delete.assert_called_once()
    def test_demo_does_not_read_saved_or_typed_key(self):
        a=self.app();a.configure_credentials(True,False)
        a.key_store.load.assert_not_called();a.key.get.assert_not_called()
        a.bridge.call.assert_called_once_with('configure',key='',pro=False,demo=True)
    def test_wrong_account_kind_no_ipc(self):
        a=self.app()
        with self.assertRaises(ReaderError):a.configure_credentials(False,True)
        a.bridge.call.assert_not_called()
    def test_blocked_legacy_no_ipc(self):
        a=self.app();a.credentials_blocked=True
        with self.assertRaises(ReaderError):a.configure_credentials(False,False)
        a.bridge.call.assert_not_called();a.key_store.load.assert_not_called()
    def test_load_failure_no_ipc(self):
        a=self.app();a.key_store.load.side_effect=ReaderError('failed')
        with self.assertRaises(ReaderError):a.configure_credentials(False,False)
        a.bridge.call.assert_not_called()

    def test_failed_core_clear_does_not_auto_restart_budget(self):
        a=self.app();a.pause=Mock();a.busy=False;a.pro=Mock();a.pro.get.return_value=False
        a.status=Mock();a.key_state=Mock();a.bridge.call.side_effect=ReaderError('dead')
        original=a.bridge
        with patch('app.remove_legacy_keys',return_value=False):a.save_key()
        self.assertIs(a.bridge,original);original.close.assert_called_once()
        self.assertIn('재실행',a.status.set.call_args.args[0])

    def test_existing_live_provider_reuses_key_without_decrypt_or_ipc_secret(self):
        a=self.app();a.mode=(False,False);a.translator=Mock()
        a.configure_credentials(False,False)
        a.key_store.load.assert_not_called()
        a.bridge.call.assert_called_once_with('configure',key='',pro=False,demo=False)
