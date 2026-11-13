"""Experimental real CLI input UI. No automatic engine installation or broad hook search."""
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from core import ReaderError
from hook_cli import CliSession
from hook_stream import HookStream
from hook_processes import visible_processes,identity,foreground_pid

class HookWindow:
    def __init__(self,app):
        self.app=app;self.client=CliSession();self.stream=HookStream();self.closed=False;self.rows=[];self.processes=[]
        self.window=tk.Toplevel(app.root);self.window.title('실험: Textractor CLI 후킹 입력')
        self.window.geometry('850x700');self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.window.bind('<Escape>',lambda _:self.stop())
        panel=ttk.Frame(self.window,padding=12);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='별도 Textractor 5.2.0 CLI · 실제 게임 호환성 미검증',font=('',14,'bold')).pack(anchor='w')
        ttk.Label(panel,text='오프라인 게임만 선택하세요. 온라인/안티치트 게임에는 사용하지 마세요.\n연결은 게임 메모리에 후크를 설치하므로 충돌/미저장 진행 손실 가능성이 있습니다. 먼저 저장하세요.\n구형 엔진의 내부 통신 권한 한계와 클립보드 로컬 읽기가 있습니다. 관리자 승격·보안 예외를 요구하면 중단하세요.',wraplength=810).pack(anchor='w',pady=6)
        ttk.Button(panel,text='실행 중 창의 프로세스 목록 갱신 (주입 없음)',command=self.refresh).pack(anchor='w')
        self.games=tk.Listbox(panel,height=5,exportselection=False);self.games.pack(fill='x')
        self.games.bind('<<ListboxSelect>>',self.process_selected)
        self.folder=tk.StringVar()
        ttk.Button(panel,text='별도로 설치한 TextractorCLI.exe 선택',command=self.choose_cli).pack(anchor='w')
        ttk.Label(panel,textvariable=self.folder,wraplength=810).pack(anchor='w')
        self.consent=tk.BooleanVar(value=False)
        ttk.Checkbutton(panel,text='선택한 게임에만 연결하는 위험을 확인했습니다 (API 전송 동의와 별개)',variable=self.consent,command=self.consent_changed).pack(anchor='w')
        bar=ttk.Frame(panel);bar.pack(fill='x')
        ttk.Button(bar,text='선택 게임 연결 · 후보 수신',command=self.connect).pack(side='left')
        ttk.Button(bar,text='입력 중지 / 연결 해제 요청',command=self.stop).pack(side='left',padx=8)
        self.status=tk.StringVar(value='동봉/자동 설치 없음. 공식 CLI·DLL 해시가 일치하는 경우만 실행합니다.')
        ttk.Label(panel,textvariable=self.status,wraplength=810).pack(anchor='w',pady=8)
        ttk.Label(panel,text='게임 대사를 넘기면 엔진이 보내는 후보가 갱신됩니다. 추천은 참고이며 자동 선택하지 않습니다.').pack(anchor='w')
        self.list=tk.Listbox(panel,height=7,exportselection=False);self.list.pack(fill='both',expand=True)
        self.list.bind('<<ListboxSelect>>',self.select)
        self.preview=tk.Text(panel,height=4,wrap='word',state='disabled');self.preview.pack(fill='x')
        translate_bar=ttk.Frame(panel);translate_bar.pack(fill='x',pady=6)
        ttk.Button(translate_bar,text='선택 원문 1회 번역',command=self.translate).pack(side='left')
        ttk.Button(translate_bar,text='선택 후보 연속 번역 켜기',command=self.begin_stream).pack(side='left',padx=8)
        ttk.Button(translate_bar,text='연속 번역 정지',command=self.pause_stream).pack(side='left')
        ttk.Label(panel,text='자동 후보 수신은 로컬 전용입니다. 번역은 선택한 제공자와 기존 세션 한도를 사용합니다.\n광범위 메모리 탐색·후킹코드 입력·자동 재시도·게임별 프로필 저장은 아직 제공하지 않습니다.',wraplength=810).pack(anchor='w')
        ttk.Button(panel,text='닫고 OCR로 복귀 (자동 시작 안 함)',command=self.close).pack(anchor='e')
        self.window.after(200,self.poll)
    def refresh(self):
        if self.client.process:self.status.set('연결을 먼저 해제하세요.');return
        self.consent.set(False)
        try:
            self.processes=visible_processes();self.games.delete(0,'end')
            for p in self.processes:self.games.insert('end',f'{Path(p.path).name} · PID {p.pid} · {p.arch} · {p.path}')
        except ReaderError as e:self.status.set(str(e))
    def process_selected(self,event=None):
        self.consent.set(False)
        if self.client.process:self.stop()
    def choose_cli(self):
        if self.client.process:self.status.set('연결을 먼저 해제하세요.');return
        name=filedialog.askopenfilename(parent=self.window,title='공식 TextractorCLI.exe',filetypes=[('Textractor CLI','TextractorCLI.exe')])
        if name:self.folder.set(str(Path(name).parent));self.consent.set(False)
    def consent_changed(self):
        if not self.consent.get() and self.client.process:self.stop()
    def connect(self):
        try:
            selected=self.games.curselection()
            if not selected:raise ReaderError('게임 프로세스를 직접 선택하세요.')
            if not self.consent.get():raise ReaderError('위험 고지와 선택 게임 연결 동의가 필요합니다.')
            target=self.processes[selected[0]]
            if not messagebox.askyesno('선택한 게임에 실제 후킹 연결',f'{Path(target.path).name}\nPID {target.pid} · {target.arch}\n\n저장한 오프라인 게임이 맞습니까? 외부 엔진을 실행해 이 프로세스에 후크를 설치합니다. 게임 호환성과 정상 해제를 보장하지 않습니다.',parent=self.window):return
            self.client.connect(self.folder.get(),target,identity,True)
            self.status.set('연결 요청됨 · 게임에서 대사를 넘기세요. 후보 수신 전에는 성공으로 확인하지 않습니다.')
        except ReaderError as e:self.status.set(str(e))
    def poll(self):
        if self.closed:return
        try:
            if self.client.drain():
                selected=self.client.candidates.selected
                old=next((c.text for c in self.rows if c.identifier==selected),None)
                self.rows=self.client.candidates.ranked();self.list.delete(0,'end')
                for i,c in enumerate(self.rows):
                    self.list.insert('end',f'{c.identifier}: {c.text[:140]} [{self.client.candidates.reasons(c)}]')
                    if c.identifier==selected:
                        self.list.selection_set(i)
                        if old!=c.text:
                            if self.stream.active:
                                self.stream.update(selected,c.text,time.monotonic());self.app.pause(notify_input=False)
                            else:self.app.pause()
                        self.show(c.text)
                if not self.stream.active:self.status.set(f'실제 CLI 후보 {len(self.rows)}개 수신 · 정확성은 게임 대사와 비교하세요.')
            self.tick_stream()
        except ReaderError as e:
            reason=str(e);self.stop();self.status.set(reason+' · 후크 제거 확인 불가. OCR로 복귀할 수 있습니다.')
        self.window.after(200,self.poll)
    def on_app_pause(self):
        if self.stream.active:
            self.stream.stop()
            self.status.set('연속 번역 정지 · 후보 미리보기는 계속됩니다. 재개는 직접 켜세요.')
    def pause_stream(self):
        self.on_app_pause();self.app.pause()
    def begin_stream(self):
        try:
            if self.app.busy:raise ReaderError('진행 중 작업이 끝난 뒤 시작하세요.')
            self.client.drain();session=self.client.candidates
            if not session.selected:raise ReaderError('게임 대사 후보를 먼저 선택하세요.')
            if self.app.demo.get():raise ReaderError('실제 후킹 번역은 데모를 해제하고 제공자 전송 동의 후 켜세요.')
            if not self.app.transfer_allowed():raise ReaderError('선택한 번역 제공자 전송 동의가 필요합니다.')
            identifier=session.selected;text=session.select(identifier)
            if not messagebox.askyesno('선택 후보 연속 전송 동의',f'이 후보의 새 대사를 {self.app.provider.get()}에 계속 보냅니다. API 비용이 발생할 수 있습니다.\n\n{text}\n\n게임이 전경일 때만 전송하며 정지/오류/후보 변경 시 자동 재개하지 않습니다. 시작할까요?',parent=self.window):return
            self.client.confirmed_text(identifier,text)
            self.app.pause();self.app.translator=None;self.app.mode=None
            self.stream.start(identifier,text)
            self.status.set('15초 안에 선택한 게임으로 돌아가세요. 앱/입력 창의 정지 또는 Esc로 중지합니다.')
        except ReaderError as e:self.status.set(str(e))
    def tick_stream(self):
        if not self.stream.active:return
        try:
            if self.app.demo.get() or not self.app.transfer_allowed():raise ReaderError('모드/전송 동의 변경으로 중지했습니다.')
            session=self.client.candidates
            if session.selected!=self.stream.selected:raise ReaderError('후보 변경으로 중지했습니다.')
            current=session.select(session.selected)
            if self.stream.update(session.selected,current,time.monotonic()):self.app.pause(notify_input=False)
            text=self.stream.ready(time.monotonic(),foreground_pid()==self.client.target.pid,self.app.busy)
            if text is not None:
                self.app.translate_input(text,automatic=True,guard=lambda:self.stream_guard(text))
                self.status.set('연속 번역 중 · 최신 대사만 대기 · 0.6초 안정화 / 최소 3초 간격')
        except ReaderError as e:
            self.stream.stop();self.app.pause();self.status.set(str(e)+' · 자동 재시도 없음')
    def stream_guard(self,text):
        try:
            target=self.client.target
            return (self.stream.accepts(text) and self.client.candidates.selected==self.stream.selected
                    and identity(target.pid)==target and foreground_pid()==target.pid)
        except (ReaderError,AttributeError):return False
    def accept_result(self,text):
        try:
            self.client.drain()
            session=self.client.candidates
            if session.selected!=self.stream.selected or session.select(session.selected)!=text:return False
            return self.stream_guard(text)
        except ReaderError:
            self.stop();return False

    def show(self,text):
        self.preview.configure(state='normal');self.preview.delete('1.0','end');self.preview.insert('1.0',text);self.preview.configure(state='disabled')
    def select(self,event=None):
        indices=self.list.curselection()
        if indices:
            identifier=self.rows[indices[0]].identifier
            if identifier!=self.client.candidates.selected:self.app.pause()
            self.show(self.client.candidates.select(identifier))
    def translate(self):
        try:
            self.client.drain() # Check live identity before transmitting any selected text.
            session=self.client.candidates
            if not session.selected:raise ReaderError('실제 대사 후보를 먼저 선택하세요.')
            identifier=session.selected;text=session.select(identifier)
            provider=self.app.provider.get()
            if not messagebox.askyesno('번역 전송 확인',f'선택 원문을 {provider} 제공자에 1회 전송합니다.\n\n{text}\n\n개인정보가 없고 게임 대사가 맞습니까?',parent=self.window):return
            self.app.translate_input(self.client.confirmed_text(identifier,text))
        except ReaderError as e:self.status.set(str(e))
    def stop(self):
        self.app.pause();self.status.set(self.client.close());self.list.delete(0,'end');self.rows=[];self.show('');self.consent.set(False)
    def close(self):
        if self.closed:return
        self.closed=True;self.stop();self.app.input_window=None;self.window.destroy()
