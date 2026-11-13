"""Local-only setup helpers. Never transmit screenshots, keys, or dialogue."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from dataclasses import asdict
from core import ReaderError, Region


def application_folder():
    return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


def find_tesseract(preferred=''):
    candidates=[preferred, os.environ.get('TESSERACT_CMD',''), str(application_folder()/'ocr'/'tesseract.exe')]
    for key in ['ProgramFiles','ProgramFiles(x86)']:
        if os.environ.get(key):candidates.append(str(Path(os.environ[key])/'Tesseract-OCR'/'tesseract.exe'))
    candidates.append(shutil.which('tesseract') or '')
    for name in candidates:
        if name and Path(name).is_file():return str(Path(name).resolve())
    return ''


def inspect_engine(preferred=''):
    path=find_tesseract(preferred)
    if not path:return {'ok':False,'path':'','detail':'Tesseract를 찾지 못했습니다. 설치 안내 또는 실행파일 선택을 이용하세요.'}
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if sys.platform=='win32' else 0
    env=os.environ.copy()
    sibling=Path(path).parent/'tessdata'
    if (sibling/'jpn.traineddata').is_file():env['TESSDATA_PREFIX']=str(sibling)
    try:
        result=subprocess.run([path,'--list-langs'],capture_output=True,timeout=8,env=env,creationflags=flags)
        # Tesseract can print diagnostic language paths, but never pass raw output to logs.
        langs=result.stdout.decode('utf-8',errors='replace').splitlines()
        japanese=any(line.strip()=='jpn' for line in langs)
        if result.returncode!=0:return {'ok':False,'path':path,'detail':'OCR 실행파일 검사 실패. Tesseract 설치를 확인하세요.'}
        if not japanese:return {'ok':False,'path':path,'detail':'일본어 jpn 언어팩이 없습니다. 설치 안내에서 추가하세요.'}
        return {'ok':True,'path':path,'detail':'Tesseract 실행 및 일본어 jpn 언어팩 확인 완료 (인식 품질 검증은 별도).'}
    except (OSError,subprocess.TimeoutExpired):
        return {'ok':False,'path':path,'detail':'OCR 점검 시간 초과 또는 실행 실패. 선택한 파일을 확인하세요.'}


def region_from_drag(start,end,preview_size,monitor):
    """Map a downscaled monitor preview to physical desktop pixels, including negatives."""
    pw,ph=preview_size
    if pw<=0 or ph<=0:raise ReaderError('미리보기 크기가 올바르지 않습니다.')
    x1,x2=sorted([max(0,min(pw,start[0])),max(0,min(pw,end[0]))])
    y1,y2=sorted([max(0,min(ph,start[1])),max(0,min(ph,end[1]))])
    left=round(x1*monitor['width']/pw);right=round(x2*monitor['width']/pw)
    top=round(y1*monitor['height']/ph);bottom=round(y2*monitor['height']/ph)
    return Region(monitor['left']+left,monitor['top']+top,right-left,bottom-top)


def settings_path():
    base=Path(os.environ.get('LOCALAPPDATA') or (Path.home()/'.config'))
    return base/'KotobaBridge'/'settings.json'


def save_settings(path,region,engine):
    # Explicit allowlist: never serialize a key, consent, history or study data.
    data={'version':1,'region':asdict(region),'tesseract':str(engine)}
    if len(data['tesseract'])>4096:raise ReaderError('OCR 경로가 너무 깁니다.')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    import tempfile
    fd,temp=tempfile.mkstemp(prefix='.settings-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as output:json.dump(data,output,ensure_ascii=False)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def load_settings(path):
    path=Path(path)
    if not path.exists():return None
    if path.stat().st_size>16384:raise ReaderError('설정 파일이 너무 큽니다.')
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or set(data)!={'version','region','tesseract'} or data['version']!=1:raise ValueError()
        if not isinstance(data['tesseract'],str) or len(data['tesseract'])>4096:raise ValueError()
        if not isinstance(data['region'],dict) or set(data['region'])!={'left','top','width','height'}:raise ValueError()
        if any(type(v) is not int for v in data['region'].values()):raise ValueError()
        return Region(**data['region']),data['tesseract']
    except (ValueError,TypeError,KeyError):raise ReaderError('설정 파일을 읽을 수 없습니다. 설정을 초기화하세요.') from None
