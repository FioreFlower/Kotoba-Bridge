"""Explicit live region editing. No screen capture, persistence, or network access."""
import sys
from core import Region, ReaderError

FIELDS = ('left', 'top', 'width', 'height')
HANDLES = ('move', 'nw', 'ne', 'sw', 'se')


def real_monitors(monitors):
    """Copy actual monitor rectangles. Caller must omit mss aggregate monitor[0]."""
    result = []
    for monitor in monitors:
        values = tuple(monitor[key] for key in FIELDS)
        if any(type(value) is not int for value in values):
            raise ReaderError('모니터 좌표는 정수 물리 픽셀이어야 합니다.')
        if values[2] <= 0 or values[3] <= 0:
            raise ReaderError('모니터 크기가 올바르지 않습니다.')
        result.append(dict(zip(FIELDS, values)))
    if not result:
        raise ReaderError('실제 모니터를 찾을 수 없습니다.')
    return tuple(result)


def validate_region(region, monitors):
    values = tuple(getattr(region, field) for field in FIELDS)
    if any(type(value) is not int for value in values):
        raise ReaderError('좌표와 크기는 정수 물리 픽셀이어야 합니다.')
    Region(*values)  # Reuse the capture size limits.
    for monitor in real_monitors(monitors):
        if (region.left >= monitor['left'] and region.top >= monitor['top'] and
                region.left + region.width <= monitor['left'] + monitor['width'] and
                region.top + region.height <= monitor['top'] + monitor['height']):
            return region
    raise ReaderError('영역 전체를 한 모니터 안에 두세요. 화면 밖·모니터 사이 빈 공간은 사용할 수 없습니다.')


def parse_region(values, monitors):
    if len(values) != 4:
        raise ReaderError('왼쪽·위쪽·너비·높이를 모두 입력하세요.')
    try:
        if any(not isinstance(value, str) for value in values):
            raise ValueError()
        numbers = [int(value.strip(), 10) for value in values]
        region = Region(*numbers)
    except (ValueError, TypeError):
        raise ReaderError('좌표와 크기에 정수를 입력하세요.') from None
    return validate_region(region, monitors)


def drag_region(start, dx, dy, handle, monitors):
    """Use absolute pointer delta from drag start, never cumulative deltas/scales."""
    if handle not in HANDLES or type(dx) is not int or type(dy) is not int:
        raise ReaderError('올바르지 않은 영역 이동입니다.')
    left, top, width, height = (getattr(start, field) for field in FIELDS)
    if handle == 'move':
        left += dx
        top += dy
    else:
        right, bottom = left + width, top + height
        if 'w' in handle:
            left = max(right - 3840, min(right - 20, left + dx))
        else:
            right = min(left + 3840, max(left + 20, right + dx))
        if 'n' in handle:
            top = max(bottom - 2160, min(bottom - 20, top + dy))
        else:
            bottom = min(top + 2160, max(top + 20, bottom + dy))
        width, height = right - left, bottom - top
    return validate_region(Region(left, top, width, height), monitors)


class RegionEditSession:
    """Draft-only transaction. Invalid changes and cancellation preserve the original."""
    def __init__(self, initial, monitors):
        self.monitors = real_monitors(monitors)
        self.original = validate_region(initial, self.monitors)
        self.current = initial
        self.closed = False

    def update(self, region):
        if self.closed:
            raise ReaderError('이미 닫힌 영역 편집입니다.')
        self.current = validate_region(region, self.monitors)
        return self.current

    def finish(self, accept):
        if self.closed:
            raise ReaderError('이미 닫힌 영역 편집입니다.')
        self.closed = True
        return self.current if accept else self.original


def ensure_physical_dpi():
    """Require current thread per-monitor awareness; never change process settings.

    Call on the same UI thread before any physical GetWindowRect/monitor placement.
    """
    if sys.platform != 'win32':
        raise ReaderError('실화면 영역 편집은 Windows에서 지원합니다. 미리보기 선택을 이용하세요.')
    import ctypes
    try:
        api = ctypes.WinDLL('user32', use_last_error=True)
        api.GetThreadDpiAwarenessContext.argtypes = []
        api.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        api.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        api.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
        awareness = api.GetAwarenessFromDpiAwarenessContext(api.GetThreadDpiAwarenessContext())
    except (AttributeError, OSError):
        raise ReaderError('Windows DPI 상태를 확인하지 못했습니다. 미리보기 선택을 이용하세요.') from None
    if awareness != 2:
        raise ReaderError('물리 좌표용 DPI 설정을 확인할 수 없습니다. 앱을 다시 시작하거나 미리보기 선택을 이용하세요.')
    return True


class _PhysicalWindows:
    def __init__(self):
        ensure_physical_dpi()  # fail before any physical-coordinate UI operation
        import ctypes
        from ctypes import wintypes
        self.ctypes, self.types = ctypes, wintypes
        self.api = ctypes.WinDLL('user32', use_last_error=True)
        self.api.GetThreadDpiAwarenessContext.argtypes = []
        self.api.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        self.api.GetPhysicalCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        self.api.GetPhysicalCursorPos.restype = wintypes.BOOL
        self.api.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.api.GetAncestor.restype = wintypes.HWND
        self.api.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                         ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.api.SetWindowPos.restype = wintypes.BOOL

    def cursor(self):
        point = self.types.POINT()
        if not self.api.GetPhysicalCursorPos(self.ctypes.byref(point)):
            raise ReaderError('마우스 물리 좌표를 읽지 못했습니다.')
        return point.x, point.y

    def place(self, window, rectangle):
        window.update_idletasks()
        hwnd = self.api.GetAncestor(window.winfo_id(), 2)  # GA_ROOT, Tk wrapper HWND
        if not hwnd or not self.api.SetWindowPos(hwnd, self.types.HWND(-1), *rectangle, 0x0010 | 0x0040):
            raise ReaderError('영역 테두리를 화면에 배치하지 못했습니다.')


class LiveRegionEditor:
    """Caller MUST pause capture/translation before constructing; callbacks never resume it.

    monitors: physical mss.monitors[1:] dictionaries, not the virtual bounding rectangle.
    on_select receives one immutable Region; on_cancel takes no arguments.
    """
    def __init__(self, root, initial, monitors, on_select, on_cancel):
        import tkinter as tk
        from tkinter import ttk
        self.session = RegionEditSession(initial, monitors)
        self.native = _PhysicalWindows()  # fail before creating any UI
        self.tk, self.root = tk, root
        self.on_select, self.on_cancel = on_select, on_cancel
        self.closed = False
        self.parts = []
        self.drag_start = None
        self.window = tk.Toplevel(root)
        try:
            self.window.title('게임 위 대사 영역 편집 · 캡처 일시정지')
            self.window.attributes('-topmost', True)
            self.window.resizable(False, False)
            self.window.protocol('WM_DELETE_WINDOW', self.cancel)
            self.window.bind('<Escape>', lambda _: self.cancel())
            self.window.bind('<Destroy>', self._destroyed)
            ttk.Label(self.window, text='테두리: 이동 · 모서리: 크기 조절 · Esc: 취소\n게임은 창 모드/테두리 없는 창 모드를 사용하세요.\n수치는 물리 픽셀입니다. 한 모니터 안에서 선택하세요.').pack(padx=12, pady=8)
            inputs = ttk.Frame(self.window)
            inputs.pack(padx=12)
            self.values = []
            for index, label in enumerate(('왼쪽 X', '위쪽 Y', '너비', '높이')):
                ttk.Label(inputs, text=label).grid(row=0, column=index, padx=3)
                value = tk.StringVar()
                entry = ttk.Entry(inputs, textvariable=value, width=10)
                entry.grid(row=1, column=index, padx=3)
                entry.bind('<Return>', lambda _: self.apply_values())
                self.values.append(value)
            self.status = tk.StringVar(value='확정 전에는 기존 캡처 영역을 변경하지 않습니다.')
            ttk.Label(self.window, textvariable=self.status, wraplength=430).pack(padx=12, pady=8)
            buttons = ttk.Frame(self.window)
            buttons.pack(pady=(0, 10))
            for label, command in [('수치 적용', self.apply_values), ('이 영역 확정', self.confirm), ('취소', self.cancel)]:
                ttk.Button(buttons, text=label, command=command).pack(side='left', padx=4)
            for handle in ('move', 'move', 'move', 'move', 'nw', 'ne', 'sw', 'se'):
                part = tk.Toplevel(root)
                part.withdraw()
                part.overrideredirect(True)
                part.configure(background='#26dfa5', cursor='fleur' if handle == 'move' else 'sizing')
                part.bind('<ButtonPress-1>', lambda event, h=handle: self._press(h))
                part.bind('<B1-Motion>', self._drag)
                part.bind('<ButtonRelease-1>', self._release)
                part.bind('<Escape>', lambda _: self.cancel())
                self.parts.append(part)
            self._render()
            self.window.lift()
        except Exception:
            self.closed = True
            self._cleanup()
            raise

    def _render(self):
        region = self.session.current
        x, y, w, h = (getattr(region, field) for field in FIELDS)
        # All strips/handles lie inside the requested region; the center has no window.
        rectangles = [(x, y, w, 4), (x, y+h-4, w, 4), (x, y, 4, h), (x+w-4, y, 4, h),
                      (x, y, 10, 10), (x+w-10, y, 10, 10), (x, y+h-10, 10, 10), (x+w-10, y+h-10, 10, 10)]
        for part, rectangle in zip(self.parts, rectangles):
            part.deiconify()
            self.native.place(part, rectangle)
        for variable, field in zip(self.values, FIELDS):
            variable.set(str(getattr(region, field)))

    def _press(self, handle):
        try:
            self.drag_start = (self.session.current, self.native.cursor(), handle)
        except ReaderError as error:
            self.status.set(str(error))

    def _drag(self, _event=None):
        if self.closed or self.drag_start is None:
            return
        try:
            initial, (x, y), handle = self.drag_start
            px, py = self.native.cursor()
            self.session.update(drag_region(initial, px-x, py-y, handle, self.session.monitors))
            self._render()
            self.status.set('초록 테두리는 편집 중인 영역입니다. 확정하거나 취소하세요.')
        except ReaderError as error:
            self.status.set(str(error))

    def _release(self, event=None):
        self._drag(event)
        self.drag_start = None

    def apply_values(self):
        if self.closed:
            return False
        try:
            self.session.update(parse_region([value.get() for value in self.values], self.session.monitors))
            self._render()
            self.status.set('수치를 편집 테두리에 적용했습니다. 확정 전에는 저장하지 않습니다.')
            return True
        except ReaderError as error:
            self.status.set(str(error))
            return False

    def confirm(self):
        if self.closed or not self.apply_values():
            return
        result = self.session.finish(True)
        self.closed = True
        self._cleanup()
        self.on_select(result)

    def cancel(self):
        if self.closed:
            return
        self.session.finish(False)
        self.closed = True
        self._cleanup()
        self.on_cancel()

    def _destroyed(self, event):
        if event.widget is self.window and not self.closed:
            self.cancel()

    def _cleanup(self):
        for window in self.parts + [self.window]:
            try:
                window.destroy()
            except self.tk.TclError:
                pass
