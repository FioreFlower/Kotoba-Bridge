"""Explicit verified runtime preparation. Never executes a downloaded program."""
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import urllib.request
import zipfile
from core import ReaderError
from onboarding import data_folder
from local_models import safe_path, HTTPSRedirect
from runtime_catalog import ARCHIVE_URL, ARCHIVE_BYTES, ARCHIVE_SHA256, FILES, MIT_LICENSE


def runtime_path():
    return data_folder() / 'runtimes' / 'llama-b12359-win-cpu-x64'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify_runtime(target=None):
    target = safe_path(target if target is not None else runtime_path())
    if not target.is_dir():
        return False
    expected = set(FILES) | {'LICENSE-llama.cpp.txt'}
    if {p.name for p in target.iterdir()} != expected:
        return False
    for name, item in FILES.items():
        path = safe_path(target / name)
        if not path.is_file() or path.stat().st_nlink != 1:
            return False
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            return False
    license_path = safe_path(target / 'LICENSE-llama.cpp.txt')
    return license_path.is_file() and license_path.stat().st_nlink == 1 and license_path.read_text(encoding='utf-8') == MIT_LICENSE


def unpack_verified(archive, target, cancel=None):
    """Caller provides a private staging archive, never an arbitrary destination tree."""
    archive = safe_path(archive)
    target = safe_path(target)
    if archive.stat().st_size != ARCHIVE_BYTES or digest(archive) != ARCHIVE_SHA256:
        raise ReaderError('엔진 ZIP 무결성 검사 실패. 실행/설치하지 않았습니다.')
    if target.exists():
        raise ReaderError('기존 엔진 폴더는 덮어쓰지 않습니다.')
    target.mkdir()
    created = []
    try:
        with zipfile.ZipFile(archive) as z:
            entries = z.infolist()
            if len(entries) != len(FILES) or {i.filename for i in entries} != set(FILES):
                raise ReaderError('엔진 ZIP 파일 목록이 고정 배포 기록과 다릅니다.')
            for info in entries:
                name = info.filename
                mode = info.external_attr >> 16
                if ('/' in name or '\\' in name or ':' in name or name in {'.', '..'}
                        or info.is_dir() or stat.S_ISLNK(mode)
                        or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                        or info.file_size != FILES[name]['bytes']):
                    raise ReaderError('안전하지 않은 엔진 ZIP 항목을 거부했습니다.')
                if cancel and cancel.is_set():
                    raise ReaderError('엔진 설치를 취소했습니다.')
                out = safe_path(target / name)
                with z.open(info) as src, out.open('xb') as dst:
                    created.append(out)
                    h = hashlib.sha256(); size = 0
                    while True:
                        block = src.read(1024 * 1024)
                        if not block: break
                        size += len(block)
                        if size > FILES[name]['bytes']: raise ReaderError('엔진 압축 크기 한도 초과')
                        h.update(block); dst.write(block)
                    if size != FILES[name]['bytes'] or h.hexdigest() != FILES[name]['sha256']:
                        raise ReaderError('엔진 개별 파일 해시 불일치')
        license_path = target / 'LICENSE-llama.cpp.txt'
        with license_path.open('x', encoding='utf-8', newline='') as stream:
            created.append(license_path); stream.write(MIT_LICENSE)
        if cancel and cancel.is_set(): raise ReaderError('엔진 설치를 취소했습니다.')
        return target
    except Exception:
        # Only the files created by this invocation; never follow links or recurse.
        for path in reversed(created):
            safe_path(path).unlink(missing_ok=True)
        target.rmdir()
        raise


def install_runtime(*, accepted=False, cancel=None, progress=None):
    if accepted is not True:
        raise ReaderError('엔진 출처·라이선스·다운로드 크기 확인이 필요합니다.')
    target = safe_path(runtime_path())
    if target.exists():
        if verify_runtime(target): return target
        raise ReaderError('기존 엔진 파일이 변조되었거나 불완전합니다. 자동 덮어쓰기하지 않습니다.')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='.engine-', dir=target.parent) as temp:
            archive = Path(temp) / 'runtime.zip'
            opener = urllib.request.build_opener(HTTPSRedirect())
            with opener.open(ARCHIVE_URL, timeout=30) as response, archive.open('xb') as out:
                if response.status != 200: raise ReaderError('엔진 다운로드 응답 오류')
                if response.headers.get('Content-Length') and int(response.headers['Content-Length']) != ARCHIVE_BYTES:
                    raise ReaderError('엔진 다운로드 크기 불일치')
                size = 0
                while True:
                    if cancel and cancel.is_set(): raise ReaderError('엔진 설치를 취소했습니다.')
                    block = response.read(1024 * 1024)
                    if not block: break
                    size += len(block)
                    if size > ARCHIVE_BYTES: raise ReaderError('엔진 다운로드 크기 한도 초과')
                    out.write(block)
                    if progress: progress(size, ARCHIVE_BYTES)
                out.flush(); os.fsync(out.fileno())
            staged = unpack_verified(archive, Path(temp) / 'verified', cancel)
            if cancel and cancel.is_set(): raise ReaderError('엔진 설치를 취소했습니다.')
            # Refuse replacement, including a competing installation.
            staged.rename(target)
        return target
    except ReaderError: raise
    except Exception:
        raise ReaderError('엔진 다운로드/저장 실패. 공간·권한·연결을 확인하세요. 자동 실행/재시도 없음.') from None
