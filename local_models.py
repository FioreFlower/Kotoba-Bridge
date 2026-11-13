"""Opt-in pinned model download; no automatic model/network activity at startup."""
import hashlib
import os
from pathlib import Path
import tempfile
import socket
import urllib.request
from core import ReaderError
from onboarding import data_folder

MODEL_NAME='Qwen2.5-1.5B-Instruct Q4_K_M (오역 다수 · 추천 안 함)'
MODEL_REVISION='91cad51170dc346986eccefdc2dd33a9da36ead9'
MODEL_FILE='qwen2.5-1.5b-instruct-q4_k_m.gguf'
MODEL_BYTES=1117320736
MODEL_SHA256='6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'
MODEL_REPO='https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_URL=f'{MODEL_REPO}/resolve/{MODEL_REVISION}/{MODEL_FILE}'
LICENSE_URL=f'{MODEL_REPO}/blob/{MODEL_REVISION}/LICENSE'

MODELS={
 'qwen25-1.5b':dict(name=MODEL_NAME,file=MODEL_FILE,bytes=MODEL_BYTES,sha256=MODEL_SHA256,revision=MODEL_REVISION,repo=MODEL_REPO,memory='RAM 계획 예산 3~4GB + 게임/OS 별도 (최소사양 보장 아님)',measured='Linux 재측정 p50 1.72초/p95 3.11초; 오역 다수 → 추천 안 함; Windows 미검증'),
 'qwen3-4b':dict(name='Qwen3-4B Q4_K_M (비추론 · 비교 후보)',file='Qwen3-4B-Q4_K_M.gguf',bytes=2497280256,sha256='7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5',revision='bc640142c66e1fdd12af0bd68f40445458f3869b',repo='https://huggingface.co/Qwen/Qwen3-4B-GGUF',memory='RAM 계획 예산 5~7GB + 게임/OS 별도 (추정, 실측 아님)',measured='Linux p50 5.01초/p95 6.28초; 일부 오역/영어 응답; Windows 미검증')
}

def spec(model_id):
    if model_id not in MODELS:raise ReaderError('등록되지 않은 모델입니다.')
    return MODELS[model_id]

def model_path(model_id='qwen25-1.5b'):return data_folder()/'models'/spec(model_id)['file']

def safe_path(path):
    path=Path(path).absolute()
    for entry in [path,*path.parents]:
        if entry.is_symlink() or (hasattr(os.path,'isjunction') and os.path.isjunction(entry)):
            raise ReaderError('링크/정션 경로의 모델 작업을 거부했습니다.')
        try:
            if getattr(entry.lstat(),'st_file_attributes',0)&0x400:raise ReaderError('재분석 지점의 모델 작업을 거부했습니다.')
        except FileNotFoundError:pass
    return path

def local_server_present(port):
    try:
        port=int(port)
        if not 1024<=port<=65535:return True
        with socket.create_connection(('127.0.0.1',port),timeout=0.3):return True
    except (ValueError,TypeError):return True
    except OSError:return False

def delete_model(model_id,*,in_use=False):
    if in_use:raise ReaderError('사용 중인 모델입니다. 로컬 서버를 종료하고 다른 제공자를 선택한 뒤 삭제하세요.')
    path=safe_path(model_path(model_id))
    try:
        if path.exists() and (not path.is_file() or path.stat().st_nlink!=1):raise ReaderError('일반 모델 파일만 삭제할 수 있습니다.')
        path.unlink(missing_ok=True)
    except OSError:raise ReaderError('모델 삭제 실패. 서버 종료·파일 잠금·권한을 확인하세요. 다른 데이터는 삭제하지 않았습니다.') from None

def verify_model(path,model_id='qwen25-1.5b'):
    item=spec(model_id);path=safe_path(path)
    if not path.is_file() or path.stat().st_size!=item['bytes']:return False
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()==item['sha256']

class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not newurl.startswith('https://'):raise ReaderError('모델 다운로드의 안전하지 않은 리디렉션을 차단했습니다.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def install_model(*,accepted=False,cancel=None,progress=None,destination=None,model_id='qwen25-1.5b'):
    if accepted is not True:raise ReaderError('모델 라이선스와 표시된 크기의 다운로드 확인이 필요합니다.')
    item=spec(model_id)
    target=safe_path(Path(destination) if destination is not None else model_path(model_id))
    expected_size=item['bytes'];expected_hash=item['sha256']
    url=f"{item['repo']}/resolve/{item['revision']}/{item['file']}"
    if target.exists():
        if verify_model(target,model_id):return target
        raise ReaderError('기존 모델의 해시가 다릅니다. 파일을 직접 확인/삭제한 후 다시 설치하세요.')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        opener=urllib.request.build_opener(HTTPSRedirect())
        with opener.open(url,timeout=30) as response:
            if response.status!=200:raise ReaderError('모델 다운로드 응답 오류')
            if response.headers.get('Content-Length') and int(response.headers['Content-Length'])!=expected_size:raise ReaderError('모델 크기가 배포 기록과 다릅니다.')
            with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.model-',delete=False) as out:
                temporary=Path(out.name);h=hashlib.sha256();size=0
                while True:
                    if cancel and cancel.is_set():raise ReaderError('모델 설치를 취소했습니다.')
                    chunk=response.read(1024*1024)
                    if not chunk:break
                    size+=len(chunk)
                    if size>expected_size:raise ReaderError('모델 크기 한도 초과')
                    h.update(chunk);out.write(chunk)
                    if progress:progress(size,expected_size)
                out.flush();os.fsync(out.fileno())
        if size!=expected_size or h.hexdigest()!=expected_hash:raise ReaderError('모델 무결성 검사 실패. 설치하지 않았습니다.')
        if cancel and cancel.is_set():raise ReaderError('모델 설치를 취소했습니다.')
        os.replace(temporary,target);temporary=None
        return target
    except ReaderError:raise
    except Exception:raise ReaderError('모델 다운로드/저장 실패. 공간·연결을 확인하세요. 자동 재시도 없음.') from None
    finally:
        if temporary is not None:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass
