"""Independent MIT client for the documented Textractor 5.2 CLI wire format.
No GPL source/DLL is included. Never launches, attaches or downloads on import.
"""
import hashlib
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import time
import threading
from core import ReaderError
from input_sources import CandidateSession

PINNED = {
 'x64': {'TextractorCLI.exe':'3c70e50a33fe1165e430eb3df6b9658c3a848257d294b92aab29d87632fe3783', 'texthook.dll':'43b966f566e1d6362416041bfb55dc4e04aef7bcb8b5aae2da8179c24b2dd58e'},
 'x86': {'TextractorCLI.exe':'b8cebf066023db1ef5921135e0aa0f68f17bade795d910a2df58a3da2bebf233', 'texthook.dll':'8fde589a24ef861c581b61829626d35d6b0fcc958aaaeca620dff630f1ed465b'},
}
DLL_HASHES = {'x64': {'LoaderDll.dll': '7679f09fab25e25faf0cb76a6f704bab62893edc3f2771b7571887b8f99a904b',
         'LocaleEmulator.dll': '6e2ffbceb6b1e904e138046298e7ece0206074c5e38d15e1c452c139e71a84e1',
         'Qt5Core.dll': 'cdde527ac62cfbd1221f387ae3bf1c4c9ebeaf371993c72cd6eb0ef304f5cb14',
         'Qt5Gui.dll': 'dbf661897259c5131ae7055de86ec6fa271909f726a7271ea180bf3c0f615a33',
         'Qt5Network.dll': '7cacbee0edb722e510f3a9c163a89e0a42a354209fccd205f8905bb5efb8917c',
         'Qt5WebSockets.dll': 'f1fba98c601f8baa07896de95e577556e966b0fcb7fb28d01702eb6843e1875b',
         'Qt5Widgets.dll': '2ca3a0b4faeed43045140348e5b3285d0a85e85e0211a8a38451cb19505fe71d',
         'Qt5WinExtras.dll': '93ad30d6742131c56d19657b773e529016213b06b9470f8bc21c67b64f7f1d64',
         'concrt140.dll': '95bb425be3d515a6a58f7399d44dd9e032baea11667dfdba29517c460171880a',
         'msvcp140.dll': 'd86ac158123a245b927592c80cc020fea29c8c4addc144466c4625a00ca9c77a',
         'msvcp140_1.dll': '18aef42187072c35b537be80e3b2da7ce4919b2c9574add19409d98e3026d916',
         'msvcp140_2.dll': '5fca695ed2cefec010d546310699226eef4b305df38cbe3dea2fdf9494abc163',
         'msvcp140_atomic_wait.dll': 'a577b5fc4e3a14ae141657c30a38d11ff8593135e51e55485b252eb821d47e75',
         'msvcp140_codecvt_ids.dll': 'e1ee6d29e30708ad5812035626bbc1058ea12fd5503d5a79d28c9cb67fab4a14',
         'texthook.dll': '43b966f566e1d6362416041bfb55dc4e04aef7bcb8b5aae2da8179c24b2dd58e',
         'vccorlib140.dll': '13e568fdcde1b7b7f2d1c97a474bdb8858f5ab761157f0fea7201ccecf84b9b8',
         'vcruntime140.dll': 'e1d6f78a72836ea120bd27a33ae89cbdc3f3ca7d9d0231aaa3aac91996d2fa4e',
         'vcruntime140_1.dll': '04e7ccbdcad7cbaf0ed28692fb08eab832c38aad9071749037ee7a58f45e9d7d'},
 'x86': {'LoaderDll.dll': '7679f09fab25e25faf0cb76a6f704bab62893edc3f2771b7571887b8f99a904b',
         'LocaleEmulator.dll': '6e2ffbceb6b1e904e138046298e7ece0206074c5e38d15e1c452c139e71a84e1',
         'Qt5Core.dll': 'dbc87861f4cc15a79c38a15129e4ba185a0bd65c6e722228e8912c205e6781c2',
         'Qt5Gui.dll': '5588d0147628851f0eadb5707dfa2e4f6d80bea3eb6b63b50b2a7ef4d3543d77',
         'Qt5Network.dll': 'b1f69db86ae070d41e97eae8b22ff75df694de557476da2b9131e4302353a93d',
         'Qt5WebSockets.dll': 'f3246be684f828cf84064dc45e97e2c8b0e81b3880c0901318a168d9ee55a175',
         'Qt5Widgets.dll': '535c0b78c757fe6f11c4369b5b6993a3dd850b0269e4d0d2d0e5bf24d933f29b',
         'Qt5WinExtras.dll': 'fe148008854dcd1083a1d20f606163bb1d62e0decc9638bc2b862adb39755df5',
         'concrt140.dll': 'c6198c7a2f5e9772411b4a24f50986f5ba0f3e74e69092822f16c1a0f5024e61',
         'msvcp140.dll': '885a0a146a83b0d5a19b88c4eb6372b648cfaed817bd31d8cd3fb91313dea13d',
         'msvcp140_1.dll': '09192837e98161dad48cdbac4e2e00a6aa9ff2912a601ffca36c1dea8e4e38c5',
         'msvcp140_2.dll': '7bf18f791b503f6c4ec8b4fadeeb2b2c547750a4ac36c91d9d6469b4d048e137',
         'msvcp140_atomic_wait.dll': '651b426602c3ba021759f297d68013504420cc15c0f1003fa2bcde3b4d7f0ddf',
         'msvcp140_codecvt_ids.dll': 'dd4a2e82cf4050bae3f8ef178a71528a6933187b94872b4686885481ce557873',
         'texthook.dll': '8fde589a24ef861c581b61829626d35d6b0fcc958aaaeca620dff630f1ed465b',
         'vccorlib140.dll': 'ea85134227c8e5a23a63d60e6cdb2bc38f925427ba75426a3be33212435e1741',
         'vcruntime140.dll': '1e0f8f7f13502f5cee17232e9bebca7b44dd6ec29f1842bb61033044c65b2bbf'}}
HEADER = re.compile(r'^\[([0-9A-Fa-f]{1,16}):([0-9A-Fa-f]{1,8}):([0-9A-Fa-f]{1,16}):([0-9A-Fa-f]{1,16}):([0-9A-Fa-f]{1,16}):([^\]\r\n]{0,512})\] (.*)$')
MAX_LINE = 8192

def command(action,pid):
    if action not in ('attach','detach') or type(pid) is not int or not 1<=pid<=0xffffffff:
        raise ReaderError('잘못된 연결 명령입니다.')
    return f'{action} -P{pid}\n'

def parse_line(line,pid):
    if len(line)>MAX_LINE:raise ReaderError('후킹 출력 길이 한도를 초과했습니다.')
    m=HEADER.fullmatch(line.rstrip('\r\n'))
    if not m:return None # Usage/console/multiline continuations are not candidates.
    if int(m[2],16)!=pid:return None
    # Stable within this session only; never use these addresses for reinjection.
    identifier='_'.join(str(int(m[i],16)) for i in (1,3))
    return identifier,m[7]

def verify_cli(folder,arch):
    folder=Path(folder)
    if arch not in PINNED or not folder.is_absolute():raise ReaderError('게임에 맞는 절대 경로를 선택하세요.')
    if folder.is_symlink() or any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in (folder,*folder.parents)):
        raise ReaderError('링크/정션 경로의 엔진은 실행하지 않습니다.')
    for file in folder.iterdir():
        if file.suffix.lower()=='.dll':
            digest=DLL_HASHES[arch].get(file.name)
            if not digest or file.is_symlink() or file.stat().st_size>40_000_000 or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
                raise ReaderError('엔진 폴더의 DLL이 공식 배포 해시와 다릅니다.')
    for name,digest in PINNED[arch].items():
        file=folder/name
        if not file.is_file() or file.is_symlink() or file.stat().st_size>2_000_000:
            raise ReaderError('공식 CLI/후킹 DLL을 확인할 수 없습니다.')
        if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
            raise ReaderError('지원하는 공식 Textractor 5.2.0 파일 해시와 다릅니다. 실행하지 않습니다.')
    return folder/'TextractorCLI.exe'

class CliSession:
    """One owned CLI, one selected process identity, bounded in-memory preview.
    CLI has no detach acknowledgement; close must never claim hook removal.
    """
    def __init__(self):
        self.process=None;self.job=None;self.candidates=CandidateSession();self.events=queue.Queue(64)
        self.stopped=threading.Event();self.failure=None;self.target=None
    def connect(self,folder,target,identity,consent=False):
        if sys.platform!='win32':raise ReaderError('Windows 전용 실험 기능입니다.')
        if not consent:raise ReaderError('선택한 게임의 후킹 연결 동의가 필요합니다.')
        if self.process is not None:raise ReaderError('기존 연결을 먼저 종료하세요.')
        exe=verify_cli(folder,target.arch)
        if identity(target.pid)!=target:raise ReaderError('선택한 게임이 종료되거나 바뀌었습니다.')
        self.target=target;self.identity=identity;self.stopped.clear();self.failure=None
        self.candidates.start(True);self.started=time.monotonic();self.received=False
        env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP'}}
        try:
            self.process=subprocess.Popen([str(exe)],cwd=str(exe.parent),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,encoding='utf-16-le',errors='strict',env=env,creationflags=0x08000000)
            from managed_engine import WindowsJob
            self.job=WindowsJob(self.process) # Own the CLI only; never put the game in this job.
            if identity(target.pid)!=target:raise ReaderError('연결 직전 게임 식별자가 바뀌었습니다.')
            self.process.stdin.write(command('attach',target.pid));self.process.stdin.flush()
            threading.Thread(target=self._read,daemon=True).start()
        except Exception:
            self.close();raise ReaderError('후킹 CLI를 시작하지 못했습니다. 권한/보안 설정을 바꾸지 말고 OCR로 복귀하세요.') from None
    def _read(self):
        stream=self.process.stdout
        try:
            while not self.stopped.is_set():
                line=stream.readline(MAX_LINE+1)
                if not line:break
                if len(line)>MAX_LINE:raise ReaderError('후킹 출력 길이 초과')
                event=parse_line(line,self.target.pid)
                if event:
                    try:self.events.put_nowait(event)
                    except queue.Full:raise ReaderError('후보 입력 폭주: 연결을 중지하세요.') from None
        except Exception:
            self.failure='후킹 출력 오류/한도 초과. 연결을 중지하세요.'
        finally:
            if not self.stopped.is_set():self.failure=self.failure or '후킹 CLI 종료. 자동 재연결하지 않습니다.'
    def drain(self):
        if self.failure:raise ReaderError(self.failure)
        if self.process is None:return False
        if self.identity(self.target.pid)!=self.target:raise ReaderError('선택한 게임이 종료/변경되었습니다.')
        if not self.received and time.monotonic()-self.started>30:raise ReaderError('30초 동안 후보가 없어 중지합니다. 자동 재연결하지 않습니다.')
        changed=False
        while not self.events.empty():
            identifier,text=self.events.get_nowait()
            self.candidates.ingest(self.candidates.generation,identifier,text);changed=True;self.received=True
        return changed
    def confirmed_text(self, identifier, expected):
        self.drain()
        session=self.candidates
        current=session.candidates.get(identifier)
        if session.selected!=identifier or current is None or current.text!=expected:
            raise ReaderError('확인 중 후보가 바뀌었습니다. 새 대사를 다시 확인하세요.')
        return current.text

    def close(self):
        self.stopped.set();self.candidates.stop()
        p=self.process
        if p:
            try:
                if p.poll() is None:
                    p.stdin.write(command('detach',self.target.pid));p.stdin.flush()
                p.stdin.close()
                p.wait(timeout=2)
            except (OSError,ValueError,subprocess.TimeoutExpired):
                if p.poll() is None:p.terminate()
                try:p.wait(timeout=2)
                except subprocess.TimeoutExpired:pass
            finally:
                if self.job:self.job.close();self.job=None
                if p.stdout:p.stdout.close()
                if p.stdin and not p.stdin.closed:p.stdin.close()
        self.process=None
        while not self.events.empty():self.events.get_nowait()
        if p is None:return '입력 중지 · 연결된 CLI 없음'
        return '입력 중지·해제 요청 완료. 엔진이 해제를 확인하지 않아 후크 제거 완료는 확인할 수 없습니다. 필요하면 게임을 저장 후 직접 종료하세요.'
