import json, os, subprocess, sys, threading, unittest
from unittest.mock import patch, Mock
import managed_engine as m
from core import ReaderError

STUB=r'''
import sys,json
from http.server import HTTPServer,BaseHTTPRequestHandler
port,alias,token=sys.argv[1:]
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.headers.get('Authorization')!='Bearer '+token:self.send_error(401);return
  raw=json.dumps({'data':[{'id':alias}]}).encode()
  self.send_response(200);self.end_headers();self.wfile.write(raw)
 def log_message(self,*args):pass
HTTPServer(('127.0.0.1',int(port)),Handler).serve_forever()
'''

class ManagedTests(unittest.TestCase):
 def setUp(self):self.engine=m.ManagedEngine()
 def tearDown(self):self.engine.stop()
 def launch_context(self):
  from contextlib import ExitStack
  stack=ExitStack();original=subprocess.Popen
  def launch(args,**kw):
   self.args=args;self.env=kw['env']
   return original([sys.executable,'-c',STUB,args[args.index('--port')+1],args[args.index('--alias')+1],args[args.index('--api-key')+1]],stdin=kw['stdin'],stdout=kw['stdout'],stderr=kw['stderr'])
  stack.enter_context(patch.object(m,'WINDOWS',True))
  stack.enter_context(patch.object(m,'verify_runtime',return_value=True))
  stack.enter_context(patch.object(m,'verify_model',return_value=True))
  stack.enter_context(patch.object(m.subprocess,'Popen',side_effect=launch))
  if os.name!='nt':stack.enter_context(patch.object(m,'WindowsJob',return_value=Mock()))
  return stack
 def test_owned_start_switch_stop_and_no_cloud_environment(self):
  with patch.dict(os.environ,{'DEEPL_API_KEY':'synthetic','LLAMA_ARG_HOST':'0.0.0.0','HTTP_PROXY':'http://invalid'}),self.launch_context():
   self.engine.start('qwen25-1.5b',timeout=10)
   p=self.engine.process;conf=self.engine.configuration()
   self.assertTrue(self.engine.uses('qwen25-1.5b'));self.assertEqual(len(conf['local_token']),64)
   self.assertEqual(self.args[self.args.index('--host')+1],'127.0.0.1')
   self.assertNotIn('DEEPL_API_KEY',self.env);self.assertNotIn('LLAMA_ARG_HOST',self.env)
   self.engine.start('qwen3-4b',timeout=10)
   self.assertIsNotNone(p.poll());self.assertFalse(self.engine.uses('qwen25-1.5b'))
   self.assertNotEqual(conf['local_token'],self.engine.configuration()['local_token'])
   self.engine.stop();self.assertFalse(self.engine.active());self.assertFalse(self.engine.uses('qwen3-4b'))
   with self.assertRaises(ReaderError):self.engine.configuration()
 def test_cancel_before_launch(self):
  event=threading.Event();event.set()
  with self.launch_context():
   with self.assertRaises(ReaderError):self.engine.start('qwen25-1.5b',cancelled=event)
  self.assertIsNone(self.engine.process);self.assertFalse(self.engine.uses('qwen25-1.5b'))
 def test_timeout_cleans_owned_process(self):
  with self.launch_context():
   with self.assertRaises(ReaderError):self.engine.start('qwen25-1.5b',timeout=0)
  self.assertIsNone(self.engine.process);self.assertEqual(self.engine.token,'')
 def test_stop_never_touches_external_process(self):
  outside=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
  try:
   self.engine.stop();self.assertIsNone(outside.poll())
  finally:outside.terminate();outside.wait(timeout=5)
 def test_unverified_model_never_starts(self):
  with self.launch_context(),patch.object(m,'verify_model',return_value=False),patch.object(m.subprocess,'Popen') as launch:
   with self.assertRaises(ReaderError):self.engine.start('qwen25-1.5b')
   launch.assert_not_called()
