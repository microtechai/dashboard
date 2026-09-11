"""Authorized server-only female voice activation. No credentials returned or public audio."""
from pathlib import Path
import json,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/call'
SSH=['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','StrictHostKeyChecking=yes','root@178.104.253.211']
expected=hashlib.sha256((ROOT/'api/chat.php').read_bytes()).hexdigest()
code=r'''
from pathlib import Path
import os,subprocess,json,hashlib,shutil,datetime,grp,time,wave,tempfile
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('/var/www/dashboard/api/chat.php')==EXPECTED,'API not deployed'
cfg=Path('/etc/jarvis-chat/config.php');before='917abbd58e629ee628e3758cb47b8c239e64c32360e76e8ddc6bb944751d2b8b'
assert sha(cfg)==before,'private config drift'
source=Path('/opt/jarvis-tts/models/candidate-mia-sharvard-female-qa');dest=Path('/opt/jarvis-tts/models/mia-sharvard');assert not dest.exists()
models={'es_ES-sharvard-medium.onnx':'40febfb1679c69a4505ff311dc136e121e3419a13a290ef264fdf43ddedd0fb1','es_ES-sharvard-medium.onnx.json':'7438c9b699c72b0c3388dae1b68d3f364dc66a2150fe554a1c11f03372957b2c'}
for p,h in models.items():assert sha(source/p)==h
assert json.loads((source/'es_ES-sharvard-medium.onnx.json').read_text())['speaker_id_map']=={'M':0,'F':1}
gid=grp.getgrnam('www-data').gr_gid;dest.mkdir(mode=0o750);os.chown(dest,0,gid)
for p,h in models.items():shutil.copyfile(source/p,dest/p);os.chmod(dest/p,0o640);os.chown(dest/p,0,gid);assert sha(dest/p)==h
backup=Path('/root/mia-voice-rollback-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700);shutil.copy2(cfg,backup/'config.php');os.chmod(backup/'config.php',0o600)
model=str(dest/'es_ES-sharvard-medium.onnx');candidate=str(backup/'candidate.php')
php='$c=require "/etc/jarvis-chat/config.php";$c["piper_model"]='+json.dumps(model)+';$c["piper_speaker"]=1;file_put_contents('+json.dumps(candidate)+',"<?php\\nreturn ".var_export($c,true).";\\n");'
# Actual newline, not literal backslash-n in generated PHP.
php=php.replace('\\\\n','\\n')
subprocess.run(['php','-r',php],check=True);subprocess.run(['php','-l',candidate],check=True,capture_output=True)
assert sha(cfg)==before
st=cfg.stat();tmp=cfg.with_suffix('.mia-tmp');shutil.copyfile(candidate,tmp);os.chmod(tmp,st.st_mode&0o777);os.chown(tmp,st.st_uid,st.st_gid);os.replace(tmp,cfg)
try:
 # Read only voice fields from live config AS www-data; never export auth fields.
 select='$c=require "/etc/jarvis-chat/config.php";echo json_encode(array_intersect_key($c,array_flip(["piper_python","piper_model","piper_speaker"])));'
 live=json.loads(subprocess.check_output(['runuser','-u','www-data','--','php','-r',select]));assert live['piper_speaker']==1 and live['piper_model']==model
 results=[]
 for text in ['Hola, soy MIA, tu asistente de Microtech AI. Estoy escuchando. Puedes interrumpirme cuando quieras.','Son las 10 y 25. Tienes 3 mensajes y una reunión a las 12.']:
  fd,path=tempfile.mkstemp(suffix='.wav',prefix='mia-live-');os.close(fd);os.chown(path,33,gid)
  argv=['/usr/bin/taskset','-c','0',live['piper_python'],'-m','piper','--model',live['piper_model'],'--speaker',str(live['piper_speaker']),'--output_file',path]
  t=time.perf_counter();p=subprocess.run(['runuser','-u','www-data','--','env','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','MKL_NUM_THREADS=1',*argv],input=text+'\n',text=True,capture_output=True,timeout=30);elapsed=time.perf_counter()-t;assert p.returncode==0,p.stderr
  with wave.open(path) as w:info={'channels':w.getnchannels(),'rate':w.getframerate(),'secondsAudio':w.getnframes()/w.getframerate()}
  assert info['rate']==22050 and info['secondsAudio']>1
  results.append({'text':text,'argv':argv,'runAs':'www-data','secondsCLI':elapsed,'wav':info,'sha256':sha(path),'exit_code':p.returncode});Path(path).unlink()
except Exception:
 tmp=cfg.with_suffix('.mia-revert');shutil.copyfile(backup/'config.php',tmp);os.chmod(tmp,st.st_mode&0o777);os.chown(tmp,st.st_uid,st.st_gid);os.replace(tmp,cfg);raise
result={'scope':'real CPU0 CLI as www-data from updated live private config; not public authenticated API or TTFA/acoustic acceptance','model':model,'speaker':1,'speakerMap':{'M':0,'F':1},'models':models,'configBeforeSHA256':before,'configAfterSHA256':sha(cfg),'rollbackDir':str(backup),'measurements':results,'publicAudio':False}
(backup/'manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
'''.replace('EXPECTED',repr(expected))
r=subprocess.run(SSH+['python3 -'],input=code,text=True,capture_output=True,timeout=100)
if r.returncode:print(r.stderr);raise SystemExit(r.returncode)
result=json.loads(r.stdout);(OUT/'female-live.json').write_text(json.dumps(result,indent=2));print(r.stdout)
