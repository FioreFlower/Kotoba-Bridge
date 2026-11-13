"""Experimental local provider setup. Model download is explicit, never automatic."""
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox
from local_models import MODEL_NAME,MODEL_BYTES,LICENSE_URL,install_model,model_path,MODELS,spec,delete_model,local_server_present
from core import ReaderError
from local_runtime import install_runtime, runtime_path

class LocalWindow:
    def __init__(self,app):
        self.app=app;self.cancel=threading.Event();self.events=queue.Queue();self.busy=False
        w=self.window=tk.Toplevel(app.root);w.title('로컬 번역 설정 · 실험 기능');w.geometry('800x700')
        outer=ttk.Frame(w);outer.pack(fill='both',expand=True)
        canvas=tk.Canvas(outer,highlightthickness=0);scroll=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview)
        scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True);canvas.configure(yscrollcommand=scroll.set)
        f=ttk.Frame(canvas,padding=16);content=canvas.create_window((0,0),window=f,anchor='nw')
        f.bind('<Configure>',lambda _:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda event:canvas.itemconfigure(content,width=event.width))
        ttk.Label(f,text='로컬 번역 · 외부 API 자동 전환 없음',font=('',16,'bold')).pack(anchor='w')
        ttk.Label(f,text='공식 Windows CPU 엔진을 아래 버튼으로 설치할 수 있습니다. 자동 서버 실행은 아직 제공하지 않습니다.\n서버를 직접 설치·관리할 수 있는 시험 사용자용입니다.',wraplength=700).pack(anchor='w',pady=8)
        row=ttk.Frame(f);row.pack(fill='x')
        ttk.Label(row,text='127.0.0.1 포트').pack(side='left');ttk.Entry(row,textvariable=app.local_port,width=8).pack(side='left',padx=6)
        ttk.Label(row,text='모델 별칭').pack(side='left');ttk.Entry(row,textvariable=app.local_model,width=30).pack(side='left',padx=6)
        ttk.Checkbutton(f,text='대사를 이 PC의 로컬 서버로 보내는 데 동의 (서버의 저장/외부 전송 정책은 직접 확인)',variable=app.local_consent).pack(anchor='w',pady=8)
        ttk.Label(f,text='아래에서 모델을 고르세요. 기본 추천 모델은 아직 없습니다.\n파일 크기와 RAM 사용량은 다릅니다. 무조건 무검열/정확도/즉시 번역 보장 없음.\n서버에 선택 모델을 로드하고 별칭을 kotoba-local로 지정하세요.',wraplength=700).pack(anchor='w')
        t=tk.Text(f,height=4,wrap='word');t.pack(fill='x',pady=6);t.insert('end','라이선스: '+LICENSE_URL+'\n저장 위치: '+str(model_path()));t.configure(state='disabled')
        self.model_id=tk.StringVar(value='qwen25-1.5b')
        ttk.Combobox(f,textvariable=self.model_id,values=list(MODELS),state='readonly').pack(anchor='w')
        self.details=tk.StringVar();ttk.Label(f,textvariable=self.details,wraplength=700).pack(anchor='w')
        self.model_id.trace_add('write',lambda *_:self.describe());self.describe()
        self.accept=tk.BooleanVar(value=False)
        ttk.Checkbutton(f,text='위 모델 라이선스 확인 및 선택 모델의 표시된 크기 다운로드에 동의',variable=self.accept).pack(anchor='w')
        if not getattr(app,'manage_models_only',False):
            ttk.Button(f,text='고정 모델 다운로드 / 무결성 확인',command=self.download).pack(anchor='w',pady=6)
            ttk.Button(f,text='Windows CPU 엔진 설치 / 무결성 확인 (25.1 MB)',command=self.prepare_runtime).pack(anchor='w',pady=6)
        else:
            ttk.Label(f,text='제거 준비: 선택 모델만 즉시 삭제합니다. 프로그램 제거를 나중에 취소해도 모델 삭제는 되돌리지 않습니다.\nAPI 키·설정·복습 카드: 보존. 이 창을 닫으면 프로그램 제거를 계속합니다.',wraplength=700).pack(anchor='w',pady=6)
        self.status=tk.StringVar(value='자동 다운로드 없음 · 설치 후에는 모델 다운로드용 인터넷 연결이 필요 없습니다.')
        ttk.Label(f,textvariable=self.status,wraplength=700).pack(anchor='w')
        ttk.Button(f,text='선택 모델 제거 (카드·키·설정 유지)',command=self.remove).pack(anchor='w',pady=4)
        ttk.Button(f,text='닫기 / 다운로드 취소',command=self.close).pack(anchor='w',pady=8)
        w.protocol('WM_DELETE_WINDOW',self.close);w.after(200,self.poll)
    def describe(self):
        item=spec(self.model_id.get());p=model_path(self.model_id.get())
        self.details.set(f"{item['name']} · {item['bytes']:,} bytes · {'파일 있음 (해시 미확인)' if p.is_file() else '미설치'}\n{item['memory']}\n{item['measured']}\n사용 상태: 외부 서버의 실제 로드 모델은 앱에서 확인할 수 없음 · 로컬 제공자 선택 여부: {self.app.is_local()}\nCPU 사용 가능, GPU 필수 아님 · 모두 Apache-2.0\n라이선스: {item['repo']}/blob/{item['revision']}/LICENSE")
        if hasattr(self,'accept'):self.accept.set(False)
    def remove(self):
        if self.busy:return
        if not messagebox.askyesno('모델만 삭제','외부 로컬 서버를 먼저 종료하세요. 선택 모델 파일만 삭제하고 키·설정·복습 카드는 유지합니다. 계속할까요?',parent=self.window):return
        try:
            delete_model(self.model_id.get(),in_use=self.app.is_local() or self.app.busy or self.app.running or local_server_present(self.app.local_port.get()))
            self.status.set('모델 파일 삭제 완료 · 다시 다운로드할 수 있습니다.');self.describe()
        except ReaderError as e:self.status.set(str(e))
    def download(self):
        if self.busy:return
        if not self.accept.get():messagebox.showerror('확인 필요','모델 라이선스와 다운로드 크기를 확인하고 동의하세요.',parent=self.window);return
        selected=self.model_id.get()
        self.busy=True;self.status.set('다운로드/검증 중 · 느린 연결에서는 시간이 걸립니다.')
        def work():
            try:
                p=install_model(accepted=True,model_id=selected,cancel=self.cancel,progress=lambda n,total:self.events.put(f'다운로드 {n*100//total}%'))
                self.events.put('검증 완료: '+str(p)+' · 서버에서 이 모델을 직접 로드하세요.')
            except ReaderError as e:self.events.put(str(e))
            finally:self.events.put(None)
        threading.Thread(target=work,daemon=True).start()
    def prepare_runtime(self):
        if self.busy:return
        if not messagebox.askyesno('공식 엔진 설치 확인','llama.cpp b12359 Windows x64 CPU 엔진 (약 25.1 MB, 압축 해제 약 64.6 MB)을 GitHub 공식 배포에서 받습니다. MIT 및 LLVM OpenMP 고지를 보존합니다. 고정 SHA-256 검증 후 설치하며 실행하지 않습니다.\n출처: https://github.com/ggml-org/llama.cpp/releases/tag/b12359\n라이선스: https://github.com/ggml-org/llama.cpp/blob/b12359/LICENSE\n저장 위치: '+str(runtime_path())+'\n다운로드 및 라이선스 확인에 동의하나요?',parent=self.window):return
        self.busy=True;self.status.set('공식 엔진 다운로드/검증 중 · 자동 실행 없음')
        def work():
            try:
                path=install_runtime(accepted=True,cancel=self.cancel,progress=lambda n,total:self.events.put(f'엔진 다운로드 {n*100//total}%'))
                self.events.put('엔진 준비 완료: '+str(path)+' · 서버 자동 실행은 아직 미구현입니다.')
            except ReaderError as e:self.events.put(str(e))
            finally:self.events.put(None)
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        if not self.window.winfo_exists():return
        try:
            while True:
                item=self.events.get_nowait()
                if item is None:self.busy=False
                else:self.status.set(item)
        except queue.Empty:pass
        self.window.after(200,self.poll)
    def close(self):
        self.cancel.set();self.window.destroy();self.app.local_window=None
        if getattr(self.app,'manage_models_only',False):
            self.app.manage_models_only=False;self.app.close()
