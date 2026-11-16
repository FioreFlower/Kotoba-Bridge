"""Packaging smoke test: no GUI window, capture, key or network. Optional bundled synthetic OCR."""
import importlib
import json
from pathlib import Path
from bridge import GoBridge


def run(report=None,require_ocr=False):
    checks={};bridge=None
    try:
        for name in ['tkinter','PIL','mss']:
            importlib.import_module(name);checks[name]='import_ok'
        bridge=GoBridge();hello=bridge.call('hello')
        checks['core_protocol']=hello['protocol'];checks['core_version']=hello.get('version')
        bridge.call('configure',demo=True)
        result=bridge.call('translate',text='こんにちは。')
        if result.get('text')!='안녕하세요.':raise ValueError('Demo mismatch')
        checks['demo']='ok'
        import sys,tempfile
        if sys.platform=='win32':
            from credentials import KeyStore
            with tempfile.TemporaryDirectory() as temporary:
                store=KeyStore(Path(temporary)/'synthetic.dpapi')
                store.save('synthetic-packaging-fixture-only',False)
                if store.load()!=('synthetic-packaging-fixture-only',False):raise ValueError('DPAPI mismatch')
                store.delete()
                if store.load() is not None:raise ValueError('DPAPI delete failed')
            checks['dpapi_synthetic_roundtrip']='passed'
        if require_ocr:
            from onboarding import application_folder,inspect_engine
            from ocr_fixture import PNG_BASE64,EXPECTED
            from core import normalize
            import hashlib
            folder=application_folder()/'ocr';engine=folder/'tesseract.exe'
            # Bundled-only check: PATH/system installs cannot hide packaging omissions.
            if not engine.is_file() or not (folder/'tessdata'/'jpn.traineddata').is_file():raise ValueError('Bundled OCR missing')
            if not inspect_engine(str(engine))['ok']:raise ValueError('Bundled jpn unavailable')
            model=(folder/'tessdata'/'jpn.traineddata').read_bytes()
            digest=hashlib.sha256(model).hexdigest()
            if digest!='1f5de9236d2e85f5fdf4b3c500f2d4926f8d9449f28f5394472d9e8d83b91b4d':raise ValueError('Model digest mismatch')
            recognized=bridge.call('ocr',image=PNG_BASE64,tesseract=str(engine),scope='package-synthetic-fixture')['text']
            if normalize(recognized)!=EXPECTED:raise ValueError('Synthetic OCR mismatch')
            checks['bundled_jpn_sha256']=digest;checks['synthetic_ocr']='passed'
        checks['status']='passed';checks['ok']=True
        code=0
    except Exception:
        checks['status']='failed';checks['ok']=False;checks['error']='Runtime imports, core demo, DPAPI or required bundled OCR failed.';code=1
    finally:
        if bridge:bridge.close()
    if report:
        Path(report).write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
