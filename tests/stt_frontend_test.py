"""Isolated synthetic media APIs. Never accesses or grants real microphone."""
import unittest
from chat_frontend_test import ChatFrontend
class Voice(ChatFrontend):
 def setup_media(self, mode='ok'):
  self.page.evaluate('''mode => {
   window.micCalls=0; window.stopped=0;
   Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>{micCalls++; if(mode==='denied') throw new DOMException('denied','NotAllowedError'); if(mode==='pending') await new Promise(r=>window.resolveMic=r); return {getTracks:()=>[{stop:()=>stopped++}]};}}});
   window.MediaRecorder=class {static isTypeSupported(t){return t.includes('webm')} constructor(){this.state='inactive';this.mimeType='audio/webm';} start(){this.state='recording'} stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['fixture'],{type:'audio/webm'})});setTimeout(()=>this.onstop?.(),0)} };
   window.AudioContext=undefined; window.webkitAudioContext=undefined;
  }''',mode)
 def test_mic_explicit_denial_and_late_permission(self):
  self.login(); self.setup_media('denied')
  self.assertEqual(self.page.locator('#jarvis-chat-talk').count(),1)
  self.assertEqual(self.page.evaluate('micCalls'),0)
  self.page.locator('#jarvis-chat-talk').click(); self.page.wait_for_timeout(100)
  self.assertIn('micrófono',self.page.locator('#jarvis-chat-status').inner_text())
  self.setup_media('pending'); self.page.locator('#jarvis-chat-talk').click(); self.page.locator('#jarvis-chat-stop').click()
  self.page.evaluate('resolveMic()'); self.page.wait_for_timeout(100)
  self.assertEqual(self.page.evaluate('stopped'),1)
  self.assertFalse(any(c[0]=='transcribe' for c in self.calls))
 def test_voice_only_autoread_and_stop_tracks(self):
  self.login(); self.setup_media()
  self.page.route('**/api/chat.php?action=transcribe', lambda r:r.fulfill(json={'text':'<img src=x onerror=alert(1)> voz'}))
  self.options(); self.page.locator('#jarvis-chat-autoread').check(); self.page.locator('#jarvis-chat-options > summary').click()
  self.send('texto'); self.page.locator('.jarvis-chat-read').wait_for(); self.page.wait_for_timeout(100)
  self.assertFalse(any(c[0]=='tts' for c in self.calls))
  self.page.locator('#jarvis-chat-talk').click(); self.page.locator('#jarvis-chat-talk').click()
  self.page.wait_for_timeout(400)
  self.assertEqual(self.page.evaluate('stopped'),1)
  self.assertTrue(any(c[0]=='tts' for c in self.calls))
  self.assertEqual(self.page.locator('#jarvis-chat-history img').count(),0)
 def test_recording_limit_cancel_and_stale_transcription(self):
  self.login(); self.setup_media()
  self.page.evaluate('''() => {const orig=setTimeout; window.setTimeout=(f,ms,...args)=>{if(ms===20000){window.limitRecording=f; return 999;}return orig(f,ms,...args)};
   const real=fetch; window.fetch=(u,o)=>u.includes('action=transcribe')?new Promise(r=>{window.transcribeSignal=o.signal;window.lateTranscript=()=>r(new Response(JSON.stringify({text:'STALE VOICE'}),{headers:{'Content-Type':'application/json'}}))}):real(u,o);
  }''')
  self.page.locator('#jarvis-chat-talk').click(); self.page.evaluate('limitRecording()'); self.page.wait_for_timeout(100)
  self.assertEqual(self.page.evaluate('stopped'),1)
  self.page.locator('#jarvis-chat-stop').click(); self.assertTrue(self.page.evaluate('transcribeSignal.aborted'))
  self.page.evaluate('lateTranscript()'); self.page.wait_for_timeout(100)
  self.assertNotIn('STALE VOICE',self.page.locator('#jarvis-chat-history').inner_text())
  self.assertFalse(any(c[0]=='message' for c in self.calls))
 def test_stop_recording_does_not_upload(self):
  self.login(); self.setup_media(); self.page.locator('#jarvis-chat-talk').click(); self.page.locator('#jarvis-chat-stop').click(); self.page.wait_for_timeout(100)
  self.assertEqual(self.page.evaluate('stopped'),1)
  self.assertFalse(any(c[0]=='transcribe' for c in self.calls))
 def test_native_recorder_real_rms_no_physical_mic(self):
  self.login()
  self.page.evaluate('''() => {
   window.states=[];addEventListener('jarvis-chat-state',e=>states.push(e.detail));
   window.testContext=new AudioContext();testContext.resume();window.osc=testContext.createOscillator();osc.frequency.value=440;window.dest=testContext.createMediaStreamDestination();osc.connect(dest);osc.start();
   Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia:async()=>dest.stream}});
  }''')
  captured=[]
  def transcribe(r):
   captured.append({'mime':r.request.headers['content-type'],'csrf':r.request.headers.get('x-csrf-token'),'bytes':len(r.request.post_data_buffer),'track':self.page.evaluate('dest.stream.getTracks()[0].readyState')})
   r.fulfill(json={'text':'Prueba de audio nativo'})
  self.page.route('**/api/chat.php?action=transcribe',transcribe)
  self.page.locator('#jarvis-chat-talk').click()
  self.page.wait_for_function("states.some(x=>x.state==='listening'&&x.level>0.01)")
  self.page.wait_for_timeout(400); self.page.locator('#jarvis-chat-talk').click(); self.page.locator('.jarvis-chat-read').wait_for()
  self.assertEqual(captured[0]['track'],'ended'); self.assertEqual(captured[0]['csrf'],'rotated-fixture'); self.assertIn('multipart/form-data',captured[0]['mime']); self.assertGreater(captured[0]['bytes'],1000)
  self.assertIn('transcribing',self.page.evaluate('states.map(x=>x.state)'))
  self.page.evaluate('osc.stop();testContext.close()')
if __name__=='__main__': unittest.main()
