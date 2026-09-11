"""Actual candidate render and keyboard contracts via isolated real PHP form login."""
import unittest,json,os,time
from pathlib import Path
from playwright.sync_api import sync_playwright
from access_gate_test import Access
from chat_backend_test import ROOT,RUN
OUT=ROOT/'docs/evidence/mia/redesign';OUT.mkdir(parents=True,exist_ok=True)
class Redesign(unittest.TestCase):
 def test_center_context_and_core_states(self):
  Access.setUpClass()
  try:
   origin=f'http://localhost:{Access.pp}'
   (RUN/'config.php').write_text('<?php return json_decode('+repr(json.dumps({**Access.cfg,'origin':origin}))+',true);')
   (RUN/'router.php').write_text('<?php define("JARVIS_CHAT_CONFIG",__DIR__."/config.php");define("JARVIS_DOCUMENT_ROOT",'+repr(str(ROOT))+');$p=parse_url($_SERVER["REQUEST_URI"],PHP_URL_PATH);if($p==="/login.html"){header("Content-Type: text/html");readfile('+repr(str(ROOT/'login.html'))+');exit;}require $p==="/api/chat.php"?'+repr(str(ROOT/'api/chat.php'))+':'+repr(str(ROOT/'server/gate.php'))+';')
   with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=False,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1120},permissions=[]);errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/three.min.js',lambda r:r.fulfill(body=(ROOT/'tests/vendor/three-r128.cjs').read_bytes(),content_type='application/javascript'))
    page.route('**/voice/speech.js',lambda r:r.fulfill(body=(ROOT/'tests/fixtures/legacy-speech.js').read_bytes(),content_type='application/javascript'))
    page.route('**/api/stats.php*',lambda r:r.fulfill(json={'fixture':True}))
    page.add_init_script("window.micCalls=0;window.legacyConstructors=0;window.SpeechRecognition=class {constructor(){legacyConstructors++}start(){micCalls++}};navigator.mediaDevices.getUserMedia=async()=>{micCalls++;throw new DOMException('Fixture denied','NotAllowedError')};")
    page.goto(origin+'/');page.wait_for_url('**/login.html')
    page.locator('[name=username]').fill('fixture-user');page.locator('[name=password]').fill('fixture-password');page.locator('#submit').click();page.wait_for_url(origin+'/')
    page.wait_for_function('typeof renderer!=="undefined"');page.wait_for_timeout(1500)
    before=bool(os.getenv('MIA_REDESIGN_BEFORE'));prefix='before' if before else 'after'
    perf=page.evaluate('''async()=>{const a=[];const geos=renderer.info.memory.geometries;const gl=renderer.getContext();let last=performance.now();for(let i=0;i<30;i++){await new Promise(requestAnimationFrame);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array(4));let now=performance.now();a.push(now-last);last=now}a.sort((a,b)=>a-b);return {geometryGrowth:renderer.info.memory.geometries-geos,p95:a[Math.floor(a.length*.95)],calls:renderer.info.render.calls,triangles:renderer.info.render.triangles}}''')
    (OUT/(prefix+'-performance.json')).write_text(json.dumps({'softwareGL':True,'measurement':perf,'hardwareAcceptance':'pending','technical250msBudgetPassed':perf['p95']<=250},indent=2))
    for name,w,h in [('desktop',1440,1120),('mobile',390,844)]:
     page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(450)
     page.screenshot(path=str(OUT/(prefix+'-'+name+'.png')))
    if before:browser.close();return
    page.set_viewport_size({'width':1440,'height':1120});page.wait_for_timeout(500)
    target=page.locator('#sidebar').bounding_box()['width'];target=(1440+target)/2
    x=page.evaluate('()=>{const v=fireController.group.position.clone().project(camera);return (v.x+1)*innerWidth/2}')
    self.assertAlmostEqual(x,target,delta=3,msg='reactor centered in available content, not viewport')
    b=page.locator('#jarvis-chat-toggle').bounding_box();self.assertAlmostEqual(b['x']+b['width']/2,target,delta=3)
    self.assertEqual(page.locator('[data-mia-node]').count(),17)
    self.assertEqual(page.locator('[data-view],[data-page],[data-target]').count(),24)
    details=page.locator('#mia-context');details.locator('summary').focus();page.keyboard.press('Enter')
    self.assertTrue(details.evaluate('(e)=>e.open'))
    nodes=page.evaluate('NODES.map(n=>n.id)')
    for nid in nodes:
     page.locator('[data-mia-node="'+nid+'"]').click();self.assertTrue(page.locator('#sidePanel').evaluate('(e)=>e.classList.contains("open")'));page.locator('#closeBtn').click()
    details.locator('summary').focus();page.keyboard.press('Enter')
    page.locator('#jarvis-chat-toggle').click();page.locator('#jarvis-chat-conversation').wait_for()
    self.assertEqual(page.locator('#mia-pipeline').count(),0)
    for state,color in [('listening',0x22d3ee),('transcribing',0x22d3ee),('thinking',0xd6a343),('speaking',0x2dd4a0),('idle',0x249ac2)]:
     page.evaluate('(state)=>dispatchEvent(new CustomEvent("jarvis-chat-state",{detail:{state,level:0}}))',state)
     page.wait_for_function('(color)=>{let found=false;fireController.group.traverse(o=>{if(o.geometry?.type==="IcosahedronGeometry")found=o.material.emissive.getHex()===color});return found}',arg=color)
    page.emulate_media(reduced_motion='reduce')
    page.evaluate('dispatchEvent(new CustomEvent("jarvis-chat-state",{detail:{state:"thinking",level:0}}))')
    page.wait_for_timeout(100)
    snapshot='()=>{const values=[];fireController.group.traverse(o=>{if(o.isMesh)values.push([o.scale.toArray(),o.rotation.toArray(),o.material.emissiveIntensity,o.material.uniforms?.power?.value])});return values}'
    frozen=page.evaluate(snapshot);page.wait_for_timeout(150)
    self.assertEqual(page.evaluate(snapshot),frozen)
    page.emulate_media(reduced_motion='no-preference')
    self.assertIsNone(page.evaluate('()=>{checkHover(innerWidth/2,innerHeight/3);return hoveredNode}'))
    for w,h,name in [(1440,1120,'desktop-chat'),(768,1024,'tablet-chat'),(390,844,'mobile-chat')]:
     page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(400)
     page.screenshot(path=str(OUT/('after-'+name+'.png')))
     if not page.locator('#jarvis-chat-options').evaluate('(e)=>e.open'):
      page.locator('#jarvis-chat-options > summary').click()
     for sel in ['#jarvis-chat-input','#jarvis-chat-continuous','#jarvis-chat-mute','#jarvis-chat-compose button[type=submit]','#jarvis-chat-logout','#sidebarToggle','#toggle-executor']:
      needs_options=sel in ['#jarvis-chat-continuous','#jarvis-chat-mute','#jarvis-chat-logout']
      is_open=page.locator('#jarvis-chat-options').evaluate('(e)=>e.open')
      if needs_options and not is_open: page.locator('#jarvis-chat-options > summary').click()
      if not needs_options and is_open: page.locator('#jarvis-chat-options > summary').click()
      hit=page.locator(sel).evaluate('(e)=>{const b=e.getBoundingClientRect();const h=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return {ok:e===h||e.contains(h),bounds:b.toJSON(),hit:h?.outerHTML.slice(0,500)}}')
      self.assertTrue(hit['ok'],sel+' reachable '+name+' '+json.dumps(hit))
     self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),w)
    self.assertEqual(page.evaluate('micCalls'),0);self.assertEqual(page.evaluate('legacyConstructors'),0,'one voice owner; legacy stays on disk, not instantiated');self.assertEqual(errors,[])
    self.assertEqual(perf['geometryGrowth'],0);self.assertLess(perf['calls'],200);self.assertLess(perf['triangles'],100000)
    self.assertLess(perf['p95'],600,'fixed gross-regression guard, NOT technical performance acceptance')
    (OUT/'layout.json').write_text(json.dumps({'nodes':nodes,'navigation':24,'centerX':x,'expectedCenterX':target,'pageErrors':errors,'permissionCalls':0,'fixtureLogin':True,'hardwarePending':True},indent=2))
    browser.close()
  finally:Access.tearDownClass()
if __name__=='__main__':unittest.main(verbosity=2)
