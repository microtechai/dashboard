"""One bounded real CPU Whisper invocation per generated WAV, via existing SSH/venv."""
from pathlib import Path
import subprocess,time,json,hashlib
ROOT=Path('/home/ddr/jarvis-phase2-20260908');SSH=['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','StrictHostKeyChecking=yes','root@178.104.253.211'];results=[]
for file in [Path('/home/ddr/jarvis-bargein-spike/captured-piper.wav'),ROOT/'docs/evidence/phase7/captured-browser.wav']:
 target='/tmp/jarvis-phase7-fixture.wav'
 subprocess.run(['scp','-i','/home/ddr/.ssh/hetzner-admin',str(file),'root@178.104.253.211:'+target],check=True,capture_output=True)
 t=time.monotonic()
 r=subprocess.run(SSH+['taskset -c 1 /opt/jarvis-stt/venv/bin/python /opt/jarvis-stt/stt_worker.py '+target],capture_output=True,text=True,timeout=50)
 results.append({'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size,'exit_code':r.returncode,'seconds':time.monotonic()-t,'output':r.stdout,'stderr':r.stderr,'realWhisper':True,'authenticatedHTTP':False,'cpu':1})
 subprocess.run(SSH+['rm -- '+target],check=True,capture_output=True)
 assert r.returncode==0
(ROOT/'docs/evidence/phase7/real-stt.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
