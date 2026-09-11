"""Sequential integration release checks. No real owner login/microphone/business mutations."""
import subprocess,json,time,hashlib,shutil,datetime,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/mia';OUT.mkdir(parents=True,exist_ok=True)
QA_PYTHON=os.environ.get('MIA_QA_PYTHON','/home/ddr/mia-qa-venv/bin/python')
ready=subprocess.run([QA_PYTHON,'-c','import av,numpy,sys,json;print(json.dumps({"python":sys.version,"executable":sys.executable,"av":av.__version__,"numpy":numpy.__version__}))'],text=True,capture_output=True,check=True)
(OUT/'qa-environment.json').write_text(ready.stdout)
commands=[['python3','tests/mia_branding_test.py'],['node','--test','tests/mia_reactor.cjs'],['xvfb-run','-a','python3','tests/mia_reactor_test.py','Reactor'],['python3','tests/run_call.py'],['python3','tests/chat_frontend_test.py'],['python3','tests/chat_backend_test.py'],[QA_PYTHON,'tests/stt_worker_test.py'],['python3','tests/executor_minimize.py'],['node','--check','reactor/reactor.js']]
files=['index.html','login.html','chat/chat.js','chat/chat.css','reactor/reactor.js','server/gate.php','api/chat.php','integration.js','fire/shaders.js','chat/voice/core.mjs']
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
startHashes={p:sha(p) for p in files};results=[]
for i,c in enumerate(commands):
 start=time.monotonic();r=subprocess.run(c,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=700)
 (OUT/f'regression-{i}.txt').write_text(r.stdout);results.append({'command':c,'exit_code':r.returncode,'seconds':time.monotonic()-start,'log':f'regression-{i}.txt'});print('PASS' if r.returncode==0 else 'FAIL',c,flush=True)
 if c[-1]=='tests/run_call.py':shutil.copytree(ROOT/'docs/evidence/call',OUT/'call-regression',dirs_exist_ok=True)
 if r.returncode:print(r.stdout,flush=True)
endHashes={p:sha(p) for p in files};assert endHashes==startHashes,'Source changed during verification'
(OUT/'regressions.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':results,'hashes':endHashes,'sourceStableDuringRun':True},indent=2))
raise SystemExit(any(t['exit_code'] for t in results))
