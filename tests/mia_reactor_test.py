"""Real software GL with real PHP fixture login; never physical permission or production data."""
import json,os,unittest,time,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from access_gate_test import Access
from chat_backend_test import ROOT,RUN
OUT=ROOT/'docs/evidence/mia';OUT.mkdir(parents=True,exist_ok=True)
class Reactor(unittest.TestCase):
 def test_layout_and_navigation(self):
  Access.setUpClass()
  try:
   origin=f'http://localhost:{Access.pp}'
   baseline_dir=RUN/'mia-baseline';baseline_dir.mkdir(exist_ok=True)
   (baseline_dir/'index.html').write_bytes(subprocess.check_output(['git','show','a8aa284d22f17070d804705c5ce52d10d6da4570:index.html'],cwd=ROOT))
   (RUN/'config.php').write_text('<?php return json_decode('+repr(json.dumps({**Access.cfg,'origin':origin}))+',true);')
   (RUN/'router.php').write_text('<?php define("JARVIS_CHAT_CONFIG",__DIR__."/config.php");define("JARVIS_DOCUMENT_ROOT",($_GET["miaBaseline"]??"")==="1"?'+repr(str(baseline_dir))+':'+repr(str(ROOT))+');$p=parse_url($_SERVER["REQUEST_URI"],PHP_URL_PATH);if($p==="/login.html"){header("Content-Type: text/html");readfile('+repr(str(ROOT/'login.html'))+');exit;}require $p==="/api/chat.php"?'+repr(str(ROOT/'api/chat.php'))+':'+repr(str(ROOT/'server/gate.php'))+';')
   with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=False,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1120},permissions=[]);errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/three.min.js',lambda r:r.fulfill(body=(ROOT/'tests/vendor/three-r128.cjs').read_bytes(),content_type='application/javascript'))
    page.route('**/voice/speech.js',lambda r:r.fulfill(body=(ROOT/'tests/fixtures/legacy-speech.js').read_bytes(),content_type='application/javascript'))
    page.route('**/api/stats.php*',lambda r:r.fulfill(json={'fixture':True}))
    page.add_init_script("window.micCalls=0;navigator.mediaDevices.getUserMedia=async()=>{micCalls++;throw new DOMException('Fixture denied','NotAllowedError')};")
    page.goto(origin+'/');page.wait_for_url('**/login.html')
    for suffix in ['', '?v=old', '?v=20260908-mia1']:
     self.assertEqual(page.request.get(origin+'/reactor/reactor.js'+suffix).status,401)
    page.locator('[name=username]').fill('fixture-user');page.locator('[name=password]').fill('fixture-password');page.locator('#submit').click();page.wait_for_url(origin+'/')
    asset=page.request.get(origin+'/reactor/reactor.js?v=20260908-mia1');self.assertEqual(asset.status,200);self.assertIn('application/javascript',asset.headers['content-type'])
    self.assertEqual(page.request.get(origin+'/reactor/missing.js').status,404)
    page.wait_for_function('typeof renderer!=="undefined"');page.wait_for_timeout(3500)
    # Mobile defaults must be usable without scripted collapsing or losing desktop prefs.
    if not os.getenv('MIA_BEFORE'):
     desktop_pref=page.evaluate('localStorage.getItem("jarvis.executor.minimized")')
     page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(400)
     self.assertTrue(page.locator('#sidebar').evaluate('(e)=>e.classList.contains("collapsed")'),'mobile drawer must start collapsed')
     self.assertEqual(page.locator('#toggle-executor').get_attribute('aria-expanded'),'false','mobile executor must start minimized')
     for selector in ['#sidebarToggle','#toggle-executor']:
      button=page.locator(selector);self.assertTrue(button.get_attribute('aria-label'));button.focus();page.keyboard.press('Enter')
      self.assertEqual(button.get_attribute('aria-expanded'),'true')
      page.keyboard.press('Enter');self.assertEqual(button.get_attribute('aria-expanded'),'false')
     self.assertEqual(page.evaluate('localStorage.getItem("jarvis.executor.minimized")'),desktop_pref)
     page.wait_for_timeout(400)
     page.screenshot(path=str(OUT/'mobile-default.png'))
     self.assertTrue(page.locator('#jarvis-chat-toggle').is_visible())
     page.locator('#jarvis-chat-toggle').click();page.locator('#jarvis-chat-conversation').wait_for()
     for selector in ['#jarvis-chat-input','#jarvis-chat-continuous','#sidebarToggle','#toggle-executor']:
      self.assertTrue(page.locator(selector).evaluate('(e)=>{const b=e.getBoundingClientRect();const hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return e===hit||e.contains(hit)}'),selector+' unobstructed')
     self.assertEqual(page.evaluate('NODES.length'),17)
     self.assertEqual(page.locator('[data-view],[data-page],[data-target]').count(),24)
     page.screenshot(path=str(OUT/'mobile-expanded-chat.png'))
     page.locator('#jarvis-chat-minimize').click()
     page.set_viewport_size({'width':1440,'height':1120});page.wait_for_timeout(400)
     self.assertFalse(page.locator('#sidebar').evaluate('(e)=>e.classList.contains("collapsed")'))
     self.assertEqual(page.locator('#toggle-executor').get_attribute('aria-expanded'),'true')
     if os.getenv('MIA_LAYOUT_ONLY'):browser.close();return
    prefix='before' if os.getenv('MIA_BEFORE') else 'after'
    metrics=[]
    for name,w,h in [('desktop',1440,1120),('mobile',390,844)]:
     page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(500)
     page.screenshot(path=str(OUT/f'{prefix}-{name}.png'))
     metrics.append(page.evaluate('({calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,geometries:renderer.info.memory.geometries})'))
    (OUT/f'{prefix}-metrics.json').write_text(json.dumps(metrics,indent=2))
    if os.getenv('MIA_BEFORE'):return
    page.locator('#jarvis-chat-toggle').click();page.locator('#jarvis-chat-conversation').wait_for()
    page.set_viewport_size({'width':1440,'height':1120});page.wait_for_timeout(200)
    box=page.locator('#jarvis-chat-panel').bounding_box()
    self.assertAlmostEqual(box['x']+box['width']/2,720,delta=30,msg='single bar is viewport centered')
    self.assertTrue(page.evaluate('!!window.MiaReactor'),'new scoped reactor is present')
    self.assertEqual(page.evaluate('NODES.length'),17)
    baseline=json.loads((ROOT/'tests/fixtures/mia-nav-baseline.json').read_text())
    self.assertEqual(page.evaluate('NODES.map(n=>n.id)'),baseline['nodes'])
    for item in baseline['ids']:self.assertEqual(page.locator('[id="'+item['id']+'"]').count(),1,item['id'])
    if os.getenv('MIA_PROFILE'):
     profile=page.evaluate((ROOT/'tests/mia_profile.js').read_text())
     (OUT/'bounded-profile.json').write_text(json.dumps(profile,indent=2));print(json.dumps(profile,indent=2));browser.close();return
    perf=page.evaluate('''async()=>{const frames=[];let last=performance.now();const geos=renderer.info.memory.geometries;for(let i=0;i<90;i++){await new Promise(requestAnimationFrame);const gl=renderer.getContext();gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array(4));const now=performance.now();frames.push(now-last);last=now;}frames.sort((a,b)=>a-b);return {p95:frames[Math.floor(frames.length*.95)],max:Math.max(...frames),calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,geometryGrowth:renderer.info.memory.geometries-geos};}''')
    page.goto(origin+'/?miaBaseline=1');page.wait_for_timeout(3500)
    oldperf=page.evaluate('''async()=>{const frames=[];let last=performance.now();for(let i=0;i<90;i++){await new Promise(requestAnimationFrame);const gl=renderer.getContext();gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array(4));const now=performance.now();frames.push(now-last);last=now;}frames.sort((a,b)=>a-b);return {p95:frames[Math.floor(frames.length*.95)],max:Math.max(...frames)};}''')
    limit=max(250,oldperf['p95']*1.5+30)
    (OUT/'render-performance.json').write_text(json.dumps({'softwareGL':True,'measurement':perf,'baselineTiming':oldperf,'p95Guard':limit,'baselineCommit':'a8aa284d22f17070d804705c5ce52d10d6da4570','baselineGeometryCounts':json.loads((OUT/'before-metrics.json').read_text()),'hardwareBenchmark':False},indent=2))
    self.assertLess(perf['p95'],limit);self.assertLess(perf['calls'],200);self.assertLess(perf['triangles'],100000);self.assertEqual(perf['geometryGrowth'],0)
    page.goto(origin+'/');page.wait_for_timeout(3500);page.locator('#jarvis-chat-toggle').click();page.locator('#jarvis-chat-conversation').wait_for()
    nav=page.locator('[data-view],[data-page],[data-target]')
    self.assertEqual(nav.count(),len(baseline['navigation']))
    page.locator('#jarvis-chat-input').fill('Preservar entrada fixture')
    for i in range(nav.count()):
     target=nav.nth(i)
     ancestor=target.locator('xpath=..')
     parent_id=ancestor.get_attribute('id')
     if parent_id in ['proj-sub','srv-sub','ai-sub'] and not ancestor.evaluate('(e)=>e.classList.contains("open")'):
      page.locator('[data-target="'+parent_id+'"]').click()
     target.click();page.wait_for_timeout(50)
     if target.get_attribute('data-page'):
      self.assertFalse(page.evaluate('fireController.group.visible'))
      self.assertIn('sin conexión',page.locator('#services-list').inner_text())
    self.assertEqual(page.locator('#jarvis-chat-input').input_value(),'Preservar entrada fixture')
    page.locator('.nav-btn[data-view=projects]').click()
    self.assertTrue(page.locator('#jarvis-chat-panel').is_hidden(),'modules minimize theater without destroying composer')
    page.locator('.nav-btn[data-view=dashboard]').click()
    page.locator('#closeBtn').click()
    page.locator('#jarvis-chat-toggle').click()
    for name,w,h in [('desktop-bar',1440,1120),('mobile-bar',390,844)]:
     page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(300)
     if w<760 and not page.locator('#sidebar').evaluate('(e)=>e.classList.contains("collapsed")'):page.locator('#sidebarToggle').click()
     if w<760 and page.locator('#toggle-executor').get_attribute('aria-expanded')=='true':page.locator('#toggle-executor').click()
     page.screenshot(path=str(OUT/f'after-{name}.png'))
     if w>760:
      page.mouse.move(720,300);page.mouse.down();page.mouse.move(810,330,steps=8);page.mouse.up();page.wait_for_timeout(400)
      page.screenshot(path=str(OUT/'after-desktop-angle.png'))
      page.mouse.move(810,330);page.mouse.down();page.mouse.move(720,300,steps=8);page.mouse.up();page.wait_for_timeout(400)
     for selector in ['#jarvis-chat-continuous','#jarvis-chat-mute','#jarvis-chat-input','#jarvis-chat-stop']:
      b=page.locator(selector).bounding_box();self.assertIsNotNone(b);self.assertGreaterEqual(b['x'],0);self.assertGreaterEqual(b['y'],0);self.assertLessEqual(b['x']+b['width'],w);self.assertLessEqual(b['y']+b['height'],h)
    (OUT/'navigation-matrix.json').write_text(json.dumps({'entries':baseline['navigation'],'nodes':baseline['nodes'],'errors':errors,'permissionCalls':page.evaluate('micCalls'),'MCendToEnd':False},indent=2))
    self.assertEqual(page.locator('#jarvis-chat-compose').count(),1)
    self.assertEqual(page.locator('#mia-metrics-toggle').count(),1,'mobile metrics must remain reachable')
    page.locator('#mia-metrics-toggle').click()
    self.assertTrue(page.locator('#metrics-panel').is_visible())
    page.locator('#mia-metrics-toggle').click()
    self.assertEqual(page.evaluate('micCalls'),0)
    self.assertEqual(errors,[])
    page.add_init_script("const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...a){return /webgl/i.test(type)?null:get.call(this,type,...a)};")
    page.reload();page.locator('.nav-btn[data-view=projects]').click()
    self.assertTrue(page.locator('#mia-render-status').is_visible(),'GL failure must not remove navigation')
    self.assertEqual(page.locator('#jarvis-chat-compose').count(),1)
    self.assertEqual(errors,[])
    browser.close()
  finally:Access.tearDownClass()
if __name__=='__main__':unittest.main(verbosity=2)
