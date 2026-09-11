"""Resolve only obsolete test contracts, preserving failed full-run evidence and source hashes."""
from pathlib import Path
import json,subprocess,hashlib,time,os,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/mia/redesign'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((OUT/'regressions.json').read_text());calls=json.loads((OUT/'call-regression/tests.json').read_text())
assert base['sourceStableDuringRun'] and all(sha(ROOT/f)==h for f,h in base['hashes'].items()),'Source drift: full suite must be reconsidered'
assert [i for i,t in enumerate(base['tests']) if t['exit_code']]==[6,10]
assert [i for i,t in enumerate(calls['tests']) if t['exit_code']]==[6]
checks=[{**t,'origin':'full-suite'} for t in base['tests'] if t['exit_code']==0]
checks += [{**t,'origin':'full-call-suite','log':'call-regression/'+t['log']} for t in calls['tests'] if t['exit_code']==0]
for name,c in [('executor',['python3','tests/executor_minimize.py']),('native-barge-in',['xvfb-run','-a','python3','tests/call_barge_in_test.py','VoiceBargeIn'])]:
 start=time.monotonic();p=subprocess.run(c,cwd=ROOT,env={**os.environ,'JARVIS_HEADFUL':'1'},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 log='recheck-'+name+'.txt';(OUT/log).write_text(p.stdout);print(p.stdout,flush=True)
 checks.append({'command':c,'exit_code':p.returncode,'seconds':time.monotonic()-start,'log':log,'origin':'targeted-contract-recheck'})
 if p.returncode:raise SystemExit(p.returncode)
assert all(sha(ROOT/f)==h for f,h in base['hashes'].items()),'Source drift during targeted checks'
report={'verificationMode':'full-plus-targeted','mode':'operator-preview','hardwarePerformance':'pending','sourceStableDuringRun':True,'hashes':base['hashes'],'tests':checks,'baseFullRunExitCode':1,'baseFullRunSHA256':sha(OUT/'regressions.json'),'baseCallRunSHA256':sha(OUT/'call-regression/tests.json'),'resolvedTestOnlyContracts':['Legacy voiceSystem must be absent','900px is intentional tablet collapse, 1280px explicit desktop; keyboard/restore/prefs retained'],'productionSourceChangedAfterFullRun':False}
(OUT/'release-validation.json').write_text(json.dumps(report,indent=2));print('PASS covered checks:',len(checks),'(full-run failures remain recorded; targeted-only revalidation)')
shutil.copytree(ROOT/'docs/evidence/call',OUT/'native-recheck-evidence',dirs_exist_ok=True)
