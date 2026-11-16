"""Bounded latest-only continuous translation policy; no network or GUI dependencies."""
import time
from core import ReaderError

class HookStream:
    def __init__(self):
        self.stop()
    def stop(self):
        self.active=False;self.selected=None;self.current=None;self.changed_at=0
        self.sent=None;self.last_sent=None;self.armed=False;self.deadline=0
    def start(self,identifier,text,now=None):
        self.stop();self.active=True;self.selected=identifier
        now=time.monotonic() if now is None else now
        self.current=text;self.changed_at=now;self.deadline=now+15
    def update(self,identifier,text,now):
        if not self.active:return False
        if identifier!=self.selected:
            self.stop();raise ReaderError('선택 후보가 바뀌어 연속 번역을 중지했습니다.')
        if text!=self.current:
            self.current=text;self.changed_at=now;return True
        return False
    def ready(self,now,foreground,busy):
        if not self.active:return None
        if not foreground:
            if self.armed or now>=self.deadline:
                self.stop();raise ReaderError('게임 포커스가 없어 연속 번역을 중지했습니다. 자동 재개하지 않습니다.')
            return None
        self.armed=True
        if busy or now-self.changed_at<0.6 or self.current==self.sent:return None
        if self.last_sent is not None and now-self.last_sent<3:return None
        self.sent=self.current;self.last_sent=now
        return self.current
    def accepts(self,text):
        return self.active and self.armed and self.current==text and self.sent==text
