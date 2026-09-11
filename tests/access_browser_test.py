"""Browser + real PHP gate/login HTTP; MC is an isolated existing TEST FIXTURE.
No auth injection/storage overrides, no production accounts or credentials.
Protected HTML is a minimal test document, not visual/dashboard QA.
"""
import json, unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
from access_gate_test import Access
from chat_backend_test import ROOT, RUN, Fixture

class BrowserAccess(unittest.TestCase):
    def test_login_once_shared_chat_sidebar_logout_and_denial(self):
        Access.setUpClass()
        try:
            origin=f'http://localhost:{Access.pp}'
            cfg={**Access.cfg,'origin':origin}
            (RUN/'config.php').write_text('<?php return json_decode('+repr(json.dumps(cfg))+',true);')
            doc=RUN/'doc'; (doc/'chat').mkdir(parents=True)
            (doc/'index.html').write_text('<!doctype html><title>Protected FIXTURE</title><button class="sidebar-logout">Cerrar sesión</button><script src="/chat/chat.js" defer></script>')
            (doc/'chat/chat.js').write_bytes((ROOT/'chat/chat.js').read_bytes())
            (RUN/'router.php').write_text('<?php define("JARVIS_CHAT_CONFIG",__DIR__."/config.php"); define("JARVIS_DOCUMENT_ROOT",__DIR__."/doc"); $p=parse_url($_SERVER["REQUEST_URI"],PHP_URL_PATH); if($p==="/login.html"){header("Content-Type: text/html");readfile('+repr(str(ROOT/'login.html'))+');exit;} require $p==="/api/chat.php"?'+repr(str(ROOT/'api/chat.php'))+':'+repr(str(ROOT/'server/gate.php'))+';')
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                page=browser.new_page(); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(origin+'/'); page.wait_for_url('**/login.html')
                self.assertEqual(page.locator('form').count(),1)
                self.assertEqual(page.locator('#jarvis-chat').count(),0)
                page.locator('[name=username]').fill('fixture-user')
                page.locator('[name=password]').fill('fixture-password')
                page.locator('#submit').click(); page.wait_for_url(origin+'/')
                page.locator('#jarvis-chat-toggle').click()
                page.locator('#jarvis-chat-conversation').wait_for(state='visible')
                self.assertEqual(page.locator('input[type=password]').count(),0)
                self.assertIn('fixture-user',page.locator('#jarvis-chat-status').inner_text())
                page.locator('.sidebar-logout').click(); page.wait_for_url('**/login.html')
                page.goto(origin+'/index.html'); page.wait_for_url('**/login.html')
                page.locator('[name=username]').fill('fixture-user')
                page.locator('[name=password]').fill('fixture-password')
                page.locator('#submit').click(); page.wait_for_url(origin+'/')
                Fixture.mode='revoked'
                page.reload(); page.wait_for_url('**/login.html')
                self.assertEqual(errors,[])
                browser.close()
        finally: Access.tearDownClass()

if __name__=='__main__':unittest.main(verbosity=2)
