"""Isolated HTTP security tests; does not claim real transcription."""
import unittest, http.client, json, sys
from chat_backend_test import Backend, ORIGIN
class STT(Backend):
    def upload(self, extra=None, payload=b'not audio'):
        boundary='jarvis-fixture'
        data=b'--'+boundary.encode()+b'\r\nContent-Disposition: form-data; name="audio"; filename="x.webm"\r\nContent-Type: audio/webm\r\n\r\n'+payload+b'\r\n--'+boundary.encode()+b'--\r\n'
        h={'Cookie':self.cookie,'Origin':ORIGIN,'X-CSRF-Token':self.csrf,'Content-Type':'multipart/form-data; boundary='+boundary}; h.update(extra or {})
        c=http.client.HTTPConnection('127.0.0.1',self.pp,timeout=50); c.request('POST','/?action=transcribe',data,h); r=c.getresponse(); status=r.status; self.last_data=r.read(); c.close(); return status
    def test_transcribe_guards(self):
        self.req()
        self.assertEqual(self.upload(),401)
        self.login()
        self.assertEqual(self.upload({'Origin':'https://evil.test'}),403)
        self.assertEqual(self.upload({'X-CSRF-Token':'wrong'}),403)
        self.assertEqual(self.upload(payload=b'x'*2097153),413)
        self.assertEqual(self.upload(),415)
    @unittest.skipUnless(__import__('os').environ.get('JARVIS_REAL_STT'), 'requires installed production CPU worker, isolated auth fixture')
    def test_real_audio_worker_http_and_cleanup(self):
        import pathlib, time, fcntl, wave, io
        from chat_backend_test import RUN
        self.login()
        lock=open(RUN/'state/transcribe.lock','w'); fcntl.flock(lock,fcntl.LOCK_EX)
        audio=pathlib.Path('/var/lib/jarvis-chat/audio/phase4-native.webm').read_bytes()
        self.assertEqual(self.upload(payload=audio),429); lock.close()
        for name in ['phase3-voice-check.wav','phase4-native.webm']:
            start=time.monotonic(); self.assertEqual(self.upload(payload=pathlib.Path('/var/lib/jarvis-chat/audio',name).read_bytes()),200)
            text=json.loads(self.last_data)['text']; self.assertIn('núcleo azul',text)
            print(json.dumps({'file':name,'seconds':time.monotonic()-start,'text':text},ensure_ascii=False))
            self.assertEqual(list((RUN/'state').glob('stt-*')),[])
        wav=io.BytesIO()
        with wave.open(wav,'wb') as w: w.setparams((1,2,16000,0,'NONE','')); w.writeframes(b'\0'*672000)
        self.assertEqual(self.upload(payload=wav.getvalue()),502)
        self.assertEqual(list((RUN/'state').glob('stt-*')),[])
if __name__=='__main__': unittest.main()
