"""Bounded, local candidate state. No process attachment, clipboard polling or sockets."""
from dataclasses import dataclass
import re
from core import ReaderError, normalize


def source_text(value):
    if not isinstance(value,str) or len(value)>2000:
        raise ReaderError('원문은 최대 2,000자입니다.')
    if any(ord(c)<32 and c not in '\n\r\t' for c in value):
        raise ReaderError('제어 문자가 포함된 입력입니다.')
    value=normalize(value)
    if not value:raise ReaderError('확인할 원문을 입력하세요.')
    return value

@dataclass(frozen=True)
class Candidate:
    identifier: str
    text: str
    updates: int=1
    repeats: int=0

class CandidateSession:
    """Adapter contract prototype: generation fences and bounded streams, never auto-select."""
    def __init__(self):
        self.generation=0;self.active=False;self.candidates={};self.selected=None;self.events=0
    def start(self,consent=False):
        self.stop()
        if not consent:raise ReaderError('로컬 후보 미리보기 동의가 필요합니다.')
        self.active=True
        return self.generation
    def stop(self):
        self.generation+=1;self.active=False;self.candidates.clear();self.selected=None;self.events=0
    def ingest(self,generation,identifier,text):
        if not self.active or generation!=self.generation:return False
        if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',identifier):
            raise ReaderError('잘못된 후보 식별자입니다.')
        text=source_text(text)
        if self.events>=1000:
            self.stop();raise ReaderError('후보 입력 한도 초과: 탐색을 중지했습니다.')
        if identifier not in self.candidates and len(self.candidates)>=32:
            self.stop();raise ReaderError('후보 수 한도 초과: 탐색을 중지했습니다.')
        old=self.candidates.get(identifier)
        self.candidates[identifier]=Candidate(identifier,text,old.updates+1 if old else 1,
            old.repeats+int(old.text==text) if old else 0)
        self.events+=1
        return True
    def select(self,identifier):
        if not self.active or identifier not in self.candidates:raise ReaderError('유효한 후보를 선택하세요.')
        self.selected=identifier
        return self.candidates[identifier].text
    def ranked(self):
        def rank(c):
            japanese=sum('\u3040'<=x<='\u30ff' or '\u3400'<=x<='\u9fff' for x in c.text)
            return (int(len(c.text)>=8)+int(japanese>0)+int(any(x in c.text for x in '。！？'))-int(c.repeats>1),c.identifier)
        return sorted(self.candidates.values(),key=rank,reverse=True)
    @staticmethod
    def reasons(c):
        return ('문장 길이 후보' if len(c.text)>=8 else '짧은 이름/메뉴 가능')+' · '+('반복 많음' if c.repeats>1 else '반복 적음')+' · 정확성 미확인'
