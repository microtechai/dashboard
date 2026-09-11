"""Real PHP process argv with silent Piper fixture; not synthesis evidence."""
import json,unittest
from chat_backend_test import Backend,RUN
class FemaleSpeaker(Backend):
 def test_private_speaker_exact_argv_and_invalid_config(self):
  original=(RUN/'config.php').read_text();script=self.piper.read_text()
  try:
   self.piper.write_text('#!/usr/bin/python3\nimport sys,json,wave,pathlib\npathlib.Path('+repr(str(RUN/'argv.json'))+').write_text(json.dumps(sys.argv))\nwith wave.open(sys.argv[-1],"wb") as w:\n w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050);w.writeframes(b"\\0"*440)\n')
   def config(value):
    (RUN/'config.php').write_text('<?php return json_decode('+repr(json.dumps({**self.cfg,'piper_speaker':value,'piper_model':'/private/fixture-sharvard.onnx'}))+',true);')
   config(1);self.login();self.assertEqual(self.req('tts',{'text':'MIA fixture'})[0],200)
   args=json.loads((RUN/'argv.json').read_text());self.assertIn('--speaker',args);self.assertEqual(args[args.index('--speaker')+1],'1');self.assertEqual(args[args.index('--model')+1],'/private/fixture-sharvard.onnx')
   for bad in ['1','1;touch /tmp/no',-1,1.5,True,1024]:
    config(bad);(RUN/'argv.json').unlink(missing_ok=True)
    self.assertEqual(self.req('tts',{'text':'invalid speaker'})[0],503)
    self.assertFalse((RUN/'argv.json').exists())
  finally:(RUN/'config.php').write_text(original);self.piper.write_text(script)
if __name__=='__main__':unittest.main(verbosity=2)
