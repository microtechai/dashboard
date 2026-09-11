import unittest,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Release(unittest.TestCase):
 def test_preview_requires_green_frozen_evidence_and_explicit_flag(self):
  spec=importlib.util.spec_from_file_location('deploy_redesign',ROOT/'server/deploy_redesign.py')
  self.assertTrue((ROOT/'server/deploy_redesign.py').exists(),'dedicated six-file guarded release required')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  files={f:'hash' for f in module.FILES}
  report={'sourceStableDuringRun':True,'hashes':files,'tests':[{'exit_code':0}]*16}
  for preview,change in [(False,{}),(True,{'sourceStableDuringRun':False}),(True,{'tests':[{'exit_code':1}]*16}),(True,{'tests':[]})]:
   with self.assertRaises(AssertionError):module.validate_report({**report,**change},files,preview)
  module.validate_report(report,files,True)
  covered={**report,'tests':[{'exit_code':0}]*31,'verificationMode':'full-plus-targeted','productionSourceChangedAfterFullRun':False}
  module.validate_report(covered,files,True)
  with self.assertRaises(AssertionError):module.validate_report({**covered,'productionSourceChangedAfterFullRun':True},files,True)
  with self.assertRaises(AssertionError):module.validate_report(report,{**files,'index.html':'drift'},True)
if __name__=='__main__':unittest.main(verbosity=2)
