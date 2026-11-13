"""Windows-first visual novel subtitle companion. No game hooks or injection."""
import ctypes
import base64
import io
import shutil
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from bridge import GoBridge, GoTranslator, GoStable
from onboarding import find_tesseract, inspect_engine, load_settings, save_settings, settings_path
from setup_ui import RegionPicker
from study import StudyStore
from study_ui import Subtitle, StudyWindow
from core import Region, ReaderError, StableText, normalize
from ocr_feedback import preview_text, usage_label
from credentials import KeyStore, remove_legacy_keys, valid_key
from overlay_settings import load_opacity, save_opacity


def capture_region(region):
    import mss
    from PIL import Image, ImageOps
    with mss.mss() as capture:
        shot = capture.grab(vars(region))
    image = ImageOps.autocontrast(ImageOps.grayscale(Image.frombytes('RGB', shot.size, shot.rgb)))
    scale = min(2.0, (2_000_000 / (image.width * image.height)) ** 0.5)
    image = image.resize((max(1,int(image.width*scale)), max(1,int(image.height*scale))))
    buffer = io.BytesIO(); image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def ocr_region(region, bridge=None, preferred=''):
    if bridge is None:
        raise ReaderError('OCR 코어 연결이 없습니다.')
    executable=find_tesseract(preferred)
    if not executable:
        raise ReaderError('Tesseract를 찾지 못했습니다. 초기 설정에서 실행파일을 선택하세요.')
    scope=','.join(str(v) for v in (region.left,region.top,region.width,region.height))
    return bridge.call('ocr', image=capture_region(region), tesseract=executable, scope=scope)['text']



from dataclasses import dataclass

@dataclass(frozen=True)
class CaptureTarget:
    hwnd: int
    pid: int
    rect: tuple


def target_window(region):
    if sys.platform != 'win32':
        raise ReaderError('실제 게임 창 연결은 Windows에서 확인해야 합니다.')
    from ctypes import wintypes
    import os
    from live_region import ensure_physical_dpi
    ensure_physical_dpi()
    api=ctypes.windll.user32
    api.WindowFromPoint.argtypes=[wintypes.POINT];api.WindowFromPoint.restype=wintypes.HWND
    api.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];api.GetAncestor.restype=wintypes.HWND
    api.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];api.GetWindowRect.restype=wintypes.BOOL
    api.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)];api.GetWindowThreadProcessId.restype=wintypes.DWORD
    point=wintypes.POINT(region.left+region.width//2,region.top+region.height//2)
    hwnd=api.GetAncestor(api.WindowFromPoint(point),2)
    rect=wintypes.RECT();pid=wintypes.DWORD()
    if not hwnd or not api.GetWindowRect(hwnd,ctypes.byref(rect)) or not api.GetWindowThreadProcessId(hwnd,ctypes.byref(pid)):
        raise ReaderError('대사 영역의 게임 창을 찾지 못했습니다.')
    if pid.value==os.getpid():raise ReaderError('앱/자막창이 대사 영역을 가립니다. 자막을 영역 밖으로 옮기세요.')
    if not (rect.left<=region.left and rect.top<=region.top and rect.right>=region.left+region.width and rect.bottom>=region.top+region.height):
        raise ReaderError('대사 영역 전체가 게임 창 안에 있어야 합니다.')
    return CaptureTarget(int(hwnd),pid.value,(rect.left,rect.top,rect.right,rect.bottom))


def foreground_handle():
    if sys.platform!='win32':return None
    from ctypes import wintypes
    api=ctypes.windll.user32
    api.GetForegroundWindow.restype=wintypes.HWND
    return api.GetForegroundWindow()


def check_target(target,region):
    if target is None:return
    if foreground_handle()!=target.hwnd:
        raise ReaderError('게임 창 포커스 변경: 캡처/전송을 정지했습니다.')
    if target_window(region)!=target:
        raise ReaderError('게임 창 위치/크기/대상 변경 또는 가림: 캡처/전송을 정지했습니다.')


class App:
    def __init__(self, root):
        self.root = root
        root.title('Kotoba Bridge · 일본어 → 한국어')
        root.geometry('860x790+30+30')
        root.minsize(800,650)
        root.attributes('-topmost', False)
        self.key_store=KeyStore()
        self.credentials_blocked=False
        self.key_state=tk.StringVar(value="저장 키 없음 · 입력란에는 저장 키를 다시 표시하지 않습니다.")
        self.study=StudyStore()
        self.study_window=None
        self.input_window=None
        self.subtitle=Subtitle(root)
        self.ready_at = 0
        self.running = False
        self.busy = False
        self.generation = 0
        self.results = queue.Queue()
        self.stop_event = threading.Event()
        self.translator = None
        self.bridge = None
        self.engine = tk.StringVar(value=find_tesseract())
        self.engine_verified = ''
        self.monitor_index = tk.IntVar(value=0)
        self.setup_window = None
        self.region_editor=None;self.placement_editor=None
        self.restore_after_job = False
        self.usage_busy=False;self.usage_attempt=0;self.usage_revision=0
        self.stable = StableText()
        self.provider=tk.StringVar(value='DeepL')
        self.local_port=tk.StringVar(value='8087');self.local_model=tk.StringVar(value='kotoba-local')
        self.local_consent=tk.BooleanVar(value=False);self.local_window=None
        from managed_engine import ManagedEngine
        self.managed_engine=ManagedEngine();self.use_managed=False
        self.demo = tk.BooleanVar(value=True)
        self.pro = tk.BooleanVar(value=False)
        self.consent = tk.BooleanVar(value=False)
        panel = ttk.Frame(root, padding=16)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Kotoba Bridge', font=('', 20, 'bold')).pack(anchor='w')
        ttk.Label(panel, text='처음에는 오프라인 데모로 확인하세요. 실제 게임은 ① 설정 → ② 영역 → ③ OCR 미리보기 순서입니다.').pack(anchor='w', pady=6)
        onboarding=ttk.Frame(panel);onboarding.pack(fill='x',pady=4)
        for label,command in [('① 초기 설정',self.open_setup),('② 게임 위 영역 편집',self.pick_region),('③ 로컬 OCR 미리보기',self.preview),('화면 사진에서 선택',self.pick_snapshot)]:
            ttk.Button(onboarding,text=label,command=command).pack(side='left',padx=3)
        provider_row=ttk.Frame(panel);provider_row.pack(fill='x')
        ttk.Label(provider_row,text='번역 제공자').pack(side='left')
        ttk.Combobox(provider_row,textvariable=self.provider,values=['DeepL','로컬 llama.cpp'],state='readonly',width=20).pack(side='left',padx=6)
        ttk.Button(provider_row,text='로컬 모델 / 연결 설정',command=self.open_local).pack(side='left')
        ttk.Checkbutton(panel, text='오프라인 데모 (화면·API 사용 안 함)', variable=self.demo).pack(anchor='w')
        row = ttk.Frame(panel); row.pack(fill='x', pady=8)
        self.coords = []
        for name, value in [('왼쪽', '100'), ('위', '700'), ('너비', '900'), ('높이', '200')]:
            ttk.Label(row, text=name).pack(side='left')
            entry = ttk.Entry(row, width=7); entry.insert(0, value); entry.pack(side='left', padx=4)
            self.coords.append(entry)
        ttk.Label(panel, text='물리 픽셀 좌표 · 이 창과 겹치지 않게 지정 · 화면 변경 전 정지').pack(anchor='w')
        keyrow = ttk.Frame(panel); keyrow.pack(fill='x', pady=8)
        ttk.Label(keyrow, text='DeepL API 키').pack(side='left')
        self.key = ttk.Entry(keyrow, show='•', width=42); self.key.pack(side='left', padx=8)
        ttk.Checkbutton(keyrow, text='Pro', variable=self.pro).pack(side='left')
        ttk.Button(keyrow,text='암호화 저장 / 교체',command=self.save_key).pack(side='left',padx=6)
        ttk.Label(panel,textvariable=self.key_state,wraplength=800).pack(anchor='w')
        ttk.Label(panel,text='Windows 사용자별 DPAPI · PC/계정 이동용 아님 · 같은 계정의 악성 코드는 보호 범위 밖',wraplength=800).pack(anchor='w')
        ttk.Checkbutton(panel, text='인식된 대사와 이전 최대 3개 대사를 DeepL에 전송하는 데 동의', variable=self.consent).pack(anchor='w')
        ttk.Label(panel, text='이미지는 업로드하지 않습니다. 알림·개인정보가 영역에 들어오면 함께 인식될 수 있습니다.', wraplength=650).pack(anchor='w', pady=4)
        row = ttk.Frame(panel); row.pack(fill='x', pady=8)
        ttk.Button(row, text='시작 / 재개', command=self.start).pack(side='left')
        ttk.Button(row, text='정지 (앱 안에서 Esc)', command=self.pause).pack(side='left', padx=6)
        ttk.Button(row, text='대화 지우기', command=self.clear).pack(side='left')
        ttk.Button(row, text='학습 / 기록', command=self.learn).pack(side='left', padx=6)
        ttk.Button(row,text='API 키 지우기',command=self.forget_key).pack(side='left')
        input_row=ttk.Frame(panel);input_row.pack(fill='x')
        ttk.Button(input_row,text='외부 원문 붙여넣기 / 후보 선택 체험',command=self.open_input).pack(side='left')
        ttk.Button(input_row,text='실험: Textractor 후킹 입력',command=self.open_hook).pack(side='left',padx=8)
        self.status = tk.StringVar(value='준비 · 앱 안전 제한 적용 · 실제 계정 사용량은 DeepL 조회로 확인')
        self.account_usage=tk.StringVar(value='DeepL 계정 사용량 미조회 · 데모/로컬에서는 조회하지 않습니다.')
        ttk.Button(panel,text='DeepL 계정 사용량 새로고침',command=self.refresh_usage).pack(anchor='w')
        ttk.Label(panel,textvariable=self.account_usage,wraplength=800).pack(anchor='w')
        ttk.Label(panel, textvariable=self.status, wraplength=650).pack(anchor='w', pady=8)
        self.output = tk.Text(panel, height=9, wrap='word', font=('', 16), bg='#17212d', fg='#f3f6fa')
        self.output.pack(fill='both', expand=True)
        self.output.configure(state='disabled')
        root.bind('<Escape>', lambda _: self.pause())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.mode = None
        overlay_row=ttk.Frame(panel);overlay_row.pack(fill='x',pady=4,before=self.output)
        try:initial_opacity=load_opacity()
        except ReaderError:initial_opacity=85
        self.opacity_value=tk.DoubleVar(value=initial_opacity)
        self.opacity_label=tk.StringVar()
        ttk.Label(overlay_row,text='자막 배경 불투명도').pack(side='left')
        slider=ttk.Scale(overlay_row,from_=0,to=100,variable=self.opacity_value,command=self.change_opacity)
        slider.pack(side='left',padx=6)
        if not self.subtitle.separate_background:slider.configure(state='disabled')
        ttk.Label(overlay_row,textvariable=self.opacity_label).pack(side='left')
        ttk.Button(overlay_row,text='배경 설정 저장',command=self.save_overlay).pack(side='left',padx=6)
        ttk.Button(overlay_row,text='자막 위치 편집',command=self.edit_overlay).pack(side='left')
        ttk.Button(overlay_row,text='자막 위치·배경 복구',command=self.restore_overlay).pack(side='left')
        self.change_opacity(initial_opacity)
        self.demo.trace_add('write',self.invalidate_usage)
        self.pro.trace_add('write',self.invalidate_usage)
        self.consent.trace_add('write',lambda *_:self.pause() if not self.transfer_allowed() and (self.running or self.busy) else None)
        self.local_consent.trace_add('write',lambda *_:self.pause() if not self.transfer_allowed() and (self.running or self.busy) else None)
        for option in [self.provider,self.local_port,self.local_model]:option.trace_add('write',self.provider_changed)
        try:
            self.credentials_blocked=remove_legacy_keys(settings_path())
            if self.credentials_blocked:
                self.key_state.set('기존 평문 키 필드를 제거했습니다. 해당 키를 폐기/재발급하고 새 키를 저장하세요.')
            else:
                saved_key=self.key_store.load()
                if saved_key:
                    self.pro.set(saved_key[1]);self.key_state.set('저장 키 준비됨 · 입력란은 비워 둡니다. 전송 동의는 다시 필요합니다.')
                del saved_key
        except ReaderError as exc:
            self.credentials_blocked=True;self.key_state.set(str(exc))
        try:
            saved=load_settings(settings_path())
            if saved:
                region,engine=saved
                self.set_region(region);self.engine.set(engine)
                self.status.set('저장한 영역/엔진 설정을 읽었습니다. 키·전송 동의는 저장하지 않습니다.')
        except (ReaderError,OSError):
            self.status.set('저장된 설정을 읽지 못했습니다. 초기 설정에서 다시 저장하거나 삭제하세요.')
        root.after(100, self.poll)
        root.after(200,self.load_overlay_placement)

    def invalidate_usage(self,*_):
        self.usage_revision+=1
        self.account_usage.set('설정 변경 · 사용량 미조회')

    def refresh_usage(self,configure=True):
        if self.demo.get() or self.is_local():
            self.account_usage.set('데모/로컬 모드 · DeepL 사용량 조회 없음');return
        if self.usage_busy:return
        now=time.monotonic()
        if now-self.usage_attempt<60:
            return # Keep the API value and its timestamp, never fabricate a newer value.
        if configure and (self.busy or self.running):
            self.account_usage.set('번역을 정지한 뒤 수동 조회하세요. 시작 시에는 자동 조회합니다.');return
        try:
            if not self.transfer_allowed():raise ReaderError('DeepL 전송 동의 후 조회하세요.')
            if configure:
                if self.bridge is None:self.bridge=GoBridge()
                self.configure_credentials(False,self.pro.get())
        except ReaderError as e:
            self.account_usage.set('미조회 · '+str(e));return
        self.usage_attempt=now;self.usage_busy=True
        generation=self.generation;bridge=self.bridge;revision=self.usage_revision
        self.account_usage.set('DeepL 계정 사용량 조회 중 · 대사 전송 없음')
        def work():
            try:
                from account_usage import format_usage
                message=format_usage(bridge.call('usage'))
            except ReaderError as e:message='사용량 조회 실패 · '+str(e)+' · 현재 값 알 수 없음'
            except Exception:message='사용량 조회 실패 · 현재 값 알 수 없음'
            self.results.put((generation,'account_usage',(revision,message)))
        threading.Thread(target=work,daemon=True).start()

    def is_local(self):
        return hasattr(self,'provider') and self.provider.get()=='로컬 llama.cpp'

    def transfer_allowed(self):
        return self.local_consent.get() if self.is_local() else self.consent.get()

    def provider_changed(self,*_):
        self.pause();self.mode=None;self.translator=None
        self.account_usage.set('제공자/설정 변경 · 사용량 미조회')
        self.status.set('제공자/설정 변경으로 정지했습니다. 선택한 대상의 전송 동의 후 시작하세요. 자동 전환 없음.')

    def open_local(self):
        self.pause()
        if self.local_window:self.local_window.window.lift();return
        from local_ui import LocalWindow
        self.local_window=LocalWindow(self)

    def change_opacity(self,value):
        supported=self.subtitle.set_background_opacity(value)
        self.opacity_label.set(f'{round(float(value))}% · 글자 100%' if supported else 'Windows 전용 · 현재 불투명 배경')

    def save_overlay(self):
        try:
            save_opacity(self.opacity_value.get())
            self.status.set('자막 배경 설정 저장 완료 · 글자 불투명도는 항상 100%')
        except (OSError,ReaderError,ValueError):self.status.set('자막 배경 설정 저장 실패. 폴더 권한을 확인하세요.')

    def load_overlay_placement(self):
        if self.placement_editor or self.region_editor:return
        try:
            import mss
            from overlay_placement import restore_placement
            with mss.mss() as capture:monitors=list(capture.monitors[1:])
            restore_placement(self.subtitle.window,monitors)
            self.subtitle._queue_sync()
        except Exception:
            self.status.set('저장 자막 위치를 적용하지 못했습니다. 자막 위치·배경 복구를 사용하세요.')

    def edit_overlay(self):
        if self.busy or self.region_editor or self.placement_editor:return
        self.pause()
        previous=self.subtitle.learning
        try:
            import mss
            from overlay_placement import OverlayPlacementEditor
            with mss.mss() as capture:monitors=list(capture.monitors[1:])
            def finished(saved,geometry):
                self.placement_editor=None;self.subtitle.mode(previous)
                self.subtitle._queue_sync()
                self.status.set('자막 배치 저장 완료 · 번역은 정지 상태' if saved else '자막 배치 취소 · 이전 위치 복원 · 번역은 정지 상태')
            self.placement_editor=OverlayPlacementEditor(self.root,self.subtitle.window,monitors,pause=self.pause,set_interactive=lambda enabled:self.subtitle.mode(enabled),finished=finished,on_change=self.subtitle._queue_sync)
        except Exception as exc:
            self.subtitle.mode(previous)
            self.status.set(str(exc) if isinstance(exc,ReaderError) else '자막 위치 편집을 열지 못했습니다.')

    def restore_overlay(self):
        self.pause()
        if self.busy or self.placement_editor or self.region_editor:
            self.status.set('진행 중 작업/편집을 마친 뒤 자막 위치를 복구하세요.');return
        try:
            import mss
            from overlay_placement import Geometry,fit_geometry,apply_geometry,save_placement
            with mss.mss() as capture:monitors=list(capture.monitors[1:])
            geometry=fit_geometry(Geometry(),monitors)
            apply_geometry(self.subtitle.window,geometry);save_placement(geometry)
            self.subtitle.mode(False);self.opacity_value.set(85);self.change_opacity(85)
            self.status.set('자막 위치를 화면 안으로 복구·저장했습니다. 배경은 85%이며 번역은 정지 상태입니다.')
        except Exception as exc:
            self.status.set(str(exc) if isinstance(exc,ReaderError) else '자막 위치 복구 실패. 모니터와 폴더 권한을 확인하세요.')

    def open_hook(self):
        self.pause()
        if self.busy:
            self.status.set('진행 중 작업이 끝난 뒤 입력 창을 열어 주세요.');return
        if self.input_window:
            self.input_window.window.lift();return
        from hook_ui import HookWindow
        self.input_window=HookWindow(self)

    def open_input(self):
        self.pause()
        if self.busy:
            self.status.set('진행 중 작업이 끝난 뒤 입력 창을 열어 주세요.');return
        if self.input_window:
            self.input_window.window.lift();return
        from input_ui import InputWindow
        self.input_window=InputWindow(self)

    def translate_input(self,text):
        from input_sources import source_text
        text=source_text(text)
        if self.busy:raise ReaderError('진행 중 작업이 끝난 뒤 다시 눌러 주세요.')
        if not self.transfer_allowed():raise ReaderError('선택한 제공자의 전송 동의가 필요합니다.')
        self.pause()
        if self.bridge is None:self.bridge=GoBridge()
        self.configure_credentials(False,self.pro.get())
        self.key.delete(0,'end');self.mode=(False,self.pro.get())
        self.translator=GoTranslator(self.bridge)
        self.manual_context=True
        # Each reviewed paste is independent; retain session budget, clear old context.
        self.bridge.call('clear')
        self.stop_event=threading.Event();self.busy=True
        generation=self.generation;stop=self.stop_event;translator=self.translator
        def work():
            try:
                if stop.is_set():return
                translated=translator.translate(text)
                if not stop.is_set():self.results.put((generation,'text',text+'\n\n'+translated))
            except ReaderError as e:self.results.put((generation,'error',str(e)))
            except Exception:self.results.put((generation,'error','입력 번역 실패. 자동 재시도하지 않습니다.'))
            finally:self.results.put((generation,'done',''))
        threading.Thread(target=work,daemon=True).start()
        self.status.set('확인한 외부 원문 1회 번역 중 · 자동 감시 없음')

    def reset_manual_context(self):
        # A pasted line must never become context for a later screen capture.
        if getattr(self,'manual_context',False):
            self.bridge.call('clear')
            self.manual_context=False

    def local_output(self,value):
        self.output.configure(state='normal');self.output.delete('1.0','end')
        self.output.insert('end',value);self.output.configure(state='disabled')

    def set_region(self,region):
        for entry,value in zip(self.coords,(region.left,region.top,region.width,region.height)):
            entry.delete(0,'end');entry.insert(0,str(value))

    def current_region(self):
        return Region(*(int(e.get()) for e in self.coords))

    def open_setup(self):
        self.pause()
        if self.setup_window and self.setup_window.winfo_exists():
            self.setup_window.lift();return
        win=tk.Toplevel(self.root);self.setup_window=win
        win.title('초기 설정 · 로컬 점검');win.geometry('680x440')
        body=ttk.Frame(win,padding=16);body.pack(fill='both',expand=True)
        ttk.Label(body,text='1. Tesseract 일본어 OCR 설치',font=('',14,'bold')).pack(anchor='w')
        ttk.Label(body,text='OCR 포함 배포본은 엔진·일본어 모델을 함께 제공합니다. 먼저 환경 점검을 누르세요.\n개발 소스 실행 또는 손상된 배포본은 단계별 도움말을 확인하세요.',wraplength=620).pack(anchor='w',pady=8)
        def instructions():
            import webbrowser
            webbrowser.open('https://tesseract-ocr.github.io/tessdoc/Installation.html')
        ttk.Button(body,text='공식 OCR 설치 안내 열기 (브라우저)',command=instructions).pack(anchor='w')
        ttk.Button(body,text='단계별 설치 도움말 / 일본어 언어팩',command=self.ocr_help).pack(anchor='w',pady=4)
        ttk.Entry(body,textvariable=self.engine,width=75).pack(fill='x',pady=8)
        row=ttk.Frame(body);row.pack(fill='x')
        def browse():
            path=filedialog.askopenfilename(parent=win,title='설치한 tesseract.exe 선택',filetypes=[('Tesseract','*.exe'),('모든 파일','*')])
            if path:self.engine.set(path);self.engine_verified=''
        ttk.Button(row,text='OCR 실행파일 선택',command=browse).pack(side='left')
        ttk.Button(row,text='환경 점검 (전송 없음)',command=self.check_environment).pack(side='left',padx=8)
        ttk.Label(body,text='2. 사용할 모니터',font=('',12,'bold')).pack(anchor='w',pady=(16,4))
        try:
            import mss
            with mss.mss() as capture:monitors=list(capture.monitors[1:])
            options=[f'{i+1}: {m["width"]}×{m["height"]} ({m["left"]}, {m["top"]})' for i,m in enumerate(monitors)]
        except Exception:options=['디스플레이를 찾지 못했습니다. 데모는 사용 가능합니다.']
        choices=ttk.Combobox(body,state='readonly',values=options,width=65)
        choices.current(min(self.monitor_index.get(),len(options)-1));choices.pack(anchor='w')
        choices.bind('<<ComboboxSelected>>',lambda _:self.monitor_index.set(choices.current()))
        row=ttk.Frame(body);row.pack(fill='x',pady=14)
        ttk.Button(row,text='영역·엔진 설정 저장',command=self.persist_settings).pack(side='left')
        ttk.Button(row,text='저장 설정 삭제',command=self.delete_settings).pack(side='left',padx=6)
        ttk.Button(row,text='닫기',command=win.destroy).pack(side='right')
        ttk.Label(body,text='저장: 영역 좌표와 엔진 경로만. API 키·동의·대사 제외.\n설정 위치: '+str(settings_path()),wraplength=620).pack(anchor='w')

    def ocr_help(self):
        from ocr_install import format_install_guide,get_install_guide
        import webbrowser
        win=tk.Toplevel(self.root);win.title('OCR 설치 도움말 · 자동 설치 없음');win.geometry('740x620')
        text=tk.Text(win,wrap='word',padx=12,pady=12);text.pack(fill='both',expand=True)
        text.insert('1.0',format_install_guide());text.configure(state='disabled')
        for label,url in get_install_guide()['links'][:3]:
            ttk.Button(win,text=label+' (브라우저)',command=lambda url=url:webbrowser.open(url)).pack(anchor='w',padx=12,pady=3)
        ttk.Button(win,text='설치 후 OCR 다시 확인 (로컬 실행)',command=self.check_environment).pack(anchor='w',padx=12,pady=8)
        ttk.Button(win,text='닫기',command=win.destroy).pack(anchor='e',padx=12,pady=8)

    def persist_settings(self):
        try:
            save_settings(settings_path(),self.current_region(),self.engine.get())
            self.status.set('영역·엔진 경로 저장 완료. API 키와 전송 동의는 저장하지 않았습니다.')
        except (OSError,ValueError,ReaderError):self.status.set('설정 저장 실패. 영역 값과 폴더 권한을 확인하세요.')

    def delete_settings(self):
        try:
            settings_path().unlink(missing_ok=True)
            self.status.set('저장 설정 삭제 완료. 현재 화면 값과 복습 파일은 유지됩니다.')
        except OSError:self.status.set('설정 파일 삭제 권한을 확인하세요.')

    def check_environment(self,then_start=False):
        if self.busy:return
        self.pause();self.busy=True
        generation=self.generation;preferred=self.engine.get()
        self.status.set('로컬 엔진과 코어를 점검하고 있습니다. 외부 전송은 없습니다.')
        def work():
            try:
                if self.bridge is None:self.bridge=GoBridge()
                hello=self.bridge.call('hello')
                result=inspect_engine(preferred)
                result['core']=hello.get('version','?');result['then_start']=then_start
                self.results.put((generation,'diagnostics',result))
            except ReaderError as error:self.results.put((generation,'error',str(error)))
            except Exception:self.results.put((generation,'error','환경 점검 실패. 코어와 OCR 설치 경로를 확인하세요.'))
            finally:self.results.put((generation,'done',''))
        threading.Thread(target=work,daemon=True).start()

    def pick_region(self):
        if self.busy or self.region_editor or self.placement_editor:return
        self.pause()
        try:
            import mss
            from live_region import LiveRegionEditor,validate_region,ensure_physical_dpi
            ensure_physical_dpi()
            with mss.mss() as capture:monitors=list(capture.monitors[1:])
            try:initial=validate_region(self.current_region(),monitors)
            except (ValueError,ReaderError):
                monitor=monitors[min(self.monitor_index.get(),len(monitors)-1)]
                initial=Region(monitor['left'],monitor['top'],min(900,monitor['width']),min(140,monitor['height']))
            def restore():
                self.region_editor=None;self.root.deiconify()
                self.status.set('영역 편집 종료 · 번역은 정지 상태입니다.')
            def selected(region):
                try:
                    with mss.mss() as capture:current=list(capture.monitors[1:])
                    validate_region(region,current)
                    self.set_region(region);restore()
                    self.root.after(100,self.preview)
                except (ReaderError,ValueError):
                    restore();self.status.set('모니터 구성이 바뀌어 새 영역을 적용하지 않았습니다. 다시 선택하세요.')
            self.subtitle.window.withdraw();self.root.withdraw()
            self.region_editor=LiveRegionEditor(self.root,initial,monitors,selected,restore)
        except Exception as exc:
            self.root.deiconify();self.region_editor=None
            self.status.set(str(exc) if isinstance(exc,ReaderError) else '실제 화면 편집 실패. 화면 사진 선택 또는 수치 입력을 사용하세요.')

    def pick_snapshot(self):
        if self.busy:return
        self.pause()
        if self.setup_window and self.setup_window.winfo_exists():self.setup_window.destroy()
        self.root.withdraw();self.subtitle.window.withdraw()
        def restore():
            self.root.deiconify();self.subtitle.window.deiconify()
        def selected(region):
            self.set_region(region);restore()
            self.status.set('영역을 선택했습니다. 로컬 OCR 미리보기를 실행합니다. 외부 전송 없음.')
            self.root.after(100,self.preview)
        def show():
            try:
                import mss
                with mss.mss() as capture:monitors=list(capture.monitors[1:])
                if not monitors:raise ReaderError('사용할 모니터가 없습니다.')
                monitor=monitors[min(self.monitor_index.get(),len(monitors)-1)]
                RegionPicker(self.root,monitor,selected,restore)
            except Exception:
                restore();self.status.set('영역 선택 실패. 디스플레이 권한을 확인하거나 좌표를 직접 입력하세요.')
        self.root.after(350,show)

    def preview(self):
        if self.busy:return
        self.pause()
        try:region=self.current_region()
        except (ValueError,ReaderError):self.status.set('미리볼 대사 영역을 먼저 선택하세요.');return
        generation=self.generation;preferred=self.engine.get()
        self.busy=True;self.restore_after_job=True
        if self.setup_window and self.setup_window.winfo_exists():self.setup_window.destroy()
        self.root.withdraw();self.subtitle.window.withdraw()
        def work():
            try:
                if self.bridge is None:self.bridge=GoBridge()
                self.bridge.call('clear')
                text=ocr_region(region,self.bridge,preferred)
                self.results.put((generation,'preview',text))
            except ReaderError as error:self.results.put((generation,'error',str(error)))
            except Exception:self.results.put((generation,'error','OCR 미리보기 실패. 엔진/jpn 언어팩/영역을 확인하세요.'))
            finally:self.results.put((generation,'done',''))
        self.root.after(350,lambda:threading.Thread(target=work,daemon=True).start())

    def save_key(self):
        self.account_usage.set('키 변경 · 사용량 미조회')
        self.pause()
        if self.busy:
            self.status.set('진행 중 작업이 끝난 뒤 키를 저장하세요.');return
        try:
            remove_legacy_keys(settings_path())
            self.key_store.save(self.key.get(),self.pro.get())
            # Invalidate the provider only after the replacement was durably saved.
            memory_failed=False
            if self.bridge:
                try:self.bridge.call('forget_key')
                except ReaderError:
                    self.bridge.close();memory_failed=True
            self.translator=None;self.mode=None;self.key.delete(0,'end')
            self.credentials_blocked=False
            self.key_state.set('암호화 저장 완료 · 입력란을 비웠습니다. 재실행 시 같은 Windows 계정에서 사용합니다.')
            self.status.set('저장만 완료 · API 호출 없음 · 기존 세션 사용량 유지' if not memory_failed else '키는 저장했지만 코어 연결이 끊겼습니다. 앱을 재실행하세요. 새 세션 한도가 적용됩니다.')
        except ReaderError as exc:
            self.key_state.set(str(exc))

    def configure_credentials(self,demo,pro):
        if demo:
            # Demo must never decrypt, send, or consume a typed key.
            self.bridge.call('configure',key='',pro=pro,demo=True);return
        if self.is_local():
            if not self.local_consent.get():raise ReaderError('로컬 서버 전송 동의가 필요합니다.')
            if getattr(self,'use_managed',False):options=self.managed_engine.configuration()
            else:
                try:port=int(self.local_port.get())
                except ValueError:raise ReaderError('로컬 포트는 숫자여야 합니다.') from None
                options=dict(local_port=port,local_model=self.local_model.get(),local_token='')
            self.bridge.call('configure',provider='local',key='',demo=False,**options)
            return
        if getattr(self,'credentials_blocked',False):
            raise ReaderError('저장 키/기존 설정 확인이 필요합니다. 새 키를 암호화 저장하거나 API 키 지우기를 누르세요.')
        key=self.key.get().strip()
        if key:key=valid_key(key)
        elif getattr(self,'mode',None)!=(False,pro) or getattr(self,'translator',None) is None:
            saved=self.key_store.load()
            if saved:
                key,saved_pro=saved
                if saved_pro!=pro:
                    raise ReaderError('저장된 키의 Free/Pro 종류와 다릅니다. 맞는 종류로 되돌리거나 키를 교체 저장하세요.')
        self.bridge.call('configure',key=key,pro=pro,demo=False)
        self.key.delete(0,'end')

    def forget_key(self):
        self.account_usage.set('키 삭제 · 사용량 미조회')
        self.pause()
        if self.busy:
            self.status.set('진행 중 작업이 끝난 뒤 키를 삭제하세요.');return
        self.key.delete(0,'end');self.consent.set(False)
        self.translator=None;self.mode=None
        memory_failed=False
        try:
            if self.bridge:self.bridge.call('forget_key')
        except ReaderError:
            self.bridge.close();memory_failed=True
        try:
            self.key_store.delete()
            remove_legacy_keys(settings_path())
            self.credentials_blocked=False
            self.key_state.set('저장 키 삭제됨 · 이전 복사본/백업은 별도로 삭제하세요.')
            self.display('')
            self.status.set('키 삭제 완료 · 세션 사용량 유지' if not memory_failed else '키 삭제 완료 · 오류가 난 코어를 종료했습니다. 앱을 재실행하세요.')
        except ReaderError as exc:
            self.credentials_blocked=True;self.key_state.set(str(exc))

    def learn(self):
        self.pause()
        if self.busy:
            self.status.set('작업 종료 후 학습을 다시 눌러 주세요.'); return
        self.subtitle.mode(True)
        if self.study_window is None:
            self.study_window=StudyWindow(self)
        else:
            self.study_window.window.lift()

    def display(self, value):
        self.subtitle.show(value)
        self.output.configure(state='normal'); self.output.delete('1.0', 'end')
        self.output.insert('end', value); self.output.configure(state='disabled')

    def start_if_current(self, generation):
        # An engine-check callback queued before Esc/stop may not restart later.
        if generation == self.generation:self.start()

    def pause(self):
        self.running = False; self.stop_event.set(); self.generation += 1
        self.status.set('정지 · 진행 중인 요청은 취소되지 않을 수 있으며 결과는 버립니다.')

    def clear(self):
        self.pause()
        if self.busy:
            self.status.set('작업 종료 후 대화 지우기를 다시 눌러 주세요.'); return
        try:
            if self.bridge:self.bridge.call('clear')
        except ReaderError:
            self.status.set('코어 연결 중단. 앱을 재실행하세요.');return
        self.key.delete(0, 'end'); self.display('')
        self.status.set('대화·입력 키 삭제. 사용량 한도는 유지됩니다. 앱 종료 시 메모리 해제.')

    def start(self):
        if self.running or self.busy or self.study_window is not None or self.input_window is not None or self.region_editor is not None or self.placement_editor is not None:
            return
        try:
            mode = (self.demo.get(), self.pro.get())
            if not mode[0] and not self.transfer_allowed():
                raise ReaderError('외부 전송 동의가 필요합니다.')
            region = self.current_region()
            if not mode[0]:
                engine=find_tesseract(self.engine.get())
                if not engine or self.engine_verified!=engine:
                    self.check_environment(then_start=True);return
                self.active_engine=engine
                import mss
                with mss.mss() as sct:
                    monitors = sct.monitors[1:]
                if not any(region.left >= m['left'] and region.top >= m['top'] and
                           region.left+region.width <= m['left']+m['width'] and
                           region.top+region.height <= m['top']+m['height'] for m in monitors):
                    raise ReaderError('영역이 한 모니터 안에 완전히 들어가야 합니다.')
            if self.translator is None or self.mode != mode or (not mode[0] and self.key.get().strip()):
                if self.bridge is None:
                    self.bridge = GoBridge()
                self.configure_credentials(mode[0],mode[1])
                self.translator = GoTranslator(self.bridge)
                self.mode = mode
                if not mode[0]:self.key.delete(0, 'end')
            self.reset_manual_context()
            self.region = region
            self.stable = GoStable(self.bridge)
            self.stop_event = threading.Event()
            self.generation += 1
            generation=self.generation
            if not mode[0] and not self.is_local():self.refresh_usage(configure=False)
            if mode[0]:
                self.target=None;self.running=True;self.ready_at=time.monotonic()+1
                self.status.set('오프라인 데모 실행 중 · 외부 전송 없음')
            else:
                # Remove the control window before resolving the game underneath ROI.
                if self.setup_window and self.setup_window.winfo_exists():self.setup_window.destroy()
                self.busy=True;self.root.iconify();self.subtitle.window.withdraw()
                self.status.set('게임 창을 클릭하세요. 최대 15초 동안 포커스를 확인하며 캡처/번역하지 않습니다.')
                deadline=time.monotonic()+15
                self.root.after(350,lambda:self.arm_game(generation,region,deadline))

        except (ValueError, ReaderError) as exc:
            messagebox.showerror('시작할 수 없음', str(exc))
        except Exception:
            messagebox.showerror('시작할 수 없음', '캡처 라이브러리 또는 디스플레이를 확인하세요.')

    def arm_game(self,generation,region,deadline,candidate=None,shown=False,since=None):
        if generation!=self.generation:
            self.busy=False;return
        try:
            if time.monotonic()>=deadline:
                raise ReaderError('게임 창 연결 시간 초과: 캡처/번역을 시작하지 않았습니다. 대사 영역·자막 겹침을 확인하고 다시 시작하세요.')
            try:
                chosen=candidate or target_window(region)
                check_target(chosen,region)
            except ReaderError:
                self.root.after(200,lambda:self.arm_game(generation,region,deadline,candidate,shown,None));return
            if not shown:
                before=foreground_handle()
                if sys.platform=='win32' and not self.subtitle.mode(False):
                    raise ReaderError('클릭 통과를 설정하지 못해 시작하지 않았습니다.')
                self.focus_transition=(before,foreground_handle()) # memory only, no titles or screenshots
                self.root.after(200,lambda:self.arm_game(generation,region,deadline,chosen,True,None));return
            now=time.monotonic()
            if since is None or now-since<0.6:
                self.root.after(200,lambda:self.arm_game(generation,region,deadline,chosen,True,now if since is None else since));return
            self.target=chosen;self.busy=False;self.running=True;self.ready_at=now+0.3
            self.status.set('게임 창 연결 완료 · 포커스/위치 변경 시 즉시 정지합니다.')
        except ReaderError as error:
            self.busy=False;self.root.deiconify();self.pause();self.status.set(str(error))

    def worker(self, generation, demo, stop, translator):
        try:
            if stop.is_set(): return
            if not demo: check_target(self.target, self.region)
            text = ['こんにちは。', '一緒に帰りましょう。', '明日、またここで会おう。'][int(time.monotonic()/6)%3] if demo else ocr_region(self.region, getattr(self, 'bridge', None), getattr(self, 'active_engine', ''))
            if stop.is_set(): return
            stable = self.stable.feed(text, time.monotonic())
            if stable:
                if stop.is_set(): return
                if not demo and getattr(self,'bridge',None):
                    remaining=self.bridge.call('status').get('retry_after_ms',0)/1000
                    if remaining>0:
                        if stop.wait(min(remaining,3.1)):return
                        check_target(self.target,self.region)
                        if normalize(ocr_region(self.region,self.bridge,getattr(self,'active_engine',''))) != stable:
                            self.stable=GoStable(self.bridge);return
                    check_target(self.target,self.region)
                if stop.is_set():return
                result = translator.translate(stable)
                if stop.is_set(): return
                if not demo:
                    check_target(self.target, self.region)
                    if normalize(ocr_region(self.region, getattr(self, 'bridge', None), getattr(self, 'active_engine', ''))) != stable:
                        self.stable = GoStable(self.bridge) if getattr(self, 'bridge', None) else StableText()
                        return
                self.results.put((generation, 'text', stable+'\n\n'+result))
        except ReaderError as exc:
            self.results.put((generation, 'error', str(exc)))
        except Exception:
            self.results.put((generation, 'error', '캡처/OCR 실패: Tesseract 경로, jpn 언어팩, 화면 권한을 확인하세요.'))
        finally:
            self.results.put((generation, 'done', ''))

    def poll(self):
        try:
            while True:
                generation, kind, text = self.results.get_nowait()
                if kind == 'account_usage':
                    self.usage_busy=False
                    if generation==self.generation and text[0]==self.usage_revision and not self.demo.get() and not self.is_local():self.account_usage.set(text[1])
                    else:self.account_usage.set('모드/상태 변경으로 조회 결과 폐기 · 미조회')
                    continue
                if kind == 'done':
                    self.busy = False
                    if self.restore_after_job:
                        self.restore_after_job=False;self.root.deiconify();self.subtitle.window.deiconify()
                if generation != self.generation: continue
                if kind == 'error': self.pause(); self.status.set(text)
                if kind == 'diagnostics':
                    self.engine_verified=text['path'] if text['ok'] else ''
                    self.status.set(text['detail'])
                    self.local_output(f"Go 코어 {text['core']}: 연결 확인\n{text['detail']}\n\n외부 전송/유료 API 호출 없이 점검했습니다.")
                    if text['ok']:
                        self.engine.set(text['path'])
                        if text['then_start']:self.root.after(0,lambda g=generation:self.start_if_current(g))
                if kind == 'preview':
                    self.local_output(preview_text(text))
                    self.status.set('원본과 후보를 비교하세요. 배경 문자가 섞이면 대사 줄만 다시 선택하세요. 후보는 자동 번역에 적용하지 않습니다.')
                if kind == 'text':
                    self.display(text)
                    source, translation = text.split('\n\n', 1)
                    self.study.record(source, translation)
                    b = self.translator.budget
                    self.status.set(usage_label(b.calls,b.chars,demo=bool(self.mode and self.mode[0]),local=self.is_local()))
        except queue.Empty:
            pass
        if self.running and not self.busy and time.monotonic() >= self.ready_at:
            window = Region(self.root.winfo_rootx(), self.root.winfo_rooty(), max(20,self.root.winfo_width()), max(20,self.root.winfo_height()))
            subtitle_region = Region(self.subtitle.window.winfo_rootx(), self.subtitle.window.winfo_rooty(), max(20,self.subtitle.window.winfo_width()), max(20,self.subtitle.window.winfo_height()))
            if not self.mode[0] and ((self.root.state() != 'iconic' and self.region.overlaps(window)) or (self.subtitle.window.state() != 'withdrawn' and self.region.overlaps(subtitle_region))):
                self.pause(); self.status.set('캡처 영역과 자막 창이 겹칩니다. 창을 옮긴 후 재개하세요.')
            elif not self.mode[0] and not self.transfer_allowed():
                self.pause(); self.status.set('전송 동의 해제로 정지했습니다.')
            else:
                self.busy = True
                threading.Thread(target=self.worker, args=(self.generation,self.mode[0],self.stop_event,self.translator), daemon=True).start()
        self.root.after(1000, self.poll)

    def close(self):
        self.pause()
        if self.input_window:self.input_window.close()
        for editor in [getattr(self,'region_editor',None),getattr(self,'placement_editor',None)]:
            try:
                if editor:editor.cancel()
            except (ReaderError,tk.TclError):pass
        if getattr(self,'local_window',None):self.local_window.close()
        try:
            if getattr(self,'managed_engine',None):self.managed_engine.stop()
        except ReaderError as exc:
            self.status.set(str(exc));return
        if self.bridge: self.bridge.close()
        self.root.destroy()

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--manage-models',action='store_true');parser.add_argument('--self-test',action='store_true');parser.add_argument('--report');parser.add_argument('--require-ocr',action='store_true')
    args=parser.parse_args()
    if args.self_test:
        from selftest import run
        raise SystemExit(run(args.report,require_ocr=args.require_ocr))
    if sys.platform == 'win32':
        try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception: pass
    app=App(tk.Tk())
    if args.manage_models:
        app.manage_models_only=True;app.root.withdraw();app.subtitle.window.withdraw();app.open_local()
    app.root.mainloop()
