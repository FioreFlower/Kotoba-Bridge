"""Explicit paste review and an honestly labelled synthetic candidate UX."""
import tkinter as tk
from tkinter import ttk, messagebox
from input_sources import CandidateSession, source_text
from core import ReaderError

class InputWindow:
    def __init__(self,app):
        self.app=app;self.session=CandidateSession();self.closed=False
        self.window=tk.Toplevel(app.root);self.window.title('텍스트 입력 · 외부 도구 연결 아님')
        self.window.geometry('760x740');self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.window.bind('<Escape>',lambda _:self.close())
        body=ttk.Frame(self.window,padding=12);body.pack(fill='both',expand=True)
        ttk.Label(body,text='외부 도구에서 복사한 원문을 직접 확인',font=('',14,'bold')).pack(anchor='w')
        ttk.Label(body,text='Textractor의 Copy to Clipboard 출력 등을 사용자가 붙여넣는 방식입니다.\n클립보드 출처를 인증하지 못합니다. 비밀번호·메시지·개인정보가 아닌지 확인하세요.\n자동 감시·주입·게임 연결은 하지 않습니다. OCR은 이 창을 여는 동안 정지합니다.',wraplength=700).pack(anchor='w',pady=8)
        self.text=tk.Text(body,height=6,wrap='word');self.text.pack(fill='x')
        self.text.bind('<<Modified>>',self.changed)
        row=ttk.Frame(body);row.pack(fill='x',pady=6)
        ttk.Button(row,text='클립보드 한 번 읽기',command=self.paste).pack(side='left')
        ttk.Button(row,text='확인한 원문 1회 번역',command=self.translate).pack(side='left',padx=8)
        ttk.Label(body,text='번역은 메인 화면의 DeepL 키·전송 동의·세션 한도를 사용합니다. 자동 반복/재시도 없음.',wraplength=700).pack(anchor='w')
        ttk.Separator(body).pack(fill='x',pady=10)
        ttk.Label(body,text='후킹 후보 선택 체험 — 합성 예제만, 실제 탐색 미구현',font=('',12,'bold')).pack(anchor='w')
        self.preview_consent=tk.BooleanVar(value=False)
        ttk.Checkbutton(body,text='합성 후보만 로컬 미리보기 (게임 주입 동의가 아님)',variable=self.preview_consent,command=self.consent_changed).pack(anchor='w')
        row=ttk.Frame(body);row.pack(fill='x')
        ttk.Button(row,text='예제 후보 탐색',command=self.begin).pack(side='left')
        ttk.Button(row,text='예제 다음 대사',command=self.advance).pack(side='left',padx=8)
        ttk.Button(row,text='탐색 중지',command=self.stop).pack(side='left')
        self.list=tk.Listbox(body,height=4,exportselection=False);self.list.pack(fill='x',pady=6)
        self.list.bind('<<ListboxSelect>>',self.select)
        self.detail=tk.StringVar(value='후보는 자동 선택하지 않습니다. 추천은 정답이나 정확도 확률이 아닙니다.')
        ttk.Label(body,textvariable=self.detail,wraplength=700).pack(anchor='w')
        ttk.Label(body,text='실제 후킹 도구는 별도 설치·동의가 필요합니다. 온라인/안티치트 게임 사용을 피하고,\n보안 예외나 관리자 승격이 필요하면 중단하세요. 통합 프로세스 선택/주입은 제공하지 않습니다.',wraplength=700).pack(anchor='w',pady=8)
        ttk.Button(body,text='닫고 OCR 설정으로 복귀 (자동 시작 안 함)',command=self.close).pack(anchor='e')
    def changed(self,event=None):
        if self.text.edit_modified():
            self.app.pause();self.text.edit_modified(False)
    def paste(self):
        self.app.pause()
        try:
            text=source_text(self.window.clipboard_get())
            self.text.delete('1.0','end');self.text.insert('1.0',text)
        except (tk.TclError,ReaderError):messagebox.showerror('붙여넣기 실패','텍스트가 없거나 2,000자 제한을 넘었습니다.',parent=self.window)
    def translate(self):
        self.text.edit_modified(False)
        try:
            text=source_text(self.text.get('1.0','end-1c'))
            if not messagebox.askyesno('외부 전송 확인','현재 원문을 DeepL에 1회 전송합니다. 개인정보가 없고 선택한 대사가 맞습니까?\n화면 이미지와 합성 후보는 전송하지 않습니다.',parent=self.window):return
            self.app.translate_input(text)
        except ReaderError as e:messagebox.showerror('전송할 수 없음',str(e),parent=self.window)
    def consent_changed(self):
        if not self.preview_consent.get():self.stop()
    def begin(self):
        try:self.token=self.session.start(self.preview_consent.get())
        except ReaderError as e:self.detail.set(str(e));return
        self.step=0;self.advance()
    def advance(self):
        if not self.session.active:return
        self.step+=1
        for identifier,text in [('name','葵'),('noise','DEBUG FPS 60'),('dialogue','一緒に帰りましょう。' if self.step%2 else '明日、またここで会おう。')]:
            self.session.ingest(self.token,identifier,text)
        self.rows=self.session.ranked();self.list.delete(0,'end')
        for c in self.rows:self.list.insert('end',f'{c.identifier}: {c.text}  [{self.session.reasons(c)}]')
        self.detail.set('합성 예제 갱신. 실제 게임 대사와 비교하는 단계의 체험이며 자동 전송하지 않습니다.')
    def select(self,event=None):
        indexes=self.list.curselection()
        if indexes:
            c=self.rows[indexes[0]];self.detail.set('선택한 합성 후보: '+self.session.select(c.identifier)+'\n번역·게임 프로필 저장·실제 주입은 수행하지 않습니다.')
    def stop(self):
        self.session.stop();self.list.delete(0,'end');self.detail.set('탐색 중지 · 후보/선택 버퍼를 지웠습니다.')
    def close(self):
        if self.closed:return
        self.closed=True;self.stop();self.app.pause();self.text.delete('1.0','end')
        self.app.input_window=None;self.window.destroy()
