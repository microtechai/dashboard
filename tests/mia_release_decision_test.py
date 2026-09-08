"""Isolated release-safety fixture: a permissive green ledger cannot override NO-GO."""
import json, shutil, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReleaseDecision(unittest.TestCase):
 def test_no_go_blocks_before_any_remote_operation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'server').mkdir();out=root/'docs/evidence/mia';out.mkdir(parents=True)
   shutil.copyfile(ROOT/'server/deploy_mia.py',root/'server/deploy_mia.py')
   (out/'regressions.json').write_text(json.dumps({'sourceStableDuringRun':True,'tests':[{'exit_code':0}],'hashes':{}}))
   (out/'architectural-cycle.json').write_text(json.dumps({'decision':'NO-GO'}))
   result=subprocess.run(['python3',str(root/'server/deploy_mia.py'),'--deploy'],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0)
   self.assertIn('Release decision is NO-GO',result.stderr)
 def test_preview_requires_explicit_flag_and_acknowledges_pending(self):
  result=subprocess.run(['python3',str(ROOT/'server/deploy_mia.py'),'--check-local'],capture_output=True,text=True)
  self.assertNotEqual(result.returncode,0)
  self.assertIn('Release decision is NO-GO',result.stderr)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'server').mkdir();out=root/'docs/evidence/mia';out.mkdir(parents=True)
   shutil.copyfile(ROOT/'server/deploy_mia.py',root/'server/deploy_mia.py')
   for name in ['regressions.json','architectural-cycle.json']:
    shutil.copyfile(ROOT/'docs/evidence/mia'/name,out/name)
   ledger=json.loads((out/'regressions.json').read_text())
   for name in ledger['hashes']:
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
   public=json.loads((ROOT/'docs/evidence/mia/operator-preview.json').read_text())
   # Isolated fixture only; never rewrite actual candidate or release evidence.
   (out/'candidate-manifest.json').write_text(json.dumps({'candidateHashes':public['candidateHashes'],'finalQA':{'navigation':24,'nodes':17}}))
   result=subprocess.run(['python3',str(root/'server/deploy_mia.py'),'--operator-preview','--check-local'],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertIn('hardware performance pending; technical decision remains NO-GO',result.stdout)
 def test_preview_cannot_override_failed_functional_checks(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'server').mkdir();out=root/'docs/evidence/mia';out.mkdir(parents=True)
   shutil.copyfile(ROOT/'server/deploy_mia.py',root/'server/deploy_mia.py')
   (out/'regressions.json').write_text(json.dumps({'sourceStableDuringRun':True,'tests':[{'exit_code':1}],'hashes':{}}))
   result=subprocess.run(['python3',str(root/'server/deploy_mia.py'),'--operator-preview','--deploy'],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0)
   self.assertNotIn('OPERATOR PREVIEW authorized',result.stdout)
if __name__=='__main__':unittest.main(verbosity=2)
