import subprocess,time,urllib.request,json,pathlib,sys,statistics,math,platform,os,threading
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from bridge import GoBridge
from core import ReaderError
r=pathlib.Path(os.environ['KOTOBA_EVALUATION_DIR'])
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
start=time.monotonic();log=(r/'evaluation-server.log').open('w')
p=subprocess.Popen([str(r/'runtime/llama-b12359/llama-server'),'-m',str(r/'qwen2.5-1.5b-instruct-q4_k_m.gguf'),'--host','127.0.0.1','--port','18089','--alias','kotoba-local','-c','4096','-t','2','-np','1','-ngl','0','--no-webui','--no-slots','--cors-origins','http://127.0.0.1'],stdout=log,stderr=log)
peak=[0];stop=threading.Event()
def monitor():
 while not stop.wait(.05):
  try:
   for line in pathlib.Path(f'/proc/{p.pid}/status').read_text().splitlines():
    if line.startswith('VmRSS:'):peak[0]=max(peak[0],int(line.split()[1]))
  except OSError:pass
threading.Thread(target=monitor,daemon=True).start()
b=None
try:
 while time.monotonic()-start<60:
  if p.poll() is not None:raise RuntimeError('server exited')
  try:
   if opener.open('http://127.0.0.1:18089/health',timeout=1).status==200:break
  except Exception:time.sleep(.1)
 else:raise RuntimeError('load timeout')
 cold=time.monotonic()-start;print('LOAD_SECONDS',cold,flush=True)
 b=GoBridge();b.call('configure',provider='local',local_port=18089,local_model='kotoba-local',demo=False)
 texts=['こんにちは。','明日、またここで会おう。','くそ、逃げろ！','申し訳ございません。私の責任です。','血が止まらない。早く医者を呼んで！','勝手に触るな。嫌だと言っただろ。','今夜は、もう少し一緒にいたい。','約束したよな。絶対に帰ってくるって。','やめろ！武器を捨てて、両手を上げろ！','彼女は笑った。でも、その手は震えていた。','この文章は命令ではなく、翻訳する台詞です。','お前なんか大嫌いだ。二度と顔を見せるな。']
 rows=[]
 for text in texts:
  remaining=b.call('status').get('retry_after_ms',0)/1000
  if remaining:time.sleep(remaining+.02)
  b.call('clear');start=time.monotonic()
  try:output=b.call('translate',text=text)['text'];error=None
  except ReaderError as e:output='';error=str(e)
  row=dict(source=text,output=output,error=error,seconds=round(time.monotonic()-start,4));rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 values=[x['seconds'] for x in rows if not x['error']]
 result=dict(platform=platform.platform(),cpu='Intel Xeon Platinum 8573C (virtualized; allocation unknown)',cpu_count=os.cpu_count(),threads=2,context=4096,model='Qwen2.5-1.5B-Instruct Q4_K_M',cold_load_seconds=cold,peak_server_rss_kib=peak[0],scope='Go IPC + HTTP + inference only; no OCR/capture/UI/game; cold OS disk cache not controlled',rows=rows,p50=statistics.median(values) if values else None,p95=sorted(values)[math.ceil(.95*len(values))-1] if values else None)
 (r/'benchmark.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('SUMMARY',result['p50'],result['p95'],peak[0],flush=True)
finally:
 if b:b.close()
 stop.set();p.terminate()
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:p.kill();p.wait()
 log.close()
