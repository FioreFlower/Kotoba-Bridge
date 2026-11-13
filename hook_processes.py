"""Read-only Windows visible-process picker. No memory write/injection/elevation."""
from dataclasses import dataclass
import ctypes as c
from ctypes import wintypes as w
import os
from core import ReaderError

@dataclass(frozen=True)
class ProcessIdentity:
    pid:int
    created:int
    path:str
    arch:str

def identity(pid):
    if os.name!='nt':raise ReaderError('Windows 게임 프로세스 선택 기능입니다.')
    k=c.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    k.GetProcessTimes.argtypes=[w.HANDLE]+[c.POINTER(w.FILETIME)]*4;k.GetProcessTimes.restype=w.BOOL
    k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)];k.QueryFullProcessImageNameW.restype=w.BOOL
    k.IsWow64Process2.argtypes=[w.HANDLE,c.POINTER(w.WORD),c.POINTER(w.WORD)];k.IsWow64Process2.restype=w.BOOL
    k.GetExitCodeProcess.argtypes=[w.HANDLE,c.POINTER(w.DWORD)];k.GetExitCodeProcess.restype=w.BOOL
    handle=k.OpenProcess(0x1000,False,pid) # QUERY_LIMITED_INFORMATION only
    if not handle:raise ReaderError('프로세스를 읽을 수 없습니다. 관리자 실행으로 우회하지 마세요.')
    try:
        times=[w.FILETIME() for _ in range(4)];buf=c.create_unicode_buffer(32768);size=w.DWORD(len(buf));code=w.DWORD()
        process_machine=w.WORD();native_machine=w.WORD()
        if not (k.GetProcessTimes(handle,*[c.byref(t) for t in times]) and
                k.QueryFullProcessImageNameW(handle,0,buf,c.byref(size)) and
                k.IsWow64Process2(handle,c.byref(process_machine),c.byref(native_machine)) and
                k.GetExitCodeProcess(handle,c.byref(code)) and code.value==259):raise ReaderError('실행 중 프로세스 확인 실패')
        machine=process_machine.value or native_machine.value
        if machine not in (0x14c,0x8664):raise ReaderError('x86/x64 게임만 후보로 표시합니다.')
        return ProcessIdentity(pid,(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime,buf.value,'x86' if machine==0x14c else 'x64')
    finally:k.CloseHandle(handle)

def visible_processes():
    if os.name!='nt':raise ReaderError('Windows 전용입니다.')
    u=c.WinDLL('user32',use_last_error=True);callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    u.EnumWindows.argtypes=[callback,w.LPARAM];u.EnumWindows.restype=w.BOOL
    u.IsWindowVisible.argtypes=[w.HWND];u.IsWindowVisible.restype=w.BOOL
    u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)];u.GetWindowThreadProcessId.restype=w.DWORD
    rows={}
    def visit(hwnd,_):
        pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(pid))
        if pid.value!=os.getpid() and u.IsWindowVisible(hwnd) and pid.value not in rows:
            try:rows[pid.value]=identity(pid.value)
            except (ReaderError,AttributeError):pass
        return True
    if not u.EnumWindows(callback(visit),0):raise ReaderError('창 목록을 읽지 못했습니다.')
    return sorted(rows.values(),key=lambda p:(p.path.casefold(),p.pid))
