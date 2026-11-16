import hashlib, io, tempfile, threading, unittest, zipfile
from pathlib import Path
from unittest.mock import Mock, patch
import local_runtime as r
from core import ReaderError

class RuntimeTests(unittest.TestCase):
    def test_no_consent_no_network(self):
        with patch('urllib.request.build_opener') as net:
            with self.assertRaises(ReaderError): r.install_runtime()
            net.assert_not_called()

    def fixture(self, names=('llama-server.exe',)):
        blob=io.BytesIO()
        with zipfile.ZipFile(blob,'w') as z:
            for name in names:z.writestr(name,b'synthetic')
        data=blob.getvalue()
        files={name:dict(bytes=9,sha256=hashlib.sha256(b'synthetic').hexdigest()) for name in names}
        return data, files

    def test_verify_extract_and_tamper(self):
        data,files=self.fixture()
        with tempfile.TemporaryDirectory() as d,patch.multiple(r,ARCHIVE_BYTES=len(data),ARCHIVE_SHA256=hashlib.sha256(data).hexdigest(),FILES=files):
            archive=Path(d)/'x.zip';archive.write_bytes(data);target=Path(d)/'installed'
            r.unpack_verified(archive,target);self.assertTrue(r.verify_runtime(target))
            (target/'llama-server.exe').write_bytes(b'corrupted')
            self.assertFalse(r.verify_runtime(target))
            with self.assertRaises(ReaderError):r.unpack_verified(archive,target)

    def test_traversal_refused_and_cleaned(self):
        data,files=self.fixture(('../outside',))
        with tempfile.TemporaryDirectory() as d,patch.multiple(r,ARCHIVE_BYTES=len(data),ARCHIVE_SHA256=hashlib.sha256(data).hexdigest(),FILES=files):
            archive=Path(d)/'x.zip';archive.write_bytes(data);target=Path(d)/'installed'
            with self.assertRaises(ReaderError):r.unpack_verified(archive,target)
            self.assertFalse(target.exists());self.assertFalse((Path(d)/'outside').exists())

    def test_corrupt_archive_and_cancel_no_target(self):
        data,files=self.fixture()
        with tempfile.TemporaryDirectory() as d,patch.multiple(r,ARCHIVE_BYTES=len(data),ARCHIVE_SHA256=hashlib.sha256(data).hexdigest(),FILES=files):
            archive=Path(d)/'x.zip';archive.write_bytes(data);target=Path(d)/'installed'
            event=threading.Event();event.set()
            with self.assertRaises(ReaderError):r.unpack_verified(archive,target,event)
            self.assertFalse(target.exists())
            archive.write_bytes(b'corrupt')
            with self.assertRaises(ReaderError):r.unpack_verified(archive,target)
            self.assertFalse(target.exists())

    def test_download_install_and_existing_tamper_never_executes(self):
        data,files=self.fixture()
        with tempfile.TemporaryDirectory() as d,patch.multiple(r,ARCHIVE_BYTES=len(data),ARCHIVE_SHA256=hashlib.sha256(data).hexdigest(),FILES=files),patch.object(r,'runtime_path',return_value=Path(d)/'runtime'),patch('subprocess.Popen') as execute:
            def response(*a,**k):
                f=io.BytesIO(data);f.status=200;f.headers={};return f
            opener=Mock();opener.open.side_effect=response
            with patch('urllib.request.build_opener',return_value=opener):
                target=r.install_runtime(accepted=True);self.assertTrue(r.verify_runtime(target))
                self.assertEqual(r.install_runtime(accepted=True),target);self.assertEqual(opener.open.call_count,1)
                (target/'unexpected.dll').write_bytes(b'bad')
                with self.assertRaises(ReaderError):r.install_runtime(accepted=True)
            execute.assert_not_called()
            self.assertEqual([p.name for p in Path(d).iterdir()],['runtime'])

    def test_symlink_destination_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);outside=root/'outside';outside.mkdir();link=root/'link'
            try:link.symlink_to(outside,target_is_directory=True)
            except OSError:self.skipTest('symlink permission unavailable')
            with patch.object(r,'runtime_path',return_value=link/'runtime'):
                with self.assertRaises(ReaderError):r.install_runtime(accepted=True)
            self.assertEqual(list(outside.iterdir()),[])
