"""Full call verification, deterministic fixtures + native ONNX/audio. No physical mic."""
from pathlib import Path
import subprocess,json,time,hashlib,os,datetime
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/call';OUT.mkdir(parents=True,exist_ok=True)
FILES=['chat/chat.js','chat/chat.css','chat/voice/speech.mjs','chat/voice/capture.js','chat/voice/worker.js','chat/voice/core.mjs','api/chat.php','server/gate.php']
commands=[['node','--test','tests/call_speech.test.mjs',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests').glob('voice_*.test.mjs'))],'tests/core_activity.cjs','tests/stt_core.cjs','tests/fire.test.cjs'],['python3','tests/call_frontend_test.py','CallFrontend'],['python3','tests/stt_frontend_test.py'],['python3','tests/access_gate_test.py'],['python3','tests/access_browser_test.py','BrowserAccess'],['python3','tests/stt_backend_test.py'],['xvfb-run','-a','python3','tests/call_barge_in_test.py','VoiceBargeIn']]
commands += [['python3','tests/call_female_test.py','FemaleSpeaker']]
commands += [['php','-l',f] for f in ['api/chat.php','server/gate.php','server/session.php','server/transcribe.php']]
commands += [['node','--check',f] for f in ['chat/chat.js','chat/voice/speech.mjs','chat/voice/capture.js','chat/voice/worker.js']]
results=[]
for i,c in enumerate(commands):
 t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat();r=subprocess.run(c,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180,env={**os.environ,'JARVIS_HEADFUL':'1'})
 log=f'test-{i}.txt';(OUT/log).write_text(r.stdout);results.append({'command':c,'started':start,'exit_code':r.returncode,'seconds':time.monotonic()-t,'log':log});print('PASS' if r.returncode==0 else 'FAIL',c,flush=True)
 if r.returncode:print(r.stdout)
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
report={'tests':results,'verifiedFiles':{p:sha(p) for p in FILES},'preserved':{p:sha(p) for p in ['index.html','fire/shaders.js']},'baselineCommit':'445ca76f4d25291ebc7efeb6d22582eaf275c398'}
(OUT/'tests.json').write_text(json.dumps(report,indent=2));raise SystemExit(any(r['exit_code'] for r in results))
