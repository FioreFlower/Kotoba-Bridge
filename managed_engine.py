"""Own only the process we created; never discover/kill servers by PID or port."""
import ctypes
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from core import ReaderError, NoRedirect
from local_models import model_path, verify_model
from local_runtime import runtime_path, verify_runtime

WINDOWS = sys.platform == 'win32'

class WindowsJob:
    """Kill owned descendants on handle close, including ordinary application exit."""
    def __init__(self, process):
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_=[('a',ctypes.c_int64),('b',ctypes.c_int64),('flags',w.DWORD),('min',ctypes.c_size_t),('max',ctypes.c_size_t),('count',w.DWORD),('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(n,ctypes.c_uint64) for n in ['r','w','o','rb','wb','ob']]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',IO),('p',ctypes.c_size_t),('j',ctypes.c_size_t),('pp',ctypes.c_size_t),('jp',ctypes.c_size_t)]
        k=self.k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];k.SetInformationJobObject.restype=w.BOOL
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];k.AssignProcessToJobObject.restype=w.BOOL
        k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
        self.handle=k.CreateJobObjectW(None,None)
        if not self.handle:raise OSError('job creation failed')
        info=Extended();info.basic.flags=0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)) or not k.AssignProcessToJobObject(self.handle,w.HANDLE(int(process._handle))):
            self.close();raise OSError('job ownership failed')
    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None

class ManagedEngine:
    def __init__(self):
        self.lock=threading.RLock();self.cancel=threading.Event()
        self.process=None;self.job=None;self.model_id=None;self.port=None;self.alias='';self.token='';self.ready=False
    def active(self):
        return self.process is not None and self.process.poll() is None
    def uses(self, model_id):
        # Keep the model reserved throughout startup and cleanup, too.
        return self.model_id==model_id
    def configuration(self):
        if not self.ready or not self.active():raise ReaderError('앱 관리 엔진이 중지되었습니다. 모델을 다시 실행하세요. 외부 서버로 전환하지 않았습니다.')
        return dict(local_port=self.port,local_model=self.alias,local_token=self.token)
    def _cleanup(self):
        p=self.process
        if p is not None:
            if self.job:self.job.close();self.job=None
            if p.poll() is None:
                p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill();p.wait(timeout=5)
        self.process=None;self.model_id=None;self.port=None;self.alias='';self.token='';self.ready=False
    def stop(self):
        self.cancel.set()
        with self.lock:
            try:self._cleanup()
            except Exception:raise ReaderError('앱 관리 엔진 종료에 실패했습니다. 모델을 삭제하지 말고 앱을 다시 확인하세요.') from None
    def start(self, model_id, *, cancelled=None, timeout=120):
        with self.lock:
            self.cancel.clear()
            self._cleanup()
            self.model_id=model_id
            try:
                if not WINDOWS:raise ReaderError('앱 관리 엔진은 Windows x64 전용입니다.')
                if not verify_runtime():raise ReaderError('공식 엔진을 먼저 설치/검증하세요.')
                if not verify_model(model_path(model_id),model_id):raise ReaderError('선택 모델을 먼저 다운로드/검증하세요.')
                if self.cancel.is_set() or (cancelled and cancelled.is_set()):raise ReaderError('엔진 시작을 취소했습니다.')
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
                self.token=secrets.token_hex(32);self.alias='kotoba-'+secrets.token_hex(16)
                exe=runtime_path()/'llama-server.exe'
                args=[str(exe),'-m',str(model_path(model_id)),'--host','127.0.0.1','--port',str(self.port),'--alias',self.alias,'--api-key',self.token,'-c','4096','-t','2','-np','1','-ngl','0','--no-webui','--no-slots','--no-webui-mcp-proxy','--cors-origins','http://127.0.0.1','--log-disable']
                # Do not inherit cloud keys, proxy settings, LLAMA_ARG_* or injected DLL paths.
                env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP'}}
                self.process=subprocess.Popen(args,cwd=runtime_path(),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.job=WindowsJob(self.process)
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
                end=time.monotonic()+timeout
                while time.monotonic()<end:
                    if self.cancel.is_set() or (cancelled and cancelled.is_set()):raise ReaderError('엔진 시작을 취소했습니다.')
                    if not self.active():raise ReaderError('엔진 시작 실패: CPU 호환성·메모리·보안 차단을 확인하세요. 자동 재시도 없음.')
                    try:
                        req=urllib.request.Request(f'http://127.0.0.1:{self.port}/v1/models',headers={'Authorization':'Bearer '+self.token})
                        with opener.open(req,timeout=0.5) as response:
                            raw=response.read(16385)
                            if len(raw)<=16384 and response.status==200 and any(m.get('id')==self.alias for m in json.loads(raw).get('data',[])):
                                if not self.active():raise ReaderError('엔진이 종료되었습니다.')
                                self.ready=True;return
                    except (OSError,ValueError,KeyError,TypeError):pass
                    self.cancel.wait(0.1)
                raise ReaderError('모델 로딩 시간 초과. 엔진을 종료했습니다. 자동 재시도 없음.')
            except Exception as exc:
                self._cleanup()
                if isinstance(exc,ReaderError):raise
                raise ReaderError('로컬 엔진 실행/소유권 확인 실패. 외부 서버는 변경하지 않았습니다.') from None
