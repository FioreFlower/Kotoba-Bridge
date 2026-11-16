"""Small native setup dialogs. Screenshot preview stays in memory and on this PC."""
import tkinter as tk
from tkinter import ttk,messagebox
from onboarding import region_from_drag
from ocr_feedback import region_hint

class RegionPicker:
    def __init__(self,root,monitor,on_select,on_cancel):
        import mss
        from PIL import Image,ImageTk
        self.monitor=monitor;self.on_select=on_select;self.on_cancel=on_cancel
        with mss.mss() as capture:shot=capture.grab(monitor)
        bitmap=Image.frombytes('RGB',shot.size,shot.rgb)
        # Use a local snapshot instead of transparent physical-coordinate overlays.
        bitmap.thumbnail((min(1000,root.winfo_screenwidth()-100),min(580,root.winfo_screenheight()-180)))
        self.size=bitmap.size
        self.window=tk.Toplevel(root);self.window.title('대사 영역 선택 · 로컬 미리보기')
        self.window.attributes('-topmost',True)
        ttk.Label(self.window,text='게임 전체가 아닌 대사 글자 줄을 작은 여백과 함께 선택하세요. 배경·메뉴·이름 칸은 필요할 때만 포함하세요.\n선택 후 로컬 OCR을 미리봅니다. 화면 미리보기는 외부 전송·저장되지 않습니다.').pack(padx=12,pady=8)
        self.canvas=tk.Canvas(self.window,width=bitmap.width,height=bitmap.height,highlightthickness=0,cursor='crosshair')
        self.image=ImageTk.PhotoImage(bitmap)
        self.canvas.create_image(0,0,anchor='nw',image=self.image);self.canvas.pack(padx=12)
        self.status=tk.StringVar(value='Esc: 취소 · 20×20픽셀 이상 선택')
        ttk.Label(self.window,textvariable=self.status).pack(pady=8)
        row=ttk.Frame(self.window);row.pack(pady=8)
        ttk.Button(row,text='이 영역 사용',command=self.confirm).pack(side='left',padx=6)
        ttk.Button(row,text='취소',command=self.cancel).pack(side='left')
        self.origin=None;self.end=None;self.box=None
        self.canvas.bind('<ButtonPress-1>',self.press);self.canvas.bind('<B1-Motion>',self.drag);self.canvas.bind('<ButtonRelease-1>',self.drag)
        self.window.bind('<Escape>',lambda _:self.cancel());self.window.protocol('WM_DELETE_WINDOW',self.cancel)
    def press(self,event):
        self.origin=(event.x,event.y);self.end=self.origin
        if self.box:self.canvas.delete(self.box)
        self.box=self.canvas.create_rectangle(event.x,event.y,event.x,event.y,outline='#32dbab',width=3)
    def drag(self,event):
        if self.origin is None:return
        self.end=(event.x,event.y);self.canvas.coords(self.box,*self.origin,*self.end)
        try:
            r=region_from_drag(self.origin,self.end,self.size,self.monitor)
            self.status.set(region_hint(r,self.monitor))
        except Exception:self.status.set('영역을 조금 더 크게 선택하세요.')
    def confirm(self):
        try:
            if self.origin is None:raise ValueError()
            region=region_from_drag(self.origin,self.end,self.size,self.monitor)
        except Exception:
            self.status.set('20×20픽셀 이상의 대사 영역을 드래그하세요.');return
        self.window.destroy();self.on_select(region)
    def cancel(self):
        self.window.destroy();self.on_cancel()
