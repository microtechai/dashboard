"""Isolated browser component tests. All APIs and credentials are TEST FIXTURES."""
import json
import tempfile
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class ChatFrontend(unittest.TestCase):
    def setUp(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        self.page = self.browser.new_page(viewport={'width': 1280, 'height': 800})
        self.calls = []
        self.auth = False
        self.history = []
        self.message_status = 200
        self.stream = 'event: delta\ndata: {"text":"Hola"}\n\nevent: done\ndata: {"text":"Hola"}\n\n'
        self.page.route('http://chat-fixture.test/**', self.route)
        self.page.goto('http://chat-fixture.test/login.html')

    def route(self, route):
        req = route.request
        if '/api/chat.php' in req.url:
            action = req.url.split('action=')[1]
            body = json.loads(req.post_data or '{}')
            self.calls.append((action, body, req.headers))
            if action == 'session':
                route.fulfill(json={'authenticated': self.auth, 'csrf': 'rotated-fixture' if self.auth else 'initial-fixture', 'username': 'fixture-user', 'history': self.history})
            elif action == 'login':
                self.auth = True
                route.fulfill(json={'authenticated': True})
            elif action == 'logout':
                self.auth = False
                route.fulfill(json={'ok': True})
            elif action == 'message':
                if self.message_status == 401: self.auth = False
                route.fulfill(status=self.message_status, content_type='text/event-stream' if self.message_status == 200 else 'application/json', body=self.stream if self.message_status == 200 else '{"error":"Fixture unavailable"}')
            else:
                route.fulfill(status=503, json={'error': 'Fixture TTS unavailable'})
        elif req.url.endswith('/login.html'):
            route.fulfill(content_type='text/html',body=(ROOT/'login.html').read_text())
        elif '/chat/' in req.url:
            path = ROOT / req.url.split('chat-fixture.test/')[1].split('?',1)[0]
            route.fulfill(status=200 if path.exists() else 404, content_type='text/javascript' if path.suffix in ['.js','.mjs'] else 'text/css', body=path.read_text() if path.exists() else '')
        else:
            route.fulfill(content_type='text/html', body='<!doctype html><meta charset="UTF-8"><meta name="viewport" content="width=device-width"><body style="background:#050810;color:white"><h1>ISOLATED MOCK API FIXTURE — NOT LIVE</h1><link rel="stylesheet" href="/chat/chat.css"><script defer src="/chat/chat.js"></script>')

    def tearDown(self):
        self.browser.close()
        self.pw.stop()

    def open(self):
        self.page.locator('#jarvis-chat-toggle').click(timeout=1500)

    def login(self):
        self.page.locator('[name=username]').fill('fixture-user')
        self.page.locator('[name=password]').fill('NOT-A-REAL-PASSWORD')
        self.page.locator('#submit').click()
        self.page.wait_for_url('http://chat-fixture.test/')
        self.open()
        self.page.locator('#jarvis-chat-input').wait_for(state='visible')

    def options(self):
        details = self.page.locator('#jarvis-chat-options')
        if not details.evaluate('(el) => el.open'):
            details.locator(':scope > summary').click()

    def send(self, text='test fixture'):
        self.page.locator('#jarvis-chat-input').fill(text)
        self.page.locator('#jarvis-chat-input').press('Enter')

    def test_login_csrf_and_safe_history(self):
        self.history = [{'role': 'assistant', 'content': '<img src=x onerror=alert(1)>'}]
        self.login()
        login = next(c for c in self.calls if c[0] == 'login')
        self.assertEqual(login[1], {'username': 'fixture-user', 'password': 'NOT-A-REAL-PASSWORD'})
        self.assertEqual(login[2]['x-csrf-token'], 'initial-fixture')
        self.assertEqual([c[0] for c in self.calls], ['session', 'login', 'session'])
        self.assertEqual(self.page.locator('input[type=password]').count(), 0)
        self.assertEqual(self.page.locator('#jarvis-chat-history img').count(), 0)
        self.assertIn('<img', self.page.locator('#jarvis-chat-history').inner_text())
        self.options()
        self.page.locator('#jarvis-chat-logout').click()
        self.page.wait_for_url('**/login.html')
        self.assertEqual(self.page.locator('#jarvis-chat-history').count(), 0)

    def test_stream_utf8_multiline_and_safe_done(self):
        self.login()
        self.page.evaluate("window.states=[]; addEventListener('jarvis-chat-state', e=>states.push(e.detail))")
        self.stream = 'event: delta\r\ndata: {"text":\r\ndata: "¡Sí! 🟦"}\r\n\r\nevent: done\ndata: {"text":"¡Sí! 🟦 <svg onload=alert(1)>"}\n\n'
        self.send()
        self.page.wait_for_function("document.querySelector('#jarvis-chat-history').textContent.includes('<svg')", timeout=2000)
        self.assertEqual(self.page.locator('#jarvis-chat-history svg').count(), 0)
        self.assertIn('¡Sí! 🟦', self.page.locator('#jarvis-chat-history').inner_text())
        message = next(c for c in self.calls if c[0] == 'message')
        self.assertEqual(message[2]['x-csrf-token'], 'rotated-fixture')
        states = self.page.evaluate('states')
        self.assertIn('thinking', [x['state'] for x in states])
        self.assertEqual(states[-1]['state'], 'idle')
        self.page.locator('#jarvis-chat-input').fill('two')
        self.page.locator('#jarvis-chat-input').press('Shift+Enter')
        self.assertEqual(self.page.locator('#jarvis-chat-input').input_value(), 'two\n')
        self.page.screenshot(path=str(Path(tempfile.gettempdir()) / 'mia-chat-frontend-desktop.png'))

    def test_audio_queue_stop_and_real_wav_analyser(self):
        self.login()
        self.stream = 'event: done\ndata: ' + json.dumps({'text': 'Frase de prueba. ' * 150}) + '\n\n'
        self.send()
        self.page.locator('.jarvis-chat-read').wait_for(timeout=2000)
        # A generated sine-wave WAV tests the real browser decoder/AudioContext,
        # NOT Piper, a live model, or audible output on a physical speaker.
        import io, wave, math, struct
        out = io.BytesIO()
        with wave.open(out, 'wb') as wav:
            wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b''.join(struct.pack('<h', int(8000 * math.sin(i * math.tau * 440 / 16000))) for i in range(16000 * 3)))
        import os
        real_wav = os.environ.get('JARVIS_TEST_WAV')
        wav_bytes = Path(real_wav).read_bytes() if real_wav else out.getvalue()
        print('Audio fixture:', real_wav or 'generated sine WAV (not Piper)')
        tts = []
        def wav_route(route):
            tts.append(json.loads(route.request.post_data))
            route.fulfill(content_type='audio/wav', body=wav_bytes)
        self.page.route('**/api/chat.php?action=tts', wav_route)
        self.page.evaluate('''() => {
          window.states=[]; window.created=[]; window.revoked=[];
          addEventListener('jarvis-chat-state', e=>states.push(e.detail));
          const create=URL.createObjectURL.bind(URL), revoke=URL.revokeObjectURL.bind(URL);
          URL.createObjectURL=b=>{const u=create(b);created.push(u);return u};
          URL.revokeObjectURL=u=>{revoked.push(u);revoke(u)};
        }''')
        self.page.locator('.jarvis-chat-read').click()
        self.page.wait_for_function("states.some(x=>x.state==='speaking' && x.level>0)", timeout=5000)
        self.assertEqual(len(tts), 1)
        self.assertTrue(0 < len(tts[0]['text']) <= 1000)
        self.page.locator('#jarvis-chat-stop').click()
        self.page.wait_for_timeout(150)
        self.assertEqual(self.page.evaluate('created'), self.page.evaluate('revoked'))
        self.assertEqual(self.page.evaluate('states.at(-1).state'), 'idle')
        self.assertEqual(len(tts), 1)

    def test_errors_and_auth_expiry(self):
        self.login()
        for code in (429, 503, 403, 401):
            with self.subTest(code=code):
                self.message_status = code
                self.send(str(code))
                if code == 401:
                    self.page.wait_for_url('**/login.html')
                    self.assertTrue(self.page.locator('#access').is_visible())
                    self.assertEqual(self.page.locator('#jarvis-chat-history').count(), 0)
                else:
                    self.page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('Fixture unavailable')", timeout=2000)
                    self.assertFalse(self.page.locator('#jarvis-chat-compose button[type=submit]').is_disabled())
                    self.page.locator('#jarvis-chat-stop').click()

    def test_byte_split_sse_abort_stale_and_malformed(self):
        self.login()
        self.page.evaluate('''() => {
          window.states=[]; addEventListener('jarvis-chat-state', e=>states.push(e.detail));
          const original=window.fetch;
          window.fetch=(url,opts)=>{
            if (!url.includes('action=message')) return original(url,opts);
            window.fixtureSignal=opts.signal;
            return Promise.resolve(new Response(new ReadableStream({start(c){window.fixtureStream=c}}),{headers:{'Content-Type':'text/event-stream'}}));
          };
          window.feed=(s)=>{for(const b of new TextEncoder().encode(s)) fixtureStream.enqueue(new Uint8Array([b]));};
        }''')
        self.send('first')
        self.page.wait_for_function('!!window.fixtureStream')
        self.page.evaluate('feed(\'event: delta\\r\\ndata: {"text":"á🟦"}\\r\\n\\r\\n\')')
        self.page.wait_for_function("document.querySelector('#jarvis-chat-history').textContent.includes('á🟦')")
        old_stream = self.page.evaluate_handle('fixtureStream')
        self.page.locator('#jarvis-chat-stop').click()
        self.assertTrue(self.page.evaluate('fixtureSignal.aborted'))
        self.send('second')
        self.page.evaluate('feed(\'event: done\\ndata: {"text":"SECOND"}\\n\\n\')')
        self.page.wait_for_function("document.querySelector('#jarvis-chat-history').textContent.includes('SECOND')")
        self.page.evaluate('(s)=>{try{s.enqueue(new TextEncoder().encode(\'event: done\\ndata: {"text":"STALE"}\\n\\n\'))}catch(e){}}', old_stream)
        self.assertNotIn('STALE', self.page.locator('#jarvis-chat-history').inner_text())
        self.assertEqual(self.page.evaluate('states.at(-1).state'), 'idle')
        for payload, expected in [('event: error\ndata: {"error":"Fixture model error"}\n\n', 'Fixture model error'), ('event: delta\ndata: broken\n\n', 'SSE'), ('event: delta\ndata: {"text":"partial"}\n\n', 'sin completar')]:
            self.send('error fixture')
            self.page.evaluate('(s)=>{feed(s);fixtureStream.close()}', payload)
            self.page.wait_for_function('(s)=>document.querySelector("#jarvis-chat-status").textContent.includes(s)', arg=expected)

    def test_autoread_history_and_tts_error(self):
        self.history = [{'role': 'assistant', 'content': 'History fixture'}]
        self.login()
        self.assertEqual(self.page.locator('.jarvis-chat-read').count(), 1)
        self.options()
        self.page.locator('#jarvis-chat-autoread').check()
        self.page.locator('#jarvis-chat-options > summary').click()
        self.send()
        self.page.wait_for_function("document.querySelectorAll('.jarvis-chat-read').length===2")
        self.assertEqual(len([c for c in self.calls if c[0] == 'tts']), 0)  # Phase4: typed replies never autoread.
        self.page.locator('.jarvis-chat-read').last.click()
        self.page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('Fixture TTS unavailable')", timeout=3000)
        self.assertEqual(len([c for c in self.calls if c[0] == 'tts']), 1)

    def test_logout_cancels_pending_reply(self):
        self.login()
        self.page.evaluate('''() => {
          const original=fetch; window.fetch=(u,o)=>u.includes('action=message') ? new Promise(resolve=>{window.pending=()=>resolve(new Response('event: done\\ndata: {"text":"STALE AFTER LOGOUT"}\\n\\n',{headers:{'Content-Type':'text/event-stream'}})); window.sig=o.signal}) : original(u,o);
        }''')
        self.send()
        self.page.evaluate("addEventListener('pagehide',()=>{pending();sessionStorage.setItem('aborted',String(sig.aborted));})")
        self.options()
        self.page.locator('#jarvis-chat-logout').click()
        self.page.wait_for_url('**/login.html')
        self.assertEqual(self.page.evaluate("sessionStorage.getItem('aborted')"),'true')
        self.page.wait_for_timeout(100)
        self.assertEqual(self.page.locator('#jarvis-chat-history').count(), 0)

    def test_audio_blocked_explicit_retry(self):
        self.login()
        self.send()
        self.page.locator('.jarvis-chat-read').wait_for()
        self.page.route('**/api/chat.php?action=tts', lambda r: r.fulfill(content_type='audio/wav', body=b'fixture-not-decoded-because-play-is-mocked'))
        self.page.evaluate('''() => {
          window.states=[]; addEventListener('jarvis-chat-state', e=>states.push(e.detail));
          HTMLMediaElement.prototype.play=()=>Promise.reject(new DOMException('Fixture autoplay denied','NotAllowedError'));
        }''')
        self.page.locator('.jarvis-chat-read').click()
        self.page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('Pulsa Leer')")
        self.assertNotIn('speaking', self.page.evaluate('states.map(s=>s.state)'))
        self.assertEqual(self.page.evaluate('states.at(-1).state'), 'idle')
        self.assertTrue(self.page.locator('.jarvis-chat-read').is_enabled())

    def test_audio_full_queue_and_end_cleanup(self):
        self.login()
        text = 'Primera frase. ' * 100  # Within the explicit 3-request audible budget.
        self.stream = 'event: done\ndata: ' + json.dumps({'text': text}) + '\n\n'
        self.send()
        self.page.locator('.jarvis-chat-read').wait_for()
        # Deterministic media double exercises serial queue/lifecycle, not sound.
        self.page.evaluate('''() => {
          window.tts=[];window.created=[];window.revoked=[];window.states=[];
          addEventListener('jarvis-chat-state',e=>states.push(e.detail));
          const original=fetch;
          window.fetch=(u,o)=>{if(!u.includes('action=tts'))return original(u,o);tts.push(JSON.parse(o.body).text);return Promise.resolve(new Response('fixture',{headers:{'Content-Type':'audio/wav'}}))};
          window.AudioContext=undefined;window.webkitAudioContext=undefined;
          window.Audio=class {constructor(){this.paused=true} play(){this.paused=false;setTimeout(()=>{this.paused=true;this.onended?.()},20);return Promise.resolve()} pause(){this.paused=true} removeAttribute(){} load(){}};
          URL.createObjectURL=()=>{let u='blob:fixture'+created.length;created.push(u);return u};URL.revokeObjectURL=u=>revoked.push(u);
        }''')
        self.page.locator('.jarvis-chat-read').click()
        self.page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('Lectura completada')")
        parts = self.page.evaluate('tts')
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(0 < len(s) <= 1000 for s in parts))
        self.assertEqual(' '.join(parts), text.strip())
        self.assertEqual(self.page.evaluate('created'), self.page.evaluate('revoked'))
        self.assertEqual(self.page.evaluate('states.at(-1).state'), 'idle')

    def test_audio_stale_play_cannot_stop_new_audio(self):
        self.login()
        self.send()
        self.page.locator('.jarvis-chat-read').wait_for()
        self.page.evaluate('''() => {
          window.audios=[];window.created=[];window.revoked=[];
          const original=fetch;
          window.fetch=(u,o)=>!u.includes('action=tts')?original(u,o):Promise.resolve(new Response('fixture',{headers:{'Content-Type':'audio/wav'}}));
          window.AudioContext=undefined;window.webkitAudioContext=undefined;
          window.Audio=class {constructor(){this.paused=true;audios.push(this)} play(){this.paused=false;return Promise.resolve()} pause(){this.paused=true} removeAttribute(){} load(){}};
          URL.createObjectURL=()=>{const u='blob:fixture'+created.length;created.push(u);return u};URL.revokeObjectURL=u=>revoked.push(u);
        }''')
        self.page.locator('.jarvis-chat-read').click()
        self.page.wait_for_function('audios.length===1')
        self.page.locator('.jarvis-chat-read').click()
        self.page.wait_for_function('audios.length===2')
        self.assertFalse(self.page.evaluate('audios[1].paused'))
        self.assertEqual(self.page.evaluate('revoked.length'), 1)
        self.page.locator('#jarvis-chat-stop').click()
        self.assertEqual(self.page.evaluate('created'), self.page.evaluate('revoked'))

    def test_session_retry_after_unavailable(self):
        self.login()
        self.page.route('**/api/chat.php?action=session', lambda r: r.fulfill(status=503, json={'error': 'Fixture session unavailable'}))
        self.page.reload()
        self.open()
        self.page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('Fixture session unavailable')")
        self.page.unroute('**/api/chat.php?action=session')
        self.page.locator('#jarvis-chat-retry').click(timeout=1500)
        self.page.locator('#jarvis-chat-conversation').wait_for(state='visible')

    def test_logout_clears_private_history_even_if_refresh_fails(self):
        self.history = [{'role': 'assistant', 'content': 'Private fixture'}]
        self.login()
        self.page.route('**/api/chat.php?action=session', lambda r: r.fulfill(status=503, json={'error': 'Fixture refresh down'}))
        self.options()
        self.page.locator('#jarvis-chat-logout').click()
        self.page.wait_for_url('**/login.html')
        self.page.wait_for_function("document.querySelector('#status').textContent.includes('Fixture refresh down')")
        self.assertEqual(self.page.locator('#jarvis-chat-history').count(), 0)
        self.assertTrue(self.page.locator('#access').is_visible())

    def test_no_message_during_logout(self):
        self.login()
        self.page.evaluate('''() => { const original=fetch;window.fetch=(u,o)=>u.includes('action=logout') ? new Promise(()=>{}) : original(u,o) }''')
        self.options()
        self.page.locator('#jarvis-chat-logout').click()
        self.send('must not send')
        self.page.wait_for_timeout(100)
        self.assertFalse(any(c[0] == 'message' for c in self.calls))

    def test_compact_bar_details_ime_and_dashboard_layout(self):
        self.login()
        self.assertEqual(self.page.locator('#jarvis-chat-compose textarea').count(), 1)
        self.assertFalse(self.page.locator('#jarvis-chat-options').evaluate('(el) => el.open'))
        self.assertFalse(self.page.locator('.mia-workflow').evaluate('(el) => el.open'))
        self.assertFalse(self.page.locator('.jarvis-voice-notice').is_visible())
        self.assertFalse(self.page.locator('#jarvis-chat-continuous').is_visible())
        self.assertTrue(self.page.locator('#jarvis-chat-stop').is_visible())
        self.page.locator('#jarvis-chat-input').fill('composición')
        self.page.locator('#jarvis-chat-input').dispatch_event('keydown', {'key': 'Enter', 'isComposing': True})
        self.assertFalse(any(c[0] == 'message' for c in self.calls))
        summary = self.page.locator('#jarvis-chat-options > summary')
        summary.focus()
        self.page.keyboard.press('Enter')
        self.assertTrue(self.page.locator('#jarvis-chat-continuous').is_visible())
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.locator('#jarvis-chat-options').evaluate('(el) => el.open'))
        self.assertTrue(self.page.locator('#jarvis-chat-panel').is_visible())
        self.page.evaluate("document.body.dataset.miaView='dashboard'")
        for width, height in [(1280, 800), (768, 1024), (375, 667), (320, 568), (667, 375)]:
            self.page.set_viewport_size({'width': width, 'height': height})
            for selector in ['#jarvis-chat-panel', '#jarvis-chat-input', '#jarvis-chat-talk', '#jarvis-chat-compose button[type=submit]', '#jarvis-chat-stop']:
                box = self.page.locator(selector).bounding_box()
                self.assertIsNotNone(box, selector)
                self.assertGreaterEqual(box['x'], 0, selector)
                self.assertGreaterEqual(box['y'], 0, selector)
                self.assertLessEqual(box['x'] + box['width'], width, selector)
                self.assertLessEqual(box['y'] + box['height'], height, selector)
        self.assertFalse(any(c[0] in ['message', 'tts', 'transcribe'] for c in self.calls))

    def test_minimize_responsive_login(self):
        self.login()
        panel = self.page.locator('#jarvis-chat-panel')
        self.assertTrue(panel.is_visible())
        self.assertLessEqual(panel.bounding_box()['width'], 400)
        self.assertLessEqual(panel.bounding_box()['height'], 620)
        self.page.locator('#jarvis-chat-minimize').click()
        self.assertFalse(panel.is_visible())
        self.page.set_viewport_size({'width': 375, 'height': 667})
        self.open()
        box = panel.bounding_box()
        self.assertGreaterEqual(box['x'], 0)
        self.assertLessEqual(box['x'] + box['width'], 375)
        self.assertFalse(self.page.locator('#jarvis-chat-autoread').is_checked())
        self.page.screenshot(path=str(Path(tempfile.gettempdir()) / 'mia-chat-frontend-mobile.png'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
