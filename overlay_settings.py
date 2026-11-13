"""Only background opacity is persisted; never full-window/text alpha."""
import json
import math
import os
from pathlib import Path
import tempfile
from core import ReaderError
DEFAULT_OPACITY = 85


def opacity(value):
    if isinstance(value,bool):raise ValueError('Invalid opacity')
    number=float(value)
    if not math.isfinite(number) or not 0<=number<=100:raise ValueError('Invalid opacity')
    return round(number)


def preference_path():
    from onboarding import data_folder
    return data_folder()/'overlay.json'


def load_opacity(path=None):
    path=Path(path) if path is not None else preference_path()
    if not path.exists():return DEFAULT_OPACITY
    try:
        with path.open('rb') as f:raw=f.read(2049)
        if len(raw)>2048:raise ValueError()
        value=json.loads(raw)
        if not isinstance(value,dict) or set(value)!={'version','background_opacity'} or value['version']!=1:raise ValueError()
        return opacity(value['background_opacity'])
    except (OSError,ValueError,TypeError):
        raise ReaderError('자막 배경 설정을 읽지 못해 기본값으로 표시합니다. 설정 저장으로 초기화하세요.') from None


def save_opacity(value,path=None):
    value=opacity(value)
    path=Path(path) if path is not None else preference_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.overlay-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump({'version':1,'background_opacity':value},f)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
