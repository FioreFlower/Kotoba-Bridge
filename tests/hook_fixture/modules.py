"""Read loaded module names of our owned synthetic fixture only; no memory writes."""
import ctypes as c
from ctypes import wintypes as w

def names(pid):
    class Entry(c.Structure):
        _fields_=[('size',w.DWORD),('module_id',w.DWORD),('pid',w.DWORD),('global_use',w.DWORD),('process_use',w.DWORD),('base',c.POINTER(c.c_byte)),('base_size',w.DWORD),('module',w.HMODULE),('name',w.WCHAR*256),('path',w.WCHAR*260)]
    k=c.WinDLL('kernel32',use_last_error=True)
    k.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];k.CreateToolhelp32Snapshot.restype=w.HANDLE
    k.Module32FirstW.argtypes=[w.HANDLE,c.POINTER(Entry)];k.Module32FirstW.restype=w.BOOL
    k.Module32NextW.argtypes=[w.HANDLE,c.POINTER(Entry)];k.Module32NextW.restype=w.BOOL
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    handle=k.CreateToolhelp32Snapshot(0x18,pid)
    if handle==w.HANDLE(-1).value:raise OSError('fixture module snapshot failed')
    try:
        item=Entry();item.size=c.sizeof(item)
        if not k.Module32FirstW(handle,c.byref(item)):raise OSError('fixture module enumeration failed')
        result=[]
        while True:
            result.append(item.name.lower())
            if not k.Module32NextW(handle,c.byref(item)):break
        return result
    finally:k.CloseHandle(handle)
