"""Reproducible verification; fixture suites never use physical microphone/production credentials."""
from pathlib import Path
import subprocess,json,time,hashlib,os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/phase7';OUT.mkdir(parents=True,exist_ok=True)
commands=[['node','--test',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests').glob('voice_*.test.mjs'))],'tests/core_activity.cjs','tests/stt_core.cjs','tests/fire.test.cjs'],['python3','tests/chat_frontend_test.py'],['python3','tests/stt_frontend_test.py'],['python3','tests/access_gate_test.py'],['python3','tests/access_browser_test.py','BrowserAccess'],['python3','tests/stt_backend_test.py'],['xvfb-run','-a','python3','tests/voice_barge_in_test.py','VoiceBargeIn']]
commands += [['php','-l',f] for f in ['api/chat.php','server/gate.php','server/session.php','server/transcribe.php']]
results=[]
for i,c in enumerate(commands):
 t=time.monotonic();r=subprocess.run(c,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180,env={**os.environ,'JARVIS_HEADFUL':'1'})
 log=f'test-{i}.txt';(OUT/log).write_text(r.stdout);results.append({'command':c,'exit_code':r.returncode,'seconds':time.monotonic()-t,'log':log});print('PASS' if r.returncode==0 else 'FAIL',c,flush=True)
 if r.returncode:print(r.stdout)
files=['chat/chat.js','chat/chat.css','server/gate.php',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'chat/voice').rglob('*')) if p.is_file()]]
report={'tests':results,'verifiedFiles':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},'preserved':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['index.html','fire/shaders.js']}}
(OUT/'tests.json').write_text(json.dumps(report,indent=2));raise SystemExit(any(r['exit_code'] for r in results))
