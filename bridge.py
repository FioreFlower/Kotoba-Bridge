"""Private parent-child JSON-lines IPC. Never starts a listening network socket."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from types import SimpleNamespace
from core import ReaderError

class GoBridge:
    def __init__(self, executable=None):
        folder=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
        self.executable=Path(executable) if executable else folder/('kotoba-core.exe' if sys.platform=='win32' else 'kotoba-core')
        if not self.executable.is_file():
            raise ReaderError('Go 코어가 없습니다. 개발 빌드 안내 또는 완성 패키지를 확인하세요.')
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if sys.platform=='win32' else 0
        self.process=subprocess.Popen([str(self.executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL,creationflags=flags)
        self.lock=threading.Lock(); self.serial=0; self.responses=queue.Queue(); self.closed=False
        threading.Thread(target=self._read,daemon=True).start()
        try:
            hello=self.call('hello')
            if hello.get('protocol')!=1:raise ReaderError('Go 코어 프로토콜 버전 불일치')
        except Exception:
            self.close(); raise
    def _read(self):
        while True:
            line=self.process.stdout.readline(131073)
            if not line or len(line)>131072:
                self.responses.put(None);return
            self.responses.put(line)
    def call(self,method,**params):
        with self.lock:
            if self.closed:raise ReaderError('Go 코어가 종료되었습니다. 앱을 다시 실행하세요.')
            self.serial+=1
            request=dict(params,id=self.serial,version=1,method=method)
            payload=json.dumps(request,ensure_ascii=False).encode('utf-8')+b'\n'
            if len(payload)>12_000_000:raise ReaderError('IPC 이미지 크기 한도를 초과했습니다.')
            try:
                self.process.stdin.write(payload);self.process.stdin.flush()
                raw=self.responses.get(timeout=130 if method=='translate' else 25)
                if raw is None:raise ValueError()
                reply=json.loads(raw)
                if reply.get('id')!=self.serial or reply.get('version')!=1:raise ValueError()
                if not reply.get('ok'):raise ReaderError(reply.get('error','Go 코어 오류'))
                return reply.get('result',{})
            except ReaderError:raise
            except Exception:
                self.close()
                raise ReaderError('코어 연결 중단/응답 오류. 자동 재시도하지 않습니다. 앱을 재실행하세요.') from None
    def close(self):
        self.closed=True
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait(timeout=2)
        for stream in [self.process.stdin,self.process.stdout]:
            try:stream.close()
            except Exception:pass

class RemoteClear:
    def __init__(self,bridge):self.bridge=bridge
    def clear(self):self.bridge.call('clear')

class GoTranslator:
    def __init__(self,bridge):
        self.bridge=bridge
        self.history=RemoteClear(bridge);self.cache=RemoteClear(bridge)
        self.budget=SimpleNamespace(calls=0,chars=0)
    def translate(self,text):
        result=self.bridge.call('translate',text=text)
        status=self.bridge.call('status')
        self.budget.calls=status['calls'];self.budget.chars=status['chars']
        return result['text']

class GoStable:
    def __init__(self,bridge):
        self.bridge=bridge
        self.bridge.call('observe',text='',reset=True)
    def feed(self,text,now):
        return self.bridge.call('observe',text=text).get('text') or None
