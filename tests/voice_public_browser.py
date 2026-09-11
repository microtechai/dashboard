"""Anonymous production browser only. No login, credentials, permission or protected content injection."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
OUT=Path(__file__).resolve().parents[1]/'docs/evidence/phase7'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
 page=browser.new_page(permissions=[]);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('https://dashboard.microtechai.es/');page.wait_for_url('**/login.html');page.locator('#submit').wait_for()
 assert page.locator('form').count()==1 and page.locator('#jarvis-chat').count()==0 and page.locator('canvas').count()==0
 assert page.locator('[name=password]').input_value()==''
 page.screenshot(path=str(OUT/'public-login.png'))
 report={'url':page.url,'forms':page.locator('form').count(),'privateChat':page.locator('#jarvis-chat').count(),'canvases':page.locator('canvas').count(),'errors':errors,'loginAttempted':False,'microphonePermissionGranted':False}
 assert not errors
 (OUT/'public-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));browser.close()
