import ctypes
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from study import dictionary_url


def click_through(window, enabled):
    if sys.platform != 'win32':
        return False
    from ctypes import wintypes
    window.update_idletasks()
    api = ctypes.windll.user32
    api.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
    api.GetAncestor.restype=wintypes.HWND
    hwnd=api.GetAncestor(window.winfo_id(),2)
    get=api.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else api.GetWindowLongW
    put=api.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p)==8 else api.SetWindowLongW
    get.argtypes=[wintypes.HWND,ctypes.c_int]; get.restype=ctypes.c_ssize_t
    put.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t]; put.restype=ctypes.c_ssize_t
    style=get(hwnd,-20)
    flags=0x20 | 0x08000000  # WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
    ctypes.set_last_error(0)
    put(hwnd,-20,(style | 0x80000 | flags) if enabled else (style & ~flags))
    return bool(get(hwnd,-20)&flags)==enabled

class Subtitle:
    def __init__(self,root):
        self.window=tk.Toplevel(root)
        self.window.title('Kotoba Bridge 자막')
        self.window.geometry('650x170+750+40')
        self.window.attributes('-topmost',True)
        self.window.attributes('-alpha',0.93)
        self.text=tk.Text(self.window,wrap='word',font=('',17),bg='#17212d',fg='#ffffff',padx=12,pady=10)
        self.text.pack(fill='both',expand=True)
        self.text.configure(state='disabled')
        self.window.protocol('WM_DELETE_WINDOW',self.window.withdraw)
        self.window.after(100,lambda:click_through(self.window,True))
    def show(self,text):
        self.text.configure(state='normal'); self.text.delete('1.0','end')
        self.text.insert('end',text); self.text.configure(state='disabled')
    def mode(self,learning):
        self.window.deiconify()
        return click_through(self.window,not learning)

class StudyWindow:
    def __init__(self,app):
        self.app=app; self.store=app.study
        self.window=tk.Toplevel(app.root)
        self.window.title('학습 · 대사 기록 / 복습 (로컬)')
        self.window.geometry('800x620')
        self.window.protocol('WM_DELETE_WINDOW',self.back)
        self.review=tk.BooleanVar(value=False)
        ttk.Checkbutton(self.window,text='저장한 복습 카드 보기',variable=self.review,command=self.refresh).pack(anchor='w')
        self.list=tk.Listbox(self.window,height=8)
        self.list.pack(fill='x'); self.list.bind('<<ListboxSelect>>',self.select)
        self.text=tk.Text(self.window,height=12,wrap='word',font=('',15),exportselection=False)
        self.text.pack(fill='both',expand=True)
        self.text.configure(state='disabled')
        row=ttk.Frame(self.window); row.pack(fill='x',pady=8)
        for name,command in [('선택 저장',self.save),('선택 사전 열기',self.lookup),('선택 카드 삭제',self.delete),('플레이로 복귀',self.back)]:
            ttk.Button(row,text=name,command=command).pack(side='left',padx=3)
        row=ttk.Frame(self.window); row.pack(fill='x')
        for name,command in [('JSON 내보내기',self.export),('JSON 불러오기',self.load),('기록·카드 전체 비우기',self.clear)]:
            ttk.Button(row,text=name,command=command).pack(side='left',padx=3)
        ttk.Label(self.window,text='원문을 드래그 선택하세요. 자동 단어 분리·읽기·뜻 생성은 하지 않습니다.\n사전은 확인 후 외부 브라우저에서 열립니다. 내보낸 파일은 평문이며 자동 삭제되지 않습니다.',wraplength=760).pack(anchor='w',pady=8)
        self.current=None
        self.refresh()
    def refresh(self):
        self.list.delete(0,'end')
        self.items=self.store.cards if self.review.get() else self.store.history
        for item in self.items: self.list.insert('end',item.get('term',item['source'])[:100])
        self.current=None
    def select(self,event=None):
        selected=self.list.curselection()
        if not selected:return
        self.current=self.items[selected[0]]
        self.text.configure(state='normal'); self.text.delete('1.0','end')
        self.text.insert('end',self.current['source']+'\n\n'+self.current['translation'])
        self.text.configure(state='disabled')
    def selected(self):
        try: return self.text.get('sel.first','sel.last').strip()
        except tk.TclError: raise ValueError('대사에서 단어나 문장을 드래그 선택하세요.')
    def save(self):
        try:
            if not self.current: raise ValueError('대사를 선택하세요.')
            self.store.save(self.selected(),self.current['source'],self.current['translation'])
            messagebox.showinfo('저장','메모리에 저장했습니다. 다음 실행에서도 보려면 JSON으로 내보내세요.',parent=self.window)
        except ValueError as e: messagebox.showerror('저장',str(e),parent=self.window)
    def lookup(self):
        try:
            term=self.selected(); url=dictionary_url(term)
            if messagebox.askyesno('사전 외부 전송',f'선택 텍스트 «{term}»를 일본어 Wiktionary URL로 전송하고 브라우저에 남깁니다. 열까요?',parent=self.window):
                webbrowser.open(url)
        except ValueError as e: messagebox.showerror('사전',str(e),parent=self.window)
    def delete(self):
        if self.review.get() and self.list.curselection():
            del self.store.cards[self.list.curselection()[0]]; self.refresh()
    def export(self):
        path=filedialog.asksaveasfilename(parent=self.window,defaultextension='.json',filetypes=[('JSON','*.json')])
        if path:
            try:self.store.export(path)
            except OSError:messagebox.showerror('저장 실패','파일 권한과 경로를 확인하세요.',parent=self.window)
    def load(self):
        path=filedialog.askopenfilename(parent=self.window,filetypes=[('JSON','*.json')])
        if path and messagebox.askyesno('불러오기','현재 메모리의 복습 카드를 파일 내용으로 바꿀까요?',parent=self.window):
            try:self.store.load(path); self.review.set(True); self.refresh()
            except (ValueError,OSError,TypeError,AttributeError):messagebox.showerror('불러오기 실패','지원하는 복습 JSON인지 확인하세요.',parent=self.window)
    def clear(self):
        if messagebox.askyesno('로컬 기록 삭제','메모리의 기록·카드와 번역 문맥을 비울까요? 내보낸 파일은 탐색기에서 별도 삭제해야 합니다.',parent=self.window):
            self.store.history.clear();self.store.cards.clear();self.app.clear();self.refresh()
    def back(self):
        self.app.subtitle.mode(False)
        self.app.study_window=None
        self.window.destroy()
        self.app.status.set('플레이 모드 · 시작을 누르고 3초 안에 게임을 클릭하세요.')
