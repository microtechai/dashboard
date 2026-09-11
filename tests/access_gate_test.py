"""PHASE5: isolated HTTP auth FIXTURES. No production credentials/accounts.
PHP router exercises gate, not a simulation of authentication success.
"""
import http.client
import unittest
from chat_backend_test import Backend, Fixture, ROOT, RUN

class Access(unittest.TestCase):
    setUp = Backend.setUp
    tearDownClass = classmethod(Backend.tearDownClass.__func__)
    req = Backend.req
    login = Backend.login

    @classmethod
    def setUpClass(cls):
        Backend.setUpClass.__func__(cls)
        (RUN/'router.php').write_text('<?php define("JARVIS_CHAT_CONFIG", __DIR__."/config.php"); define("JARVIS_DOCUMENT_ROOT", '+repr(str(ROOT))+'); $path=parse_url($_SERVER["REQUEST_URI"], PHP_URL_PATH); if ($path === "/api/chat.php") { require '+repr(str(ROOT/'api/chat.php'))+'; } else { require '+repr(str(ROOT/'server/gate.php' if (ROOT/'server/gate.php').exists() else ROOT/'api/chat.php'))+'; }')

    def get(self, path, method='GET', extra=None):
        c=http.client.HTTPConnection('127.0.0.1',self.pp,timeout=15)
        c.request(method,path,headers={'Cookie':self.cookie,**(extra or {})})
        r=c.getresponse(); result=(r.status,dict(r.getheaders()),r.read()); c.close()
        return result

    def test_anonymous_never_gets_private_bytes(self):
        for path in ['/', '/index.html', '/api/stats.php', '/chat/chat.js', '/fire/shaders.js', '/index-backup.html', '/anything', '/api/venv/bin/python']:
            with self.subTest(path=path):
                s,h,b=self.get(path)
                self.assertIn(s,[303,401,404])
                self.assertNotIn(b'const NODES',b)
                self.assertIn('no-store',h.get('Cache-Control',''))
        self.assertEqual(self.get('/')[1].get('Location'),'/login.html')

    def test_fixture_session_shared_revoked_outage_logout(self):
        self.login()
        self.assertEqual(self.get('/')[0],200)
        self.assertEqual(self.get('/chat/chat.js?v=old')[0],200)
        self.assertEqual(self.get('/index.html', 'HEAD')[2],b'')
        for path in ['/index.html.bak','/index-backup.html','/server/session.php','/api/venv/bin/python','/../index.html','/%69ndex.html']:
            self.assertEqual(self.get(path)[0],404,path)
        Fixture.mode='unavailable'; self.assertEqual(self.get('/')[0],503)
        Fixture.mode='revoked'; self.assertEqual(self.get('/')[0],303)
        Fixture.mode='ok'; self.assertEqual(self.get('/')[0],303)
        self.login(); self.req('logout',{})
        self.assertEqual(self.get('/')[0],303)
        self.cookie='__Host-jarvis-chat=invalid-not-a-session'
        self.assertEqual(self.get('/chat/chat.js')[0],401)

    def test_nginx_catchall_no_static_or_php_bypass(self):
        path=ROOT/'server/nginx-dashboard.conf'
        self.assertTrue(path.exists(), 'nginx gate routing missing')
        text=path.read_text()
        self.assertIn('SCRIPT_FILENAME /opt/jarvis-access/gate.php',text)
        self.assertIn('location = /login.html',text)
        self.assertIn('location = /api/chat.php',text)
        self.assertIn('fastcgi_hide_header Cache-Control',text)
        self.assertIn('private, no-store',text)
        self.assertNotIn('try_files $uri $uri/',text)
        self.assertIn('return 421',text)

    def test_all_voice_assets_private_and_exact_mime(self):
        import hashlib
        assets={ 'speech.mjs':'application/javascript','session.mjs':'application/javascript','core.mjs':'application/javascript','capture.js':'application/javascript','worker.js':'application/javascript','assets/ort.wasm.min.js':'application/javascript','assets/ort-wasm-simd-threaded.mjs':'application/javascript','assets/ort-wasm-simd-threaded.wasm':'application/wasm','assets/silero_vad_v5.onnx':'application/octet-stream'}
        assets.update({'assets-manifest.json':'application/json',**{name:'text/plain' for name in ['onnxruntime-license.txt','onnxruntime-ThirdPartyNotices.txt','silero-license.txt','vad-license.txt']}})
        for name in assets:
            self.assertEqual(self.get('/chat/voice/'+name)[0],401)
        self.login()
        for name,mime in assets.items():
            s,h,b=self.get('/chat/voice/'+name)
            self.assertEqual(s,200,name);self.assertEqual({k.lower():v for k,v in h.items()}['content-type'].split(';')[0],mime)
            self.assertEqual(hashlib.sha256(b).hexdigest(),hashlib.sha256((ROOT/'chat/voice'/name).read_bytes()).hexdigest())
            self.assertIn('no-store',h['Cache-Control'])
        self.req('logout',{})
        for name in assets:self.assertEqual(self.get('/chat/voice/'+name)[0],401)

    def test_single_public_login_no_local_or_second_form(self):
        login = ROOT/'login.html'
        self.assertTrue(login.exists(), 'public login missing')
        text=login.read_text()
        self.assertEqual(text.count('<form'),1)
        self.assertIn('autocomplete="current-password"',text)
        self.assertIn('/api/chat.php?action=',text)
        for name in ['index.html','chat/chat.js']:
            text=(ROOT/name).read_text()
            self.assertNotIn('mc_authed',text)
            self.assertNotIn('login-overlay',text)
            self.assertNotIn('jarvis-chat-login',text)
            self.assertNotIn('type="password"',text)
        self.assertIn('/login.html',(ROOT/'chat/chat.js').read_text())

if __name__=='__main__': unittest.main(verbosity=2)
