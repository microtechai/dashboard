"""Isolated real PHP login/gate + real Chromium/ONNX/worklet. MC/model/STT/TTS fixtures explicitly labeled; no physical mic permission."""
import json, unittest, shutil, os
from playwright.sync_api import sync_playwright
from access_gate_test import Access
from chat_backend_test import ROOT,RUN,Fixture
OUT=ROOT/'docs/evidence/call';OUT.mkdir(parents=True,exist_ok=True)
class VoiceBargeIn(unittest.TestCase):
 def test_real_vad_double_bargein_and_shutdown(self):
  Access.setUpClass()
  try:
   origin=f'http://localhost:{Access.pp}'
   (RUN/'config.php').write_text('<?php return json_decode('+repr(json.dumps({**Access.cfg,'origin':origin}))+',true);')
   (RUN/'router.php').write_text('<?php define("JARVIS_CHAT_CONFIG",__DIR__."/config.php");define("JARVIS_DOCUMENT_ROOT",'+repr(str(ROOT))+');$p=parse_url($_SERVER["REQUEST_URI"],PHP_URL_PATH);if($p==="/login.html"){header("Content-Type: text/html");readfile('+repr(str(ROOT/'login.html'))+');exit;}require $p==="/api/chat.php"?'+repr(str(ROOT/'api/chat.php'))+':'+repr(str(ROOT/'server/gate.php'))+';')
   with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=not bool(os.environ.get('JARVIS_HEADFUL')),args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1280,'height':900},permissions=[]);errors=[];uploads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda msg:print('BROWSER',msg.text) if msg.text.startswith('CALL-TRACE') else None)
    page.add_init_script("addEventListener('DOMContentLoaded',()=>{window.callTrace=[];const el=document.querySelector('#jarvis-chat-status');if(el)new MutationObserver(()=>{callTrace.push(el.textContent);console.log('CALL-TRACE '+el.textContent);}).observe(el,{childList:true,subtree:true});});")
    page.route('**/voice/speech.js',lambda r:r.fulfill(body=(ROOT/'tests/fixtures/legacy-speech.js').read_bytes(),content_type='application/javascript'))
    page.add_init_script("window.legacyStarts=0;const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(R)R.prototype.start=function(){legacyStarts++;throw Error('QA forbids physical WebSpeech');};")
    page.route('**/api/stats.php*',lambda r:r.fulfill(json={'fixture':True}))
    page.route('**/three.min.js',lambda r:r.fulfill(body=(ROOT/'tests/vendor/three-r128.cjs').read_bytes(),content_type='application/javascript'))
    page.route('**/api/chat.php?action=tts',lambda r:r.fulfill(body=(ROOT/'tests/fixtures/voice-check.wav').read_bytes(),content_type='audio/wav'))
    def stt(r):
     import email.parser,email.policy,io,wave
     uploads.append(r.request.post_data_buffer)
     message=email.parser.BytesParser(policy=email.policy.default).parsebytes(('Content-Type: '+r.request.headers['content-type']+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+uploads[-1])
     wav=next(message.iter_parts()).get_payload(decode=True)
     with wave.open(io.BytesIO(wav)) as w:
      self.assertEqual((w.getnchannels(),w.getsampwidth(),w.getframerate()),(1,2,16000));self.assertLessEqual(w.getnframes(),320000)
     self.assertLessEqual(len(wav),640044)
     if len(uploads)==1:(OUT/'captured-browser.wav').write_bytes(wav)
     r.fulfill(json={'text':'Fixture de transcripción'})
    page.route('**/api/chat.php?action=transcribe',stt)
    page.route('**/fixture.wav',lambda r:r.fulfill(body=(ROOT/'tests/fixtures/voice-check.wav').read_bytes(),content_type='audio/wav'))
    # Silence AFTER the analyser using a real zero-gain output node: muting the
    # HTMLAudio element itself yields zero samples and cannot test output RMS.
    page.add_init_script('''const NativeContext=AudioContext;window.AudioContext=class extends NativeContext{constructor(...args){super(...args);const silent=this.createGain();silent.gain.value=0;silent.connect(this.destination);Object.defineProperty(this,'destination',{value:silent});}};window.micCalls=0;window.ttsAudios=[];const NativeAudio=Audio;window.Audio=function(...args){const a=new NativeAudio(...args);ttsAudios.push(a);return a;};navigator.mediaDevices.getUserMedia=async constraints=>{micCalls++;window.constraints=constraints;return window.fakeDest.stream;};''')
    page.add_init_script("window.miaObserved={input:0,output:0};window.miaSignalSamples=[];addEventListener('mia-audio-level',e=>{if(e.detail.channel==='input'){miaObserved.input=Math.max(miaObserved.input,e.detail.level);if(miaSignalSamples.length<4096)miaSignalSamples.push({at:performance.now(),channel:'input',rms:e.detail.level});}});addEventListener('jarvis-chat-state',e=>{if(e.detail.state==='speaking'){miaObserved.output=Math.max(miaObserved.output,e.detail.level);if(miaSignalSamples.length<4096)miaSignalSamples.push({at:performance.now(),channel:'output',rms:e.detail.level,micActive:e.detail.micActive});}});")
    page.add_init_script('''window.vadTimes=[];window.maxPending=0;const NativeWorker=Worker;window.Worker=class extends NativeWorker{constructor(...a){super(...a);this.times=[];this.addEventListener('message',e=>{if(e.data.type==='frame'){vadTimes.push(performance.now()-this.times.shift());}});}postMessage(data,...args){if(data.type==='frame'){this.times.push(performance.now());maxPending=Math.max(maxPending,this.times.length);}return super.postMessage(data,...args);}};''')
    page.goto(origin+'/');page.wait_for_url('**/login.html');page.locator('[name=username]').fill('fixture-user');page.locator('[name=password]').fill('fixture-password');page.locator('#submit').click();page.wait_for_url(origin+'/')
    page.locator('#jarvis-chat-toggle').click();page.locator('#jarvis-chat-conversation').wait_for()
    # Observe the existing render owner, never install another animation loop.
    page.evaluate('''()=>{window.miaFrameSamples=[];const c=dashboardFireController,update=c.update.bind(c);const nucleus=c.group.children.find(o=>o.geometry?.type==='IcosahedronGeometry');const arc=c.group.children.find(o=>o.userData.arc&&o.material.uniforms.power.value>.5);c.update=function(dt){update(dt);if(miaFrameSamples.length<4096){const levels=c.levels,a=ttsAudios.at(-1);miaFrameSamples.push({at:performance.now(),input:levels.input,output:levels.output,emissive:nucleus.material.emissiveIntensity,arcPower:arc.material.uniforms.power.value,playing:!!a&&!a.paused,audioTime:a?.currentTime||0});}};}''')
    self.assertEqual(page.evaluate('micCalls'),0)
    self.assertTrue(page.evaluate('window.voiceSystem===undefined'),'chat is the only voice owner; legacy stays private on disk')
    self.assertEqual(page.locator('#voice-mic-btn').count(),0)
    page.keyboard.press('Control+m');self.assertEqual(page.evaluate('legacyStarts'),0)
    self.assertEqual(page.locator('#jarvis-chat-continuous').count(),1,'continuous button required')
    page.evaluate('''async()=>{window.fakeContext=new AudioContext();await fakeContext.resume();window.fakeDest=fakeContext.createMediaStreamDestination();const raw=await(await fetch('/fixture.wav')).arrayBuffer();window.fixtureBuffer=await fakeContext.decodeAudioData(raw);window.injectSpeech=()=>{const s=fakeContext.createBufferSource();s.buffer=fixtureBuffer;s.connect(fakeDest);s.start();};}''')
    page.locator('#jarvis-chat-continuous').click();page.wait_for_function("document.querySelector('#jarvis-chat-mic').dataset.state==='active'",timeout=30000)
    self.assertEqual(page.evaluate('micCalls'),1)
    self.assertEqual(page.locator('#jarvis-chat-continuous').inner_text(),'Colgar')
    micCalls=page.evaluate('micCalls');pauses=[]
    self.assertTrue(page.evaluate('constraints.audio.echoCancellation'));self.assertTrue(page.evaluate('constraints.audio.noiseSuppression'));self.assertTrue(page.evaluate('constraints.audio.autoGainControl'))
    self.assertFalse(page.locator('#jarvis-chat-autoread').is_checked())
    page.evaluate('''()=>{window.injectNoise=()=>{const b=fakeContext.createBuffer(1,Math.floor(fakeContext.sampleRate*1.2),fakeContext.sampleRate),d=b.getChannelData(0);let seed=7;for(let i=0;i<d.length;i++){seed=(1664525*seed+1013904223)>>>0;const t=i/fakeContext.sampleRate;d[i]=.025*(seed/4294967296*2-1)+.025*Math.sin(2*Math.PI*440*t)+(t%.3<.015?.3*Math.exp(-(t%.3)*200):0);}const s=fakeContext.createBufferSource();s.buffer=b;s.connect(fakeDest);s.start();};}''')
    page.evaluate('''()=>{const tone=fakeContext.createOscillator();const gain=fakeContext.createGain();gain.gain.value=.1;tone.connect(gain);gain.connect(fakeDest);tone.frequency.value=440;tone.start();tone.stop(fakeContext.currentTime+1);}''')
    page.wait_for_timeout(2200);self.assertEqual(len(uploads),0)
    page.evaluate('injectNoise()');page.wait_for_timeout(2100);self.assertEqual(len(uploads),0)
    # Quiet synthetic residual speech is below energy floor, not a physical AEC test.
    page.evaluate('''()=>{const s=fakeContext.createBufferSource(),g=fakeContext.createGain();s.buffer=fixtureBuffer;g.gain.value=.0005;s.connect(g);g.connect(fakeDest);s.start();s.stop(fakeContext.currentTime+1);}''');page.wait_for_timeout(1800);self.assertEqual(len(uploads),0)
    page.evaluate('injectSpeech()');page.wait_for_function('ttsAudios.some(a=>!a.paused)',timeout=25000)
    page.wait_for_function('miaFrameSamples.some(s=>s.playing&&s.output>.001)',timeout=5000)
    rms=page.evaluate('({observed:miaObserved,samples:miaFrameSamples,signals:miaSignalSamples})')
    self.assertGreater(rms['observed']['input'],.001)
    self.assertTrue(any(s['playing'] and s['output']>.001 for s in rms['samples']))
    for sample in rms['samples']:
     level=max(sample['input'],sample['output'])
     self.assertAlmostEqual(sample['emissive'],1.3+level,places=7)
     self.assertAlmostEqual(sample['arcPower'],.85+level*.5,places=7)
    (ROOT/'docs/evidence/mia/audio-rms.json').write_text(json.dumps({'source':'real WebAudio/ONNX synthetic fixture, not physical mic','levels':rms},indent=2))
    page.evaluate('window.noiseAudio=ttsAudios.at(-1);injectNoise()');page.wait_for_timeout(1500)
    self.assertFalse(page.evaluate('noiseAudio.paused'),'noise/knocks/tone must not interrupt playing audio');self.assertEqual(len(uploads),1)
    for turn in range(2):
     page.evaluate('window.oldAudio=ttsAudios.at(-1);window.bargeStart=performance.now();injectSpeech()')
     page.wait_for_function('oldAudio.paused',timeout=4000)
     pauses.append(page.evaluate('performance.now()-bargeStart'))
     self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'live')
     page.wait_for_function('ttsAudios.at(-1)!==oldAudio&&!ttsAudios.at(-1).paused',timeout=25000)
    self.assertEqual(len(uploads),3)
    page.wait_for_function('ttsAudios.at(-1).paused',timeout=12000);page.wait_for_timeout(1200);self.assertEqual(len(uploads),3)
    self.assertEqual(page.evaluate('dashboardFireController.levels.output'),0,'ended audio must decay to zero')
    self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'live')
    perf=page.evaluate('({roundTripMs:vadTimes,maxPending})');self.assertLessEqual(perf['maxPending'],16)
    page.locator('#jarvis-chat-mute').click()
    self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'ended')
    page.wait_for_function('dashboardFireController.levels.input===0',timeout=2000)
    rms['negativeControls']={'endedOutputZero':True,'mutedInputZero':True}
    (ROOT/'docs/evidence/mia/audio-rms.json').write_text(json.dumps({'source':'real WebAudio/ONNX synthetic fixture, zero output gain AFTER analyser; no physical mic','levels':rms},indent=2))
    self.assertEqual(page.locator('#jarvis-chat-continuous').inner_text(),'Colgar')
    self.assertIn('silenciado',page.locator('#jarvis-chat-mic').inner_text())
    page.evaluate('injectSpeech()');page.wait_for_timeout(1500);self.assertEqual(len(uploads),3)
    page.screenshot(path=str(OUT/'call-muted.png'))
    page.evaluate('window.fakeDest=fakeContext.createMediaStreamDestination()')
    page.locator('#jarvis-chat-mute').click();page.wait_for_function("document.querySelector('#jarvis-chat-mic').dataset.state==='active'")
    self.assertEqual(page.evaluate('micCalls'),2)
    page.locator('#jarvis-chat-continuous').click()
    self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'ended')
    page.wait_for_timeout(1500);self.assertEqual(len(uploads),3)
    page.screenshot(path=str(OUT/'continuous-fixture.png'))
    page.set_viewport_size({'width':390,'height':650})
    page.screenshot(path=str(OUT/'continuous-mobile.png'))
    for selector in ['#jarvis-chat-mic','#jarvis-chat-continuous','#jarvis-chat-talk','#jarvis-chat-stop']:
     box=page.locator(selector).bounding_box();self.assertGreaterEqual(box['y'],0);self.assertLessEqual(box['y']+box['height'],650)
    self.assertLessEqual(page.evaluate("document.querySelector('#jarvis-chat-panel').scrollHeight-document.querySelector('#jarvis-chat-panel').clientHeight"),1,'all controls fit without clipping')
    page.set_viewport_size({'width':1280,'height':900})
    # Stale STT ignores AbortSignal deliberately: response generation must reject it.
    page.evaluate('''()=>{window.fakeDest=fakeContext.createMediaStreamDestination();const real=fetch;window.fetch=(u,o)=>String(u).includes('action=transcribe')?new Promise(r=>{window.staleSignal=o.signal;window.releaseStale=()=>r(new Response(JSON.stringify({text:'STALE MUST NOT SEND'}),{headers:{'Content-Type':'application/json'}}));}):real(u,o);}''')
    page.locator('#jarvis-chat-continuous').click();page.wait_for_function("document.querySelector('#jarvis-chat-mic').dataset.state==='active'")
    page.evaluate('injectSpeech()');page.wait_for_function('window.releaseStale!==undefined',timeout=20000)
    before=len(Fixture.requests);page.locator('#jarvis-chat-stop').click();self.assertTrue(page.evaluate('staleSignal.aborted'))
    page.evaluate('releaseStale()');page.wait_for_timeout(300);self.assertEqual(len(Fixture.requests),before)
    self.assertNotIn('STALE MUST NOT SEND',page.locator('#jarvis-chat-history').inner_text())
    self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'live')
    # A hung response deadline shuts down the mic, never retries.
    page.evaluate('''()=>{const real=setTimeout;window.setTimeout=(fn,ms,...a)=>{if(ms===65000)window.deadline=fn;return real(fn,ms,...a);};window.fetch=(u,o)=>String(u).includes('action=message')?new Promise(()=>{}):Promise.reject(Error('unexpected request'));}''')
    page.locator('#jarvis-chat-input').fill('Timeout fixture');page.locator('#jarvis-chat-input').press('Enter');page.wait_for_function('window.deadline!==undefined');page.evaluate('deadline()')
    self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'ended')
    # Permission remains user-driven; late grant after Finish closes the returned track.
    page.evaluate('''()=>{window.fakeDest=fakeContext.createMediaStreamDestination();navigator.mediaDevices.getUserMedia=()=>{micCalls++;return new Promise(r=>window.grantLate=()=>r(fakeDest.stream));};}''')
    page.locator('#jarvis-chat-continuous').click();page.locator('#jarvis-chat-continuous').click();page.evaluate('grantLate()');page.wait_for_timeout(100)
    self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'ended')
    page.evaluate("()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('fixture denial','NotAllowedError')};}")
    page.locator('#jarvis-chat-continuous').click();page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('Usa')||document.querySelector('#jarvis-chat-status').textContent.includes('Puedes')")
    self.assertEqual(page.locator('#jarvis-chat-mic').get_attribute('data-state'),'off')
    # Recreate page for real login-session fetch and forced worker failure.
    page.reload();page.locator('#jarvis-chat-toggle').click();page.locator('#jarvis-chat-conversation').wait_for()
    page.evaluate('''async()=>{window.fakeContext=new AudioContext();await fakeContext.resume();window.fakeDest=fakeContext.createMediaStreamDestination();}''')
    page.route('**/chat/voice/worker.js',lambda r:r.fulfill(status=404,body='missing worker fixture'))
    page.locator('#jarvis-chat-continuous').click();page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('Usa Hablar')",timeout=25000)
    self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'ended')
    page.unroute('**/chat/voice/worker.js')
    # Start again then session revocation (401) closes mic and goes to public login.
    page.evaluate('window.fakeDest=fakeContext.createMediaStreamDestination()')
    page.locator('#jarvis-chat-continuous').click();page.wait_for_function("document.querySelector('#jarvis-chat-mic').dataset.state==='active'")
    self.assertNotIn('Voz continua cerrada',page.locator('#jarvis-chat-status').inner_text())
    page.screenshot(path=str(OUT/'continuous-active.png'))
    rateCalls=[]
    def rate(r):rateCalls.append(1);r.fulfill(status=429,json={'error':'Límite fixture 6/min'})
    page.route('**/api/chat.php?action=message',rate)
    page.locator('#jarvis-chat-input').fill('429 fixture');page.locator('#jarvis-chat-input').press('Enter');page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('6/min')")
    self.assertEqual(page.evaluate('fakeDest.stream.getTracks()[0].readyState'),'ended');page.wait_for_timeout(1200);self.assertEqual(len(rateCalls),1)
    page.unroute('**/api/chat.php?action=message')
    page.evaluate('window.fakeDest=fakeContext.createMediaStreamDestination()');page.locator('#jarvis-chat-continuous').click();page.wait_for_function("document.querySelector('#jarvis-chat-mic').dataset.state==='active'")
    page.evaluate("window.trackEnded=false;const t=fakeDest.stream.getTracks()[0];const stop=t.stop.bind(t);t.stop=()=>{window.trackEnded=true;stop();};window.addEventListener('pagehide',()=>sessionStorage.setItem('fixtureTrackEnded',String(trackEnded)))")
    Fixture.mode='revoked'
    page.locator('#jarvis-chat-input').fill('401 fixture');page.locator('#jarvis-chat-input').press('Enter')
    try:page.wait_for_url('**/login.html',timeout=10000)
    except Exception:
     print('401 DIAGNOSTIC',page.locator('body').inner_text(),Fixture.requests);raise
    self.assertEqual(page.evaluate("sessionStorage.getItem('fixtureTrackEnded')"),'true')
    Fixture.mode='ok'
    page.locator('[name=username]').fill('fixture-user');page.locator('[name=password]').fill('fixture-password');page.locator('#submit').click();page.wait_for_url(origin+'/');page.locator('#jarvis-chat-toggle').click()
    page.evaluate('''async()=>{window.fakeContext=new AudioContext();await fakeContext.resume();window.fakeDest=fakeContext.createMediaStreamDestination();}''')
    page.locator('#jarvis-chat-continuous').click();page.wait_for_function("document.querySelector('#jarvis-chat-mic').dataset.state==='active'")
    page.evaluate("window.trackEnded=false;const t=fakeDest.stream.getTracks()[0];const stop=t.stop.bind(t);t.stop=()=>{window.trackEnded=true;stop();};window.addEventListener('pagehide',()=>sessionStorage.setItem('logoutTrackEnded',String(trackEnded)))")
    page.locator('.sidebar-logout').click();page.wait_for_url('**/login.html')
    self.assertEqual(page.evaluate("sessionStorage.getItem('logoutTrackEnded')"),'true')
    times=sorted(perf.pop('roundTripMs'));perf.update(frames=len(times),roundTripP95Ms=times[int(len(times)*.95)],roundTripMaxMs=max(times),syntheticInjectionToPauseMs=pauses)
    (OUT/'browser.json').write_text(json.dumps({'uploads':len(uploads),'sizes':[len(x) for x in uploads],'initialMicCalls':micCalls,'performance':perf,'headful':bool(os.environ.get('JARVIS_HEADFUL')),'errors':errors,'realONNX':True,'realWorklet':True,'physicalMic':False,'AECtested':False,'cases':['seeded broadband noise + knocks + tone no interruption while playing','quiet synthetic speech residual rejected; NOT acoustic AEC','autoTTS checkbox off','legacy snapshot no UI or physical WebSpeech start','double barge-in','native mute closes tracks and discards speech','explicit unmute reacquires once','silence no auto-loop','stale STT','response deadline','late permission','denial','missing worker','real PHP 401','sidebar logout','mobile controls'],'backend':'MC/model/STT/TTS fixtures, real PHP auth form and gate'},indent=2))
    self.assertEqual(errors,[]);browser.close()
  except Exception:
   try:
    print('FAILURE UI',page.locator('#jarvis-chat-status').inner_text(),page.locator('#jarvis-chat-mic').inner_text(),page.locator('#jarvis-chat-continuous').inner_text())
    print('FAILURE EVENTS',page.evaluate('window.callTrace'))
   except Exception:pass
   raise
  finally:Access.tearDownClass()
if __name__=='__main__':unittest.main(verbosity=2)
