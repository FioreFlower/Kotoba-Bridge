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
from tkinter import ttk, messagebox
from bridge import GoBridge, GoTranslator, GoStable
from study import StudyStore
from study_ui import Subtitle, StudyWindow
from core import Region, ReaderError, StableText, normalize


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


def ocr_region(region, bridge=None):
    if bridge is None:
        raise ReaderError('OCR 코어 연결이 없습니다.')
    executable=os.environ.get('TESSERACT_CMD')
    if not executable and getattr(sys, 'frozen', False):
        executable=os.path.join(os.path.dirname(sys.executable), 'ocr', 'tesseract.exe')
    if not executable:
        executable=shutil.which('tesseract')
    if not executable or not os.path.isfile(executable):
        raise ReaderError('Tesseract 실행파일 경로를 확인하세요.')
    return bridge.call('ocr', image=capture_region(region), tesseract=os.path.abspath(executable))['text']


def target_window(region):
    if sys.platform != 'win32':
        return None
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    point = wintypes.POINT(region.left + region.width//2, region.top + region.height//2)
    hwnd = user32.GetAncestor(user32.WindowFromPoint(point), 2)
    rect = wintypes.RECT()
    if not hwnd or not user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
        raise ReaderError('게임 창을 찾지 못했습니다.')
    if not (rect.left <= region.left and rect.top <= region.top and
            rect.right >= region.left+region.width and rect.bottom >= region.top+region.height):
        raise ReaderError('캡처 영역을 게임 창 내부에 지정하세요.')
    return hwnd


def check_target(hwnd, region):
    if hwnd is None:
        return
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    if user32.GetForegroundWindow() != hwnd or target_window(region) != hwnd:
        raise ReaderError('게임 창 포커스/위치 변경: 개인정보 보호를 위해 정지했습니다.')


class App:
    def __init__(self, root):
        self.root = root
        root.title('Kotoba Bridge · 일본어 → 한국어')
        root.geometry('700x570+30+30')
        root.attributes('-topmost', False)
        self.study=StudyStore()
        self.study_window=None
        self.subtitle=Subtitle(root)
        self.ready_at = 0
        self.running = False
        self.busy = False
        self.generation = 0
        self.results = queue.Queue()
        self.stop_event = threading.Event()
        self.translator = None
        self.bridge = None
        self.stable = StableText()
        self.demo = tk.BooleanVar(value=True)
        self.pro = tk.BooleanVar(value=False)
        self.consent = tk.BooleanVar(value=False)
        panel = ttk.Frame(root, padding=16)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Kotoba Bridge', font=('', 20, 'bold')).pack(anchor='w')
        ttk.Label(panel, text='창 모드 게임의 대사 영역을 지정하면 한국어 자막을 자동 갱신합니다.').pack(anchor='w', pady=6)
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
        ttk.Checkbutton(panel, text='인식된 대사와 이전 최대 3개 대사를 DeepL에 전송하는 데 동의', variable=self.consent).pack(anchor='w')
        ttk.Label(panel, text='이미지는 업로드하지 않습니다. 알림·개인정보가 영역에 들어오면 함께 인식될 수 있습니다.', wraplength=650).pack(anchor='w', pady=4)
        row = ttk.Frame(panel); row.pack(fill='x', pady=8)
        ttk.Button(row, text='시작 / 재개', command=self.start).pack(side='left')
        ttk.Button(row, text='정지 (Esc)', command=self.pause).pack(side='left', padx=6)
        ttk.Button(row, text='대화 지우기', command=self.clear).pack(side='left')
        ttk.Button(row, text='학습 / 기록', command=self.learn).pack(side='left', padx=6)
        self.status = tk.StringVar(value='준비 · 세션 최대 100회 / 10,000자 · 최소 호출 간격 3초')
        ttk.Label(panel, textvariable=self.status, wraplength=650).pack(anchor='w', pady=8)
        self.output = tk.Text(panel, height=9, wrap='word', font=('', 16), bg='#17212d', fg='#f3f6fa')
        self.output.pack(fill='both', expand=True)
        self.output.configure(state='disabled')
        root.bind('<Escape>', lambda _: self.pause())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.mode = None
        root.after(100, self.poll)

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

    def pause(self):
        self.running = False; self.stop_event.set(); self.generation += 1
        self.status.set('정지 · 진행 중인 요청은 취소되지 않을 수 있으며 결과는 버립니다.')

    def clear(self):
        self.pause()
        if self.busy:
            self.status.set('작업 종료 후 대화 지우기를 다시 눌러 주세요.'); return
        if self.translator:
            self.translator.history.clear(); self.translator.cache.clear()
        self.key.delete(0, 'end'); self.display('')
        self.status.set('대화·입력 키 삭제. 사용량 한도는 유지됩니다. 앱 종료 시 메모리 해제.')

    def start(self):
        if self.running or self.busy or self.study_window is not None:
            return
        try:
            mode = (self.demo.get(), self.pro.get())
            if not mode[0] and not self.consent.get():
                raise ReaderError('외부 전송 동의가 필요합니다.')
            region = Region(*(int(e.get()) for e in self.coords))
            if not mode[0]:
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
                self.bridge.call('configure', key=self.key.get(), pro=mode[1], demo=mode[0])
                self.translator = GoTranslator(self.bridge)
                self.mode = mode
                self.key.delete(0, 'end')
            self.target = None if mode[0] else target_window(region)
            self.ready_at = time.monotonic() + 3
            self.region = region
            self.stable = GoStable(self.bridge)
            self.stop_event = threading.Event()
            self.running = True
            self.generation += 1
            self.status.set('3초 안에 게임 창을 클릭하세요. 포커스를 잃으면 자동 정지합니다.')
        except (ValueError, ReaderError) as exc:
            messagebox.showerror('시작할 수 없음', str(exc))
        except Exception:
            messagebox.showerror('시작할 수 없음', '캡처 라이브러리 또는 디스플레이를 확인하세요.')

    def worker(self, generation, demo, stop, translator):
        try:
            if stop.is_set(): return
            if not demo: check_target(self.target, self.region)
            text = ['こんにちは。', '一緒に帰りましょう。', '明日、またここで会おう。'][int(time.monotonic()/6)%3] if demo else ocr_region(self.region, getattr(self, 'bridge', None))
            if stop.is_set(): return
            stable = self.stable.feed(text, time.monotonic())
            if stable:
                if stop.is_set(): return
                result = translator.translate(stable)
                if stop.is_set(): return
                if not demo:
                    check_target(self.target, self.region)
                    if normalize(ocr_region(self.region, getattr(self, 'bridge', None))) != stable:
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
                if kind == 'done': self.busy = False
                if generation != self.generation: continue
                if kind == 'error': self.pause(); self.status.set(text)
                if kind == 'text':
                    self.display(text)
                    source, translation = text.split('\n\n', 1)
                    self.study.record(source, translation)
                    b = self.translator.budget
                    self.status.set(f'실행 중 · 예약 사용량 {b.calls}/100회 · {b.chars}/10,000자')
        except queue.Empty:
            pass
        if self.running and not self.busy and time.monotonic() >= self.ready_at:
            window = Region(self.root.winfo_rootx(), self.root.winfo_rooty(), max(20,self.root.winfo_width()), max(20,self.root.winfo_height()))
            subtitle_region = Region(self.subtitle.window.winfo_rootx(), self.subtitle.window.winfo_rooty(), max(20,self.subtitle.window.winfo_width()), max(20,self.subtitle.window.winfo_height()))
            if not self.mode[0] and ((self.root.state() != 'iconic' and self.region.overlaps(window)) or (self.subtitle.window.state() != 'withdrawn' and self.region.overlaps(subtitle_region))):
                self.pause(); self.status.set('캡처 영역과 자막 창이 겹칩니다. 창을 옮긴 후 재개하세요.')
            elif not self.mode[0] and not self.consent.get():
                self.pause(); self.status.set('전송 동의 해제로 정지했습니다.')
            else:
                self.busy = True
                threading.Thread(target=self.worker, args=(self.generation,self.mode[0],self.stop_event,self.translator), daemon=True).start()
        self.root.after(1000, self.poll)

    def close(self):
        self.pause()
        if self.bridge: self.bridge.close()
        self.root.destroy()

if __name__ == '__main__':
    if sys.platform == 'win32':
        try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception: pass
    App(tk.Tk()).root.mainloop()
