"""Call UI component: isolated API fixture, no real credentials/microphone."""
import unittest
from chat_frontend_test import ChatFrontend
class CallFrontend(ChatFrontend):
 def test_incremental_speech_and_mute_keep_model_separate(self):
  self.page.route('**/chat/voice/session.mjs',lambda r:r.fulfill(content_type='text/javascript',body='''export class ContinuousVoice { constructor(o){Object.assign(this,o);window.fixtureVoice=this;this.active=false;} start(){this.active=true;this.onMic('active');} shutdown(){this.active=false;this.onMic('off');} }'''))
  self.login()
  self.page.route('**/api/chat.php?action=transcribe',lambda r:r.fulfill(json={'text':'Pregunta fixture'}))
  tts=[]
  def voice(r):
   import json
   tts.append(json.loads(r.request.post_data)['text'])
   from chat_frontend_test import ROOT
   r.fulfill(content_type='audio/wav',body=(ROOT/'tests/fixtures/voice-check.wav').read_bytes())
  self.page.route('**/api/chat.php?action=tts',voice)
  self.page.evaluate('''()=>{const real=fetch;window.fetch=(u,o)=>String(u).includes('action=message')?Promise.resolve(new Response(new ReadableStream({start(c){window.modelSignal=o.signal;window.emit=(text,type='delta')=>c.enqueue(new TextEncoder().encode('event: '+type+'\\ndata: '+JSON.stringify({text})+'\\n\\n'));window.endModel=()=>{emit('## 🟦 Primera frase. Segunda frase.','done');c.close();};}}),{headers:{'Content-Type':'text/event-stream'}})):real(u,o);window.played=[];const NativeAudio=Audio;window.Audio=function(...args){const a=new NativeAudio(...args);a.muted=true;played.push(a);return a;};}''')
  self.page.locator('#jarvis-chat-continuous').click()
  self.assertFalse(self.page.locator('#jarvis-chat-autoread').is_checked())
  self.page.locator('#jarvis-chat-input').fill('Texto durante llamada también habla')
  self.page.locator('#jarvis-chat-input').press('Enter')
  self.page.wait_for_function('window.emit!==undefined')
  self.page.evaluate("window.streamStart=performance.now();emit('## 🟦 Primera frase. Segunda')")
  self.page.wait_for_function('played.some(a=>!a.paused)',timeout=5000)
  first_audio=self.page.evaluate('performance.now()-streamStart')
  self.assertEqual(tts,['Primera frase.'])
  self.assertFalse(self.page.evaluate('modelSignal.aborted'))
  self.page.locator('#jarvis-chat-mute').click()
  self.assertFalse(self.page.evaluate('fixtureVoice.active'))
  self.assertEqual(self.page.locator('#jarvis-chat-continuous').inner_text(),'Colgar')
  self.assertIn('silenciado',self.page.locator('#jarvis-chat-mic').inner_text().lower())
  self.assertFalse(self.page.evaluate('modelSignal.aborted'))
  self.page.evaluate("emit(' frase.');endModel()")
  self.page.locator('.jarvis-chat-read').wait_for()
  end_sse=self.page.evaluate('performance.now()-streamStart')
  from chat_frontend_test import ROOT
  import json
  (ROOT/'docs/evidence/call/stream-timing.json').write_text(json.dumps({'scope':'controlled local SSE with real muted HTMLAudio/WebAudio, not production E2E','firstAudioObservedMs':first_audio,'endSSEObservedMs':end_sse,'beforeEnd':first_audio<end_sse,'autoTTSCheckbox':False},indent=2))
  self.assertLess(first_audio,end_sse)
  self.page.locator('#jarvis-chat-mute').click()
  self.assertTrue(self.page.evaluate('fixtureVoice.active'))
  self.page.evaluate('fixtureVoice.onStart();fixtureVoice.onStart()')
  self.assertTrue(self.page.evaluate('played.every(a=>a.paused)'))
  self.assertTrue(self.page.evaluate('fixtureVoice.active'))
  self.page.locator('#jarvis-chat-continuous').click()
  self.assertFalse(self.page.evaluate('fixtureVoice.active'))
 def test_long_read_is_bounded_and_never_reads_labels(self):
  import json
  text='## 🟦 Estado. '+('Una frase completa. '*400)
  self.history=[{'role':'assistant','content':text}]
  self.login()
  self.page.evaluate('''()=>{window.sent=[];const real=fetch;window.fetch=(u,o)=>{if(!String(u).includes('action=tts'))return real(u,o);sent.push(JSON.parse(o.body).text);return Promise.resolve(new Response('fixture',{headers:{'Content-Type':'audio/wav'}}));};window.AudioContext=undefined;window.webkitAudioContext=undefined;window.Audio=class{play(){this.paused=false;setTimeout(()=>{this.paused=true;this.onended?.();},20);return Promise.resolve();}pause(){this.paused=true;}removeAttribute(){}load(){}};}''')
  self.page.locator('.jarvis-chat-read').click()
  self.page.wait_for_function("document.querySelector('.jarvis-speech-limit')!==null",timeout=2000)
  self.page.wait_for_function("document.querySelector('#jarvis-chat-status').textContent.includes('Lectura completada')")
  sent=self.page.evaluate('sent')
  self.assertLessEqual(len(sent),3);self.assertTrue(all(len(p)<=1000 for p in sent))
  self.assertEqual(sent[0],'Estado.')
  self.assertNotIn('Leer',' '.join(sent));self.assertNotIn('JARVIS',' '.join(sent));self.assertNotIn('🟦',' '.join(sent))
  self.assertEqual(self.page.locator('.jarvis-chat-message > p').first.inner_text(),text)
 def test_muting_pending_stt_drops_it_without_false_listening_status(self):
  self.page.route('**/chat/voice/session.mjs',lambda r:r.fulfill(content_type='text/javascript',body='''export class ContinuousVoice {constructor(o){Object.assign(this,o);window.fixtureVoice=this;}start(){this.active=true;this.onMic('active');}shutdown(){this.active=false;this.onMic('off');}}'''))
  self.login()
  self.page.evaluate('''()=>{window.states=[];addEventListener('jarvis-chat-state',e=>states.push(e.detail.state));const real=fetch;window.fetch=(u,o)=>String(u).includes('action=transcribe')?new Promise(r=>{window.sttSignal=o.signal;window.releaseSTT=()=>r(new Response(JSON.stringify({text:'MUTED STALE'})));}):real(u,o);}''')
  self.page.locator('#jarvis-chat-continuous').click()
  self.page.evaluate("void fixtureVoice.onEnd({wav:new ArrayBuffer(44),reason:'silence'})")
  self.page.wait_for_function('window.releaseSTT!==undefined')
  self.page.evaluate('fixtureVoice.onLevel(.2)')
  self.assertEqual(self.page.evaluate('states.at(-1)'),'transcribing')
  self.page.locator('#jarvis-chat-mute').click();self.assertTrue(self.page.evaluate('sttSignal.aborted'))
  self.page.evaluate('releaseSTT()');self.page.wait_for_timeout(100)
  self.assertFalse(any(c[0]=='message' for c in self.calls))
  self.assertNotIn('MUTED STALE',self.page.locator('#jarvis-chat-history').inner_text())
 def test_primary_call_and_explicit_fallback(self):
  self.login()
  self.assertEqual(self.page.locator('#jarvis-chat-continuous').inner_text(),'Llamar a MIA')
  self.assertEqual(self.page.locator('#jarvis-chat-mute').inner_text(),'Silenciar micrófono')
  self.assertIn('manual',self.page.locator('#jarvis-chat-talk').inner_text().lower())
if __name__=='__main__':unittest.main(verbosity=2)
