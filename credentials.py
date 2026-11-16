"""Current-user Windows DPAPI storage. Never falls back to plaintext."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile
from core import ReaderError

MAGIC = b'KOTOBA-DPAPI-1\x00'
MAX_FILE = 32768


def valid_key(key):
    if not isinstance(key, str) or not key.strip() or len(key) > 4096:
        raise ReaderError('API 키를 입력하세요 (최대 4096자).')
    key = key.strip()
    if any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ReaderError('API 키에 허용되지 않는 문자가 있습니다.')
    return key


class Blob(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]


class DPAPI:
    def _crypt(self, data, decrypt=False):
        if sys.platform != 'win32':
            raise ReaderError('암호화 키 저장은 Windows에서만 지원합니다. 평문으로 저장하지 않습니다.')
        if not data or len(data) > MAX_FILE:
            raise ReaderError('암호화 키 데이터가 올바르지 않습니다.')
        crypt = ctypes.WinDLL('crypt32', use_last_error=True)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        source = Blob(len(data), buffer); target = Blob()
        common = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                  ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
        fn.argtypes = common; fn.restype = wintypes.BOOL
        try:
            # No LOCAL_MACHINE, no UI prompts, no secret-bearing description.
            if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
                raise ReaderError('Windows 키 보호 실패: 같은 PC·사용자 계정인지 확인하거나 키를 다시 저장하세요.')
            if not target.pbData or not 0 < target.cbData <= MAX_FILE:
                raise ReaderError('Windows 키 보호 응답이 올바르지 않습니다.')
            return ctypes.string_at(target.pbData, target.cbData)
        finally:
            ctypes.memset(buffer, 0, len(data))
            if target.pbData:
                ctypes.memset(target.pbData, 0, target.cbData)
                kernel.LocalFree(ctypes.cast(target.pbData, ctypes.c_void_p))

    def protect(self, data):
        return self._crypt(data)

    def unprotect(self, data):
        return self._crypt(data, True)


class KeyStore:
    def __init__(self, path=None, protector=None):
        if path is None:
            from onboarding import data_folder
            path = data_folder() / 'deepl-key.dpapi'
        self.path = Path(path)
        self.protector = protector if protector is not None else DPAPI()

    def save(self, key, pro=False):
        key = valid_key(key)
        if type(pro) is not bool:raise ReaderError('API 계정 종류가 올바르지 않습니다.')
        # Encrypt BEFORE opening any disk file. Temp files contain ciphertext only.
        payload = json.dumps({'version':1, 'key':key, 'pro':pro}).encode('utf-8')
        encrypted = self.protector.protect(payload)
        if not encrypted or len(encrypted) > MAX_FILE-len(MAGIC):
            raise ReaderError('암호화 키 크기가 올바르지 않습니다.')
        temp = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(prefix='.credential-', dir=self.path.parent)
            with os.fdopen(fd, 'wb') as output:
                output.write(MAGIC + encrypted);output.flush();os.fsync(output.fileno())
            os.replace(temp, self.path)
        except OSError:
            raise ReaderError('키 저장 실패: 쓰기 가능한 데이터 폴더인지 확인하세요. 기존 저장 키는 유지됩니다.') from None
        finally:
            if temp and os.path.exists(temp):os.unlink(temp)

    def load(self):
        try:
            if not self.path.exists():return None
            with self.path.open('rb') as source:raw = source.read(MAX_FILE+1)
            if len(raw)>MAX_FILE or not raw.startswith(MAGIC):raise ValueError()
            value = json.loads(self.protector.unprotect(raw[len(MAGIC):]).decode('utf-8'))
            if not isinstance(value, dict) or set(value)!={'version','key','pro'} or value['version']!=1 or type(value['pro']) is not bool:
                raise ValueError()
            return valid_key(value['key']), value['pro']
        except ReaderError:raise
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            raise ReaderError('저장 키를 읽지 못했습니다. 손상되었거나 다른 PC·계정의 파일일 수 있습니다. 삭제 후 다시 입력하세요.') from None

    def delete(self):
        try:self.path.unlink(missing_ok=True)
        except OSError:
            raise ReaderError('저장 키 파일 삭제 실패. 데이터 폴더 권한을 확인하세요. 저장 키가 남아 있습니다.') from None


def remove_legacy_keys(path):
    """Never import unknown plaintext credentials. Drop known old fields, no backup."""
    path = Path(path)
    if not path.exists():return False
    try:
        with path.open('rb') as source:raw=source.read(16385)
        if len(raw)>16384:raise ValueError()
        value=json.loads(raw.decode('utf-8'))
        if not isinstance(value,dict):raise ValueError()
        secret_names={'key','apikey','deeplkey','deeplapikey','authkey'}
        found=[k for k in value if k.lower().replace('_','').replace('-','') in secret_names]
        if not found:return False
        for k in found:del value[k]
        # Validate remaining settings without ever writing a plaintext-key backup.
        if set(value)!={'version','region','tesseract'} or value['version']!=1:raise ValueError()
        from core import Region
        from onboarding import save_settings
        if not isinstance(value['region'],dict) or any(type(v) is not int for v in value['region'].values()):raise ValueError()
        if not isinstance(value['tesseract'],str):raise ValueError()
        save_settings(path,Region(**value['region']),value['tesseract'])
        return True
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,ReaderError):
        raise ReaderError('기존 설정을 안전하게 확인/정리하지 못했습니다. 초기 설정에서 저장 설정을 삭제하고 키를 다시 입력하세요.') from None
