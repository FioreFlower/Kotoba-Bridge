"""Packaging smoke test: no GUI window, capture, OCR process, key or network."""
import importlib
import json
from pathlib import Path
from bridge import GoBridge


def run(report=None):
    checks={};bridge=None
    try:
        for name in ['tkinter','PIL','mss']:
            importlib.import_module(name);checks[name]='import_ok'
        bridge=GoBridge();hello=bridge.call('hello')
        checks['core_protocol']=hello['protocol'];checks['core_version']=hello.get('version')
        bridge.call('configure',demo=True)
        result=bridge.call('translate',text='こんにちは。')
        if result.get('text')!='안녕하세요.':raise ValueError('Demo mismatch')
        checks['demo']='ok';checks['status']='passed';checks['ok']=True
        code=0
    except Exception:
        checks['status']='failed';checks['ok']=False;checks['error']='Runtime imports or local core demo failed.';code=1
    finally:
        if bridge:bridge.close()
    if report:
        Path(report).write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
