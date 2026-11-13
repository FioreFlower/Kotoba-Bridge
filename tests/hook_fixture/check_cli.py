"""Authorized Windows CI-only test; attaches solely to our newly created fixture.
Never discovers or attaches to pre-existing processes. No API/network calls here.
"""
import argparse,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from hook_cli import CliSession,verify_cli
from hook_processes import identity
p=argparse.ArgumentParser();p.add_argument('--engine',required=True);p.add_argument('--fixture',required=True);p.add_argument('--report',required=True);a=p.parse_args()
exe=verify_cli(Path(a.engine).resolve(),'x64')
# First smoke: empty stdin, so no attach/detach/hook commands can be issued.
r=subprocess.run([str(exe)],input='',encoding='utf-16-le',stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,cwd=exe.parent)
assert r.returncode==0 and 'Usage:' in r.stdout
fixture=subprocess.Popen([str(Path(a.fixture).resolve())]);client=CliSession();report={'engine':'official Textractor 5.2.0 x64','cli_no_attach_smoke':True,'synthetic_fixture_only':True,'actual_game_test':False,'candidate_received':False,'detach_acknowledged':False}
try:
 time.sleep(1);target=identity(fixture.pid)
 client.connect(exe.parent,target,identity,consent=True)
 end=time.monotonic()+20
 while time.monotonic()<end:
  client.drain()
  if any('明日' in c.text for c in client.candidates.ranked()):report['candidate_received']=True;break
  time.sleep(.1)
finally:
 report['stop_status']=client.close()
 if fixture.poll() is None:fixture.terminate()
 fixture.wait(timeout=5)
 Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['candidate_received'],'Synthetic GDI fixture text was not observed; actual hook success is unverified.'
