"""One sequential regression pass; fixed performance record, operator preview only."""
from pathlib import Path
import subprocess,json,hashlib,time,shutil,os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/mia/redesign';OUT.mkdir(parents=True,exist_ok=True)
COMMANDS=[['node','--test','tests/call_speech.test.mjs','tests/mia_speech_entry.test.mjs'],['python3','tests/mia_speech_backend_test.py','EmojiBackend.test_tts_stdin_strips_emoji_without_touching_history'],['xvfb-run','-a','python3','tests/mia_redesign_test.py','Redesign'],['python3','tests/mia_branding_test.py'],['node','--test','tests/mia_reactor.cjs'],['xvfb-run','-a','python3','tests/mia_reactor_test.py','Reactor'],['python3','tests/run_call.py'],['python3','tests/chat_frontend_test.py'],['python3','tests/chat_backend_test.py'],['/home/ddr/mia-qa-venv/bin/python','tests/stt_worker_test.py'],['python3','tests/executor_minimize.py'],['php','-l','api/chat.php'],['php','-l','server/gate.php'],['node','--check','chat/chat.js'],['node','--check','integration.js'],['node','--check','reactor/reactor.js']]
FILES=['index.html','chat/chat.css','chat/chat.js','chat/voice/speech.mjs','integration.js','api/chat.php','reactor/reactor.js','server/gate.php','login.html','chat/voice/core.mjs']
sha=lambda f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
hashes={f:sha(f) for f in FILES};results=[]
for i,c in enumerate(COMMANDS):
 start=time.monotonic();p=subprocess.run(c,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=700)
 log=f'regression-{i}.txt';(OUT/log).write_text(p.stdout);results.append({'command':c,'exit_code':p.returncode,'seconds':time.monotonic()-start,'log':log});print('PASS' if not p.returncode else 'FAIL',c,flush=True)
 if p.returncode:print(p.stdout,flush=True)
 if c[-1]=='tests/run_call.py':shutil.copytree(ROOT/'docs/evidence/call',OUT/'call-regression',dirs_exist_ok=True)
 stable=hashes=={f:sha(f) for f in FILES}
 (OUT/'regressions.json').write_text(json.dumps({'mode':'operator-preview','hardwarePerformance':'pending','sourceStableDuringRun':stable,'hashes':hashes,'tests':results},indent=2))
 assert stable,'Source changed during suite'
raise SystemExit(any(t['exit_code'] for t in results))
