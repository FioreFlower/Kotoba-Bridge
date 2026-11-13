import ctypes
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from study import dictionary_url


def style_matches(style, enabled):
    flags = 0x20 | 0x08000000  # WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
    return (style & flags) == (flags if enabled else 0)


def click_through(window, enabled):
    if sys.platform != 'win32':
        return False
    try:
        from ctypes import wintypes
        window.update_idletasks()
        api = ctypes.WinDLL('user32', use_last_error=True)
        api.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        api.GetAncestor.restype = wintypes.HWND
        hwnd = api.GetAncestor(window.winfo_id(), 2)
        if not hwnd:
            return False
        get = api.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else api.GetWindowLongW
        put = api.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else api.SetWindowLongW
        get.argtypes = [wintypes.HWND, ctypes.c_int]; get.restype = ctypes.c_ssize_t
        put.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]; put.restype = ctypes.c_ssize_t
        style = get(hwnd, -20)
        flags = 0x20 | 0x08000000
        ctypes.set_last_error(0)
        previous = put(hwnd, -20, (style | 0x80000 | flags) if enabled else (style & ~flags))
        if previous == 0 and ctypes.get_last_error() != 0:
            return False
        return style_matches(get(hwnd, -20), enabled)
    except (OSError, AttributeError, tk.TclError):
        return False


def replace_text(widget, value):
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    widget.insert('end', value)
    widget.configure(state='disabled')


def source_selection(widget):
    try:
        value = widget.get('sel.first', 'sel.last').strip()
    except tk.TclError:
        return ''
    return value


class Subtitle:
    def __init__(self, root):
        self.source = self.translation = ''
        self.clickthrough_ok = False
        self.window = tk.Toplevel(root)
        self.window.title('Kotoba Bridge 자막')
        self.window.geometry('650x210+750+40')
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.93)
        self.text = tk.Text(self.window, height=3, wrap='word', font=('', 16), bg='#17212d', fg='#dbe6f3', padx=12, pady=8, exportselection=False)
        self.text.pack(fill='both', expand=True)
        self.translation_text = tk.Text(self.window, height=3, wrap='word', font=('', 18), bg='#17212d', fg='#ffffff', padx=12, pady=8, exportselection=False)
        self.translation_text.pack(fill='both', expand=True)
        self.text.configure(state='disabled')
        self.translation_text.configure(state='disabled')
        self.window.protocol('WM_DELETE_WINDOW', self.window.withdraw)
        self.window.after(100, self._initial_play_mode)

    def _initial_play_mode(self):
        self.clickthrough_ok = click_through(self.window, True)

    def show(self, text):
        self.source, separator, self.translation = text.partition('\n\n')
        if not separator:
            self.translation = ''
        replace_text(self.text, self.source)
        replace_text(self.translation_text, self.translation)

    def selection_text(self):
        """Only Japanese-source pane selection is eligible for dictionary or cards."""
        return source_selection(self.text)

    def mode(self, learning):
        self.window.deiconify()
        result = click_through(self.window, not learning)
        self.clickthrough_ok = result and not learning
        return result


class StudyWindow:
    def __init__(self, app):
        self.app = app; self.store = app.study
        self.window = tk.Toplevel(app.root)
        self.window.title('학습 · 대사 기록 / 복습 (로컬)')
        self.window.geometry('820x680')
        self.window.protocol('WM_DELETE_WINDOW', self.back)
        self.review = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.window, text='저장한 복습 카드 보기', variable=self.review, command=self.refresh).pack(anchor='w')
        self.list = tk.Listbox(self.window, height=6, exportselection=False)
        self.list.pack(fill='x'); self.list.bind('<<ListboxSelect>>', self.select)
        self.term_label = tk.StringVar(value='일본어 원문 — 단어나 문장을 드래그 선택')
        ttk.Label(self.window, textvariable=self.term_label).pack(anchor='w', padx=8, pady=(8, 0))
        self.text = tk.Text(self.window, height=5, wrap='word', font=('', 15), exportselection=False)
        self.text.pack(fill='both', expand=True)
        self.text.configure(state='disabled')
        ttk.Label(self.window, text='한국어 번역 — 참고용이며 사전 뜻이 아닙니다').pack(anchor='w', padx=8)
        self.translation_text = tk.Text(self.window, height=5, wrap='word', font=('', 15), exportselection=False)
        self.translation_text.pack(fill='both', expand=True)
        self.translation_text.configure(state='disabled')
        row = ttk.Frame(self.window); row.pack(fill='x', pady=8)
        for name, command in [('선택 저장', self.save), ('선택 사전 열기', self.lookup), ('선택 카드 삭제', self.delete), ('플레이로 복귀', self.back)]:
            ttk.Button(row, text=name, command=command).pack(side='left', padx=3)
        row = ttk.Frame(self.window); row.pack(fill='x')
        for name, command in [('JSON 내보내기', self.export), ('JSON 불러오기', self.load), ('기록·카드 전체 비우기', self.clear)]:
            ttk.Button(row, text=name, command=command).pack(side='left', padx=3)
        self.status = tk.StringVar(value='기록은 메모리에만 있습니다. 다음 실행에서 복습하려면 JSON으로 내보내세요.')
        ttk.Label(self.window, textvariable=self.status, wraplength=790).pack(anchor='w', padx=8, pady=6)
        ttk.Label(self.window, text='사전은 별도 확인 후 일본어 Wiktionary를 브라우저에서 엽니다. 내장 사전·자동 독음·뜻 생성은 없습니다.\n원형이나 상용구가 아닌 선택에는 항목이 없을 수 있습니다. 내보낸 파일은 평문이며 별도 삭제해야 합니다.', wraplength=790).pack(anchor='w', padx=8, pady=4)
        self.current = None
        self.refresh()

    def refresh(self):
        self.list.delete(0, 'end')
        self.items = list(self.store.cards) if self.review.get() else list(reversed(self.store.history))
        for item in self.items:
            self.list.insert('end', item.get('term', item['source'])[:100])
        self.current = None
        replace_text(self.text, '')
        replace_text(self.translation_text, '')
        self.term_label.set('일본어 원문 — 단어나 문장을 드래그 선택')
        if self.items:
            self.list.selection_set(0)
            self.list.activate(0)
            self.select()

    def select(self, event=None):
        selected = self.list.curselection()
        if not selected:
            return
        self.current = self.items[selected[0]]
        replace_text(self.text, self.current['source'])
        replace_text(self.translation_text, self.current['translation'])
        term = self.current.get('term', '')
        self.term_label.set('저장한 표현: ' + term if term else '일본어 원문 — 단어나 문장을 드래그 선택')
        if term:
            position = self.current['source'].find(term)
            if position >= 0:
                self.text.tag_add('sel', '1.0+%dc' % position, '1.0+%dc' % (position + len(term)))
                self.text.see('1.0+%dc' % position)

    def selected(self):
        value = source_selection(self.text)
        if not value and self.current and getattr(self.app.subtitle, 'source', '') == self.current['source']:
            value = self.app.subtitle.selection_text()
        if not value:
            raise ValueError('일본어 원문에서 단어나 문장을 드래그 선택하세요. 한국어 번역은 검색하지 않습니다.')
        return value

    def save(self):
        try:
            if not self.current:
                raise ValueError('대사를 선택하세요.')
            term = self.selected()
            self.store.save(term, self.current['source'], self.current['translation'])
            self.status.set('«' + term[:60] + '» 저장됨 · 메모리 ' + str(len(self.store.cards)) + '/500개 · 다음 실행에서 보려면 JSON 내보내기')
        except ValueError as exc:
            self.status.set(str(exc))

    def lookup(self):
        try:
            term = self.selected(); url = dictionary_url(term)
            if messagebox.askyesno('사전 외부 전송', f'선택 텍스트 «{term}»를 일본어 Wiktionary URL로 전송하고 브라우저에 남깁니다. 열까요?', parent=self.window):
                if not webbrowser.open(url):
                    self.status.set('브라우저를 열지 못했습니다. 기본 브라우저 설정을 확인하세요.')
        except ValueError as exc:
            self.status.set(str(exc))

    def delete(self):
        if self.review.get() and self.current:
            self.store.cards.remove(self.current)
            self.refresh()
            self.status.set('메모리에서 카드를 삭제했습니다. 이전 내보내기 파일은 별도로 삭제하거나 다시 내보내세요.')

    def export(self):
        from onboarding import data_folder
        folder=data_folder()/'cards'
        try:folder.mkdir(parents=True,exist_ok=True)
        except OSError:
            self.status.set('복습 폴더를 만들 수 없습니다. 쓰기 가능한 위치에 압축을 풀어 주세요.');return
        path = filedialog.asksaveasfilename(parent=self.window, initialdir=str(folder), initialfile='study-cards.json', defaultextension='.json', filetypes=[('JSON', '*.json')])
        if path:
            try:
                self.store.export(path)
                self.status.set('복습 카드를 선택한 파일에 저장했습니다. 이 파일은 평문입니다.')
            except ValueError as exc:
                self.status.set(str(exc))
            except OSError:
                self.status.set('저장 실패: 파일 권한과 경로를 확인하세요. 기존 파일은 교체 성공 전까지 보존됩니다.')

    def load(self):
        from onboarding import data_folder
        path = filedialog.askopenfilename(parent=self.window, initialdir=str(data_folder()/'cards'), filetypes=[('JSON', '*.json')])
        if path and messagebox.askyesno('불러오기', '현재 메모리의 복습 카드를 파일 내용으로 바꿀까요?', parent=self.window):
            try:
                self.store.load(path); self.review.set(True); self.refresh()
                self.status.set('복습 파일을 불러왔습니다. 현재 메모리의 카드를 교체했습니다.')
            except (ValueError, OSError):
                self.status.set('불러오기 실패: 지원하는 UTF-8 복습 JSON인지 확인하세요. 기존 카드는 보존됩니다.')

    def clear(self):
        if messagebox.askyesno('로컬 기록 삭제', '메모리의 기록·카드와 번역 문맥을 비울까요? 내보낸 파일은 탐색기에서 별도 삭제해야 합니다.', parent=self.window):
            self.store.history.clear(); self.store.cards.clear(); self.app.clear(); self.refresh()
            self.status.set('메모리의 기록·카드를 비웠습니다. 내보낸 파일과 브라우저 기록은 별도입니다.')

    def back(self):
        passed = self.app.subtitle.mode(False)
        self.app.study_window = None
        self.window.destroy()
        if sys.platform == 'win32' and not passed:
            self.app.status.set('클릭 통과 설정 실패 · 자막 창을 게임 밖으로 옮기고 설정을 확인하세요.')
        else:
            self.app.status.set('플레이 모드 · 시작을 누르고 3초 안에 게임을 클릭하세요.')
