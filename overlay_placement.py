"""Explicit subtitle placement editing; persisted coordinates never contain screen data.

Geometry is outer-window x/y in virtual-desktop physical coordinates plus Tk client
width/height. Windows uses SetWindowPos for absolute negative monitor coordinates.
"""
from dataclasses import asdict, dataclass
import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import ttk

from core import ReaderError

MIN_WIDTH, MIN_HEIGHT = 240, 120
MAX_WIDTH, MAX_HEIGHT = 3840, 2160
MAX_COORDINATE = 100_000


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('잘못된 자막 위치 또는 크기입니다.')
    return value


@dataclass(frozen=True)
class Geometry:
    x: int = 40
    y: int = 80
    width: int = 650
    height: int = 210

    def __post_init__(self):
        _integer(self.x, -MAX_COORDINATE, MAX_COORDINATE)
        _integer(self.y, -MAX_COORDINATE, MAX_COORDINATE)
        _integer(self.width, MIN_WIDTH, MAX_WIDTH)
        _integer(self.height, MIN_HEIGHT, MAX_HEIGHT)


@dataclass(frozen=True)
class Monitor:
    left: int
    top: int
    width: int
    height: int

    def __post_init__(self):
        _integer(self.left, -MAX_COORDINATE, MAX_COORDINATE)
        _integer(self.top, -MAX_COORDINATE, MAX_COORDINATE)
        _integer(self.width, MIN_WIDTH, MAX_COORDINATE)
        _integer(self.height, MIN_HEIGHT, MAX_COORDINATE)


def monitor_list(monitors):
    """Accept physical MSS monitor dictionaries (exclude MSS virtual index zero)."""
    if not isinstance(monitors, (list, tuple)) or not 1 <= len(monitors) <= 32:
        raise ValueError('사용 가능한 모니터 정보가 없습니다.')
    result = []
    for value in monitors:
        if isinstance(value, Monitor):
            result.append(value)
        elif isinstance(value, dict):
            try:
                result.append(Monitor(**{key: value[key] for key in ('left', 'top', 'width', 'height')}))
            except (KeyError, TypeError) as exc:
                raise ValueError('잘못된 모니터 정보입니다.') from exc
        else:
            raise ValueError('잘못된 모니터 정보입니다.')
    return result


def intersection_area(geometry, monitor):
    width = max(0, min(geometry.x + geometry.width, monitor.left + monitor.width) - max(geometry.x, monitor.left))
    height = max(0, min(geometry.y + geometry.height, monitor.top + monitor.height) - max(geometry.y, monitor.top))
    return width * height


def fit_geometry(geometry, monitors, preferred_index=0):
    """Recover a window onto the monitor with greatest overlap, never into a gap."""
    if not isinstance(geometry, Geometry):
        raise ValueError('잘못된 자막 위치입니다.')
    screens = monitor_list(monitors)
    _integer(preferred_index, 0, len(screens) - 1)
    areas = [intersection_area(geometry, monitor) for monitor in screens]
    index = areas.index(max(areas)) if max(areas) else preferred_index
    screen = screens[index]
    width, height = min(geometry.width, screen.width), min(geometry.height, screen.height)
    if not max(areas):
        x = screen.left + min(40, screen.width - width)
        y = screen.top + min(80, screen.height - height)
    else:
        x = max(screen.left, min(geometry.x, screen.left + screen.width - width))
        y = max(screen.top, min(geometry.y, screen.top + screen.height - height))
    return Geometry(x, y, width, height)


def moved(geometry, dx, dy):
    return Geometry(max(-MAX_COORDINATE, min(MAX_COORDINATE, geometry.x + int(dx))),
                    max(-MAX_COORDINATE, min(MAX_COORDINATE, geometry.y + int(dy))),
                    geometry.width, geometry.height)


def resized(geometry, dx, dy):
    return Geometry(geometry.x, geometry.y,
                    max(MIN_WIDTH, min(MAX_WIDTH, geometry.width + int(dx))),
                    max(MIN_HEIGHT, min(MAX_HEIGHT, geometry.height + int(dy))))


def preference_path():
    from onboarding import data_folder
    return data_folder() / 'overlay-placement.json'


def load_placement(path=None):
    target = Path(path) if path is not None else preference_path()
    try:
        if not target.exists():
            return Geometry()
        with target.open('rb') as file:
            raw = file.read(2049)
        if len(raw) > 2048:
            raise ValueError()
        value = json.loads(raw)
        if (not isinstance(value, dict) or set(value) != {'version', 'x', 'y', 'width', 'height'}
                or type(value['version']) is not int or value['version'] != 1):
            raise ValueError()
        return Geometry(**{key: value[key] for key in ('x', 'y', 'width', 'height')})
    except (OSError, ValueError, TypeError):
        raise ReaderError('자막 위치 설정을 읽지 못했습니다. 기본 위치로 복구한 뒤 다시 저장하세요.') from None


def save_placement(geometry, path=None):
    if not isinstance(geometry, Geometry):
        raise ValueError('잘못된 자막 위치입니다.')
    target = Path(path) if path is not None else preference_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix='.overlay-placement-', suffix='.tmp', delete=False) as file:
            temporary = Path(file.name)
            json.dump(dict(version=1, **asdict(geometry)), file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def require_physical_coordinates():
    """Do not silently mix Tk logical coordinates and Win32 physical coordinates.

    The application must establish per-monitor DPI awareness before constructing Tk.
    Changing process awareness here after windows exist would be unsafe.
    """
    if sys.platform != 'win32':
        return
    try:
        api = ctypes.WinDLL('user32', use_last_error=True)
        api.GetThreadDpiAwarenessContext.argtypes = []
        api.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        api.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        api.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
        if api.GetAwarenessFromDpiAwarenessContext(api.GetThreadDpiAwarenessContext()) != 2:
            raise ReaderError('자막 위치 편집에는 모니터별 DPI 인식이 필요합니다. 앱을 완전히 종료한 뒤 다시 실행하세요.')
    except (OSError, AttributeError):
        raise ReaderError('모니터별 DPI 인식 상태를 확인하지 못해 자막 이동을 중지했습니다.') from None


def _windows_api(window):
    from ctypes import wintypes
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    api.GetAncestor.restype = wintypes.HWND
    hwnd = api.GetAncestor(window.winfo_id(), 2)
    if not hwnd:
        raise ReaderError('자막 창 핸들을 확인하지 못했습니다.')
    return api, hwnd


def window_geometry(window):
    require_physical_coordinates()
    window.update_idletasks()
    x, y = window.winfo_x(), window.winfo_y()
    if sys.platform == 'win32':
        from ctypes import wintypes
        api, hwnd = _windows_api(window)
        api.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        api.GetWindowRect.restype = wintypes.BOOL
        rectangle = wintypes.RECT()
        if not api.GetWindowRect(hwnd, ctypes.byref(rectangle)):
            raise ReaderError('자막 창의 현재 위치를 읽지 못했습니다.')
        x, y = rectangle.left, rectangle.top
    return Geometry(int(x), int(y), max(MIN_WIDTH, min(MAX_WIDTH, window.winfo_width())),
                    max(MIN_HEIGHT, min(MAX_HEIGHT, window.winfo_height())))


def _tk_axis(coordinate, length, screen_length):
    # Tk negative offsets mean distance from the opposite edge, not absolute x/y.
    return '+' + str(coordinate) if coordinate >= 0 else '-' + str(screen_length - length - coordinate)


def apply_geometry(window, geometry):
    """Apply a validated placement without changing opacity or play/learn mode."""
    if not isinstance(geometry, Geometry):
        raise ValueError('잘못된 자막 위치입니다.')
    require_physical_coordinates()
    window.geometry(f'{geometry.width}x{geometry.height}')
    window.update_idletasks()
    if sys.platform == 'win32':
        from ctypes import wintypes
        api, hwnd = _windows_api(window)
        api.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wintypes.UINT]
        api.SetWindowPos.restype = wintypes.BOOL
        # Keep size/z-order/activation; move to absolute virtual-desktop coordinates.
        if not api.SetWindowPos(hwnd, None, geometry.x, geometry.y, 0, 0, 0x0001 | 0x0004 | 0x0010):
            raise ReaderError('자막 창을 이동하지 못했습니다.')
    else:
        window.geometry(f'{geometry.width}x{geometry.height}' +
                        _tk_axis(geometry.x, geometry.width, window.winfo_screenwidth()) +
                        _tk_axis(geometry.y, geometry.height, window.winfo_screenheight()))


def restore_placement(window, monitors, path=None):
    geometry = fit_geometry(load_placement(path), monitors)
    apply_geometry(window, geometry)
    return geometry


class OverlayPlacementEditor:
    """Temporary explicit drag/resize controls; parent must reject a busy worker.

    pause() stops capture. set_interactive(True) must make the subtitle interactive
    and return True before controls are attached. finished(saved, geometry) restores
    the parent's chosen play/learning mode; it must not resume capture automatically.
    """
    def __init__(self, root, window, monitors, *, pause, set_interactive, finished,
                 path=None, on_change=None):
        self.monitors = monitor_list(monitors)
        self.window, self.path = window, path
        self.finished, self.on_change = finished, on_change or (lambda: None)
        self.closed = False
        self.gesture = None
        self.original = window_geometry(window)
        pause()
        if not set_interactive(True):
            raise ReaderError('자막을 편집 모드로 바꾸지 못했습니다. 클릭 통과 설정을 확인하세요.')
        self.dialog = tk.Toplevel(root)
        self.dialog.title('자막 위치 · 크기 편집')
        self.dialog.geometry('580x300')
        self.dialog.attributes('-topmost', True)
        self.dialog.protocol('WM_DELETE_WINDOW', self.cancel)
        self.dialog.bind('<Escape>', lambda event: self.cancel())
        ttk.Label(self.dialog, text='자막 위의 파란 이동 막대를 드래그하세요.\n아래 크기 막대는 가로·세로 크기를 바꿉니다. 편집 중 번역은 정지됩니다.',
                  wraplength=540).pack(anchor='w', padx=12, pady=10)
        row = ttk.Frame(self.dialog); row.pack(fill='x', padx=12)
        self.entries = {}
        for key, label in [('x', '왼쪽'), ('y', '위'), ('width', '너비'), ('height', '높이')]:
            ttk.Label(row, text=label).pack(side='left')
            entry = ttk.Entry(row, width=7); entry.pack(side='left', padx=4)
            self.entries[key] = entry
        self.status = tk.StringVar(value='저장할 때만 위치 파일을 바꿉니다. 취소하면 이전 위치로 돌아갑니다.')
        ttk.Label(self.dialog, textvariable=self.status, wraplength=540).pack(anchor='w', padx=12, pady=10)
        row = ttk.Frame(self.dialog); row.pack(fill='x', padx=12, pady=6)
        for label, command in [('숫자로 적용', self.apply_entries), ('화면 안으로 복구', self.recover),
                               ('배치 저장', self.save), ('취소', self.cancel)]:
            ttk.Button(row, text=label, command=command).pack(side='left', padx=3)
        first = window.pack_slaves()
        self.drag_handle = tk.Label(window, text='↔ 자막 위치 편집: 이 막대를 드래그',
                                    bg='#2455a4', fg='white', cursor='fleur', pady=7)
        self.drag_handle.pack(side='top', fill='x', before=first[0] if first else None)
        self.resize_handle = tk.Label(window, text='↘ 이 막대를 드래그하여 크기 조절',
                                      bg='#2455a4', fg='white', cursor='sizing', pady=4)
        self.resize_handle.pack(side='bottom', fill='x')
        for handle, action in [(self.drag_handle, 'move'), (self.resize_handle, 'resize')]:
            handle.bind('<ButtonPress-1>', lambda event, name=action: self.begin(event, name))
            handle.bind('<B1-Motion>', self.drag)
            handle.bind('<ButtonRelease-1>', self.end)
        self.current = fit_geometry(self.original, self.monitors)
        self._apply(self.current)
        self.window.deiconify()
        self.window.lift()
        self.dialog.lift()

    def _fields(self, geometry):
        for key, value in asdict(geometry).items():
            self.entries[key].delete(0, 'end'); self.entries[key].insert(0, str(value))

    def _apply(self, geometry):
        apply_geometry(self.window, geometry)
        self.current = geometry
        self._fields(geometry)
        self.on_change()

    def begin(self, event, action):
        self.gesture = (action, event.x_root, event.y_root, window_geometry(self.window))
        return 'break'

    def drag(self, event):
        if self.gesture is not None:
            action, x, y, origin = self.gesture
            change = moved if action == 'move' else resized
            try:
                self._apply(change(origin, event.x_root - x, event.y_root - y))
            except (ValueError, ReaderError, tk.TclError) as exc:
                self.status.set(str(exc))
        return 'break'

    def end(self, event):
        self.gesture = None
        self.recover()
        return 'break'

    def apply_entries(self):
        try:
            geometry = Geometry(**{key: int(entry.get()) for key, entry in self.entries.items()})
            self._apply(fit_geometry(geometry, self.monitors))
            self.status.set('현재 화면에 적용했습니다. 배치 저장을 눌러 다음 실행에도 사용하세요.')
        except (ValueError, ReaderError, tk.TclError):
            self.status.set('위치·크기를 확인하세요. 최소 크기는 240×120, 최대 크기는 3840×2160입니다.')

    def recover(self):
        try:
            self._apply(fit_geometry(window_geometry(self.window), self.monitors))
            self.status.set('연결된 모니터 안으로 복구했습니다. 배치 저장을 눌러 확정하세요.')
        except (ValueError, ReaderError, tk.TclError) as exc:
            self.status.set(str(exc))

    def save(self):
        try:
            geometry = fit_geometry(window_geometry(self.window), self.monitors)
            self._apply(geometry)
            save_placement(geometry, self.path)
            self._close(True, geometry)
        except (OSError, ValueError, ReaderError, tk.TclError):
            self.status.set('위치 저장 실패: 폴더 쓰기 권한을 확인하세요. 기존 설정은 유지됩니다.')

    def cancel(self):
        geometry = fit_geometry(self.original, self.monitors)
        try:
            self._apply(geometry)
        finally:
            self._close(False, geometry)

    def _close(self, saved, geometry):
        if self.closed:
            return
        self.closed = True
        self.drag_handle.destroy(); self.resize_handle.destroy()
        self.dialog.destroy()
        self.on_change()
        self.finished(saved, geometry)
