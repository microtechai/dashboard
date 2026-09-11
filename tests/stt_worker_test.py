"""Real decode boundary tests; inference tested separately on deployment CPU."""
import unittest, importlib.util, pathlib, tempfile, wave
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Worker(unittest.TestCase):
 def test_decode_bounded(self):
  path=ROOT/'server/stt_worker.py'
  self.assertTrue(path.exists(), 'STT worker missing')
  spec=importlib.util.spec_from_file_location('stt',path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'audio.wav'
   for seconds in [1,20,21]:
    with wave.open(str(p),'wb') as w: w.setparams((1,2,16000,0,'NONE','')); w.writeframes(b'\0'*(16000*2*seconds))
    if seconds>20:
     with self.assertRaises(ValueError): m.decode_bounded(str(p))
    else: self.assertEqual(len(m.decode_bounded(str(p))),seconds*16000)
if __name__=='__main__': unittest.main()
