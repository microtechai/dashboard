"""Local HTTP integration tests. Auth/model/Piper are labeled FIXTURES, not production proof."""
import http.client, http.server, json, os, pathlib, shutil, socket, subprocess, threading, time, unittest, fcntl, signal
from typing import Any
ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / 'tests/chat_backend_runtime'
ORIGIN = 'https://dashboard.microtechai.es'
def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]
class Fixture(http.server.BaseHTTPRequestHandler):
    mode = 'ok'
    requests = []
    entered = threading.Event()
    release = threading.Event()
    def log_message(self, format, *args): pass
    def do_GET(self):
        if self.mode == 'unavailable': self.send_error(503); return
        if self.mode == 'revoked': self.send_error(401); return
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"user":{"username":"fixture-user"},"prefs":{}}')
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/api/login':
            if data.get('password') != 'fixture-password': self.send_error(401); return
            self.send_response(200); self.send_header('Set-Cookie', 'session=' + 'a'*64 + '; Path=/; HttpOnly'); self.end_headers()
            self.wfile.write(b'{"success":true,"username":"fixture-user"}'); return
        self.requests.append(data)
        if self.mode == 'slow':
            self.entered.set(); self.release.wait(8)
        self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
        self.wfile.write(b'data: {"choices":[{"delta":{"content":"FIXTURE respuesta"}}]}\n\n')
        if self.mode != 'truncated': self.wfile.write(b'data: [DONE]\n\n')
class Backend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RUN.mkdir(exist_ok=True); (RUN/'state').mkdir(exist_ok=True)
        cls.fp, cls.pp = port(), port()
        cls.fixture = http.server.ThreadingHTTPServer(('127.0.0.1',cls.fp),Fixture)
        threading.Thread(target=cls.fixture.serve_forever,daemon=True).start()
        cls.piper = RUN/'fixture-piper'
        cls.piper.write_text('#!/usr/bin/python3\n# TEST FIXTURE ONLY: emits a silent WAV, not synthesized speech.\nimport sys, wave, time, os\ntext=sys.stdin.read().strip()\nif text == "TIMEOUT": time.sleep(30)\nif text == "FAIL": sys.exit(7)\nif text == "CPU_SINGLE" and len(os.sched_getaffinity(0)) != 1: sys.exit(9)\nif "\\n" in text: sys.exit(8)\nwith wave.open(sys.argv[-1], "wb") as w:\n w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(b"\\0"*440)\n')
        cls.piper.chmod(0o700)
        cfg = {'state_dir':str(RUN/'state'),'auth_base':f'http://127.0.0.1:{cls.fp}', 'model_url':f'http://127.0.0.1:{cls.fp}/v1/chat/completions', 'origin':ORIGIN, 'piper_python':str(cls.piper)}
        cls.cfg = cfg
        (RUN/'config.php').write_text('<?php return json_decode('+repr(json.dumps(cfg))+', true);')
        (RUN/'router.php').write_text('<?php define("JARVIS_CHAT_CONFIG", __DIR__."/config.php"); require '+repr(str(ROOT/'api/chat.php'))+';')
        cls.log = open(RUN/'server.log','w+')
        cls.proc = subprocess.Popen(['php','-S',f'127.0.0.1:{cls.pp}',str(RUN/'router.php')],stdout=cls.log,stderr=cls.log,env={**os.environ,'PHP_CLI_SERVER_WORKERS':'4'},start_new_session=True)
        for _ in range(60):
            try:
                with socket.create_connection(('127.0.0.1',cls.pp), timeout=.1): break
            except OSError: time.sleep(.05)
    @classmethod
    def tearDownClass(cls):
        os.killpg(cls.proc.pid,signal.SIGTERM); cls.proc.wait(); cls.fixture.shutdown(); cls.fixture.server_close()
        cls.log.seek(0); log=cls.log.read(); cls.log.close(); shutil.rmtree(RUN)
        errors=[line for line in log.splitlines() if any(s in line for s in ['PHP Warning:', 'PHP Fatal error:', 'PHP Notice:'])]
        if errors: raise AssertionError('PHP runtime diagnostics: ' + '\n'.join(errors))
    def setUp(self): self.cookie=''; self.csrf=''; Fixture.mode='ok'; Fixture.requests=[]
    def req(self, action='session', body=None, headers=None, method=None) -> tuple[int, dict, Any]:
        c=http.client.HTTPConnection('127.0.0.1',self.pp,timeout=70)
        h={'Cookie':self.cookie, 'Origin':ORIGIN,'X-CSRF-Token':self.csrf,'Content-Type':'application/json'}; h.update(headers or {})
        c.request(method or ('GET' if body is None else 'POST'),'/api/chat.php?action='+action, None if body is None else json.dumps(body),h)
        r=c.getresponse(); status=r.status; hs=dict(r.getheaders()); raw=r.read(); c.close()
        if 'Set-Cookie' in hs: self.cookie=hs['Set-Cookie'].split(';')[0]
        try:
            data=json.loads(raw)
            if 'csrf' in data: self.csrf=data['csrf']
        except ValueError: data=raw.decode(errors='replace')
        return status, hs, data
    def login(self):
        self.assertEqual(self.req()[0],200)
        self.assertEqual(self.req('login',{'username':'fixture-user','password':'fixture-password'})[0],200)
    def test_authentication_and_request_guards(self):
        self.req()
        self.assertEqual(self.req('login',{}, {'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.req('login',{}, {'X-CSRF-Token':'wrong'})[0],403)
        self.assertEqual(self.req('login',{}, {'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.req('message',{'text':'hola'})[0],401)
        self.assertEqual(self.req('login',{'username':'fixture-user','password':'bad'})[0],401)
        old=self.csrf
        self.login(); self.assertNotEqual(old,self.csrf)
        self.assertTrue(self.req()[2]['authenticated'])
        Fixture.mode='unavailable'; self.assertEqual(self.req()[0],503)
        Fixture.mode='revoked'; self.assertEqual(self.req('message',{'text':'hola'})[0],401)
        self.assertFalse(self.req()[2]['authenticated'])
        Fixture.mode='ok'; self.login()
        self.assertFalse(self.req('logout',{})[2]['authenticated'])
        self.assertEqual(self.req('session',{})[0],405)
        self.assertEqual(self.req('unknown')[0],404)
    def test_stream_history_limits_and_failure(self):
        self.login()
        for body in [{'text':''},{'text':'x'*4001},{'text':'ok','model':'evil'},{'text':['no']},{'text':'a\u0000b'}]:
            self.assertEqual(self.req('message',body)[0],400)
        s,h,d=self.req('message',{'text':'hola'})
        self.assertEqual(s,200); self.assertIn('text/event-stream',h['Content-Type'])
        self.assertIn('event: delta',d); self.assertIn('event: done',d)
        history=self.req()[2]['history']; self.assertEqual(len(history),2)
        self.assertEqual(history[1]['content'],'FIXTURE respuesta')
        upstream=Fixture.requests[-1]
        self.assertEqual(upstream['model'],'qwen3-coder-next'); self.assertEqual(upstream['max_tokens'],1024)
        self.assertTrue(upstream['stream']); self.assertEqual(upstream['messages'][0]['role'],'system')
        Fixture.mode='truncated'
        s,h,d=self.req('message',{'text':'hola'})
        self.assertIn('event: error',d); self.assertNotIn('event: done',d)
        self.assertEqual(len(self.req()[2]['history']),2)
        Fixture.mode='ok'
        for _ in range(4): self.assertEqual(self.req('message',{'text':'hola'})[0],200)
        self.assertEqual(self.req('message',{'text':'limit'})[0],429)
        self.assertEqual(self.req('clear',{})[2]['history'],[])
        self.assertEqual(self.req('message',{'text':'limit after clear'})[0],429)
    def test_tts_process_wav_and_cleanup(self):
        self.req(); self.assertEqual(self.req('tts',{'text':'hola'})[0],401)
        self.login()
        self.assertEqual(self.req('tts',{'text':'x'*1001})[0],400)
        self.assertEqual(self.req('tts',{'text':'hola','path':'/tmp/evil'})[0],400)
        s,h,d=self.req('tts',{'text':'hola; $(touch /not-allowed)'})
        self.assertEqual(s,200); self.assertEqual(h['Content-Type'],'audio/wav')
        self.assertTrue(d.startswith('RIFF')); self.assertEqual(d[8:12],'WAVE')
        self.assertEqual(list((RUN/'state').glob('tts-*')),[])
        self.assertEqual(self.req('tts',{'text':'FAIL'})[0],502)
        self.assertEqual(list((RUN/'state').glob('tts-*')),[])
        for _ in range(18): self.assertEqual(self.req('tts',{'text':'hola'})[0],200)
        self.assertEqual(self.req('tts',{'text':'limit'})[0],429)
    def test_tts_timeout_reaps_and_unlocks(self):
        self.login(); started=time.monotonic()
        self.assertEqual(self.req('tts',{'text':'TIMEOUT'})[0],502)
        self.assertGreaterEqual(time.monotonic()-started,19)
        self.assertLess(time.monotonic()-started,23)
        self.assertEqual(list((RUN/'state').glob('tts-*')),[])
        self.assertEqual(self.req('tts',{'text':'after timeout'})[0],200)
    def test_multiline_tts_is_one_piper_utterance(self):
        self.login()
        self.assertEqual(self.req('tts',{'text':'Primera línea.\nSegunda línea.'})[0],200)
    def test_missing_private_temp_dir_fails_closed(self):
        self.login()
        cfg={**self.cfg,'tts_temp_dir':str(RUN/'missing-private-dir')}
        (RUN/'config.php').write_text('<?php return json_decode('+repr(json.dumps(cfg))+', true);')
        try:
            self.assertEqual(self.req('tts',{'text':'must not use shared tmp'})[0],502)
        finally:
            (RUN/'config.php').write_text('<?php return json_decode('+repr(json.dumps(self.cfg))+', true);')
    def test_tts_single_cpu_affinity(self):
        self.login()
        self.assertEqual(self.req('tts',{'text':'CPU_SINGLE'})[0],200)
    def test_global_locks(self):
        self.login()
        for action in ['message','tts']:
            with open(RUN/'state'/f'{action}.lock','a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertEqual(self.req(action,{'text':'busy'})[0],429)
            self.assertEqual(self.req(action,{'text':'released'})[0],200)
    def test_history_bound_and_unicode_limit(self):
        self.login()
        for _ in range(6): self.assertEqual(self.req('message',{'text':'á'*4000})[0],200)
        history=self.req()[2]['history']
        self.assertLessEqual(len(history),12)
        self.assertLessEqual(sum(len(m['content']) for m in history),18000)
        self.assertEqual(history[0]['role'],'user')
    def test_stream_unlock_and_clear_race(self):
        self.login(); Fixture.entered.clear(); Fixture.release.clear(); Fixture.mode='slow'
        result=[]
        worker=threading.Thread(target=lambda: result.append(self.req('message',{'text':'slow'})))
        worker.start()
        try:
            self.assertTrue(Fixture.entered.wait(3))
            started=time.monotonic()
            self.assertEqual(self.req('clear',{})[0],200)
            self.assertLess(time.monotonic()-started,2)
            self.assertEqual(self.req('message',{'text':'parallel'})[0],429)
        finally:
            Fixture.release.set(); worker.join(10)
        self.assertIn('event: done',result[0][2])
        self.assertEqual(self.req()[2]['history'],[])
    def test_session_cookie_and_anonymous_state(self):
        status,h,data=self.req()
        self.assertEqual(status,200)
        self.assertFalse(data['authenticated']); self.assertEqual(data['history'],[])
        self.assertEqual(len(data['csrf']),64)
        for value in ['__Host-jarvis-chat=', 'secure','HttpOnly','SameSite=Strict','path=/']:
            self.assertIn(value,h['Set-Cookie'])
        self.assertEqual(h['Cache-Control'],'no-store')
if __name__=='__main__': unittest.main(verbosity=2)
