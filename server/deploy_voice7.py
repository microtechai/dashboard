"""Phase7 only: authenticated assets + chat + gate allowlist. No nginx/CF/services/index/fire changes.
Run AFTER tests/run_phase7.py. Remote hashes abort on drift; selective rollback is outside webroot.
"""
from pathlib import Path
import hashlib,json,subprocess,tarfile,tempfile,os
ROOT=Path(__file__).resolve().parents[1]
SSH=['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','StrictHostKeyChecking=yes','root@178.104.253.211']
checks=json.loads((ROOT/'docs/evidence/phase7/tests.json').read_text())
assert all(t['exit_code']==0 for t in checks['tests']),'Tests not green'
for name,digest in checks['verifiedFiles'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'Changed since tests: '+name
baseline={'chat/chat.js':'1d9d633d6e6794948cc2cd7ba4989c1790d072559a2dc953f9d351520a5828ef','chat/chat.css':'f94afcbce026943e635436ce9f039ca21a854951f413ddced3827e77c4ef2df6','server/gate.php':'34c0230747fc4d36982c42d5695f1223ff95c6f230cae48712793dae189d8088'}
rows=[{'source':p,'path':'/opt/jarvis-access/gate.php' if p=='server/gate.php' else '/var/www/dashboard/'+p,'before':baseline.get(p),'after':h} for p,h in checks['verifiedFiles'].items()]
# New assets first, gate next, chat entry last. No partially published entrypoint.
rows.sort(key=lambda r:0 if r['source'].startswith('chat/voice/') else 1 if r['source']=='server/gate.php' else 2 if r['source'].endswith('.css') else 3)
with tempfile.NamedTemporaryFile(suffix='.tar') as bundle:
 with tarfile.open(bundle.name,'w') as tar:
  for r in rows:tar.add(ROOT/r['source'],arcname=r['source'],recursive=False)
 remote_bundle='/root/jarvis-phase7-candidate-'+hashlib.sha256(Path(bundle.name).read_bytes()).hexdigest()[:16]+'.tar'
 subprocess.run(['scp','-i','/home/ddr/.ssh/hetzner-admin','-o','StrictHostKeyChecking=yes',bundle.name,'root@178.104.253.211:'+remote_bundle],check=True)
 code='''from pathlib import Path
import json,hashlib,tarfile,shutil,os,datetime,subprocess,pwd
rows=ROWS
bundle=Path(BUNDLE)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name,digest in PRESERVED.items():assert sha('/var/www/dashboard/'+name)==digest,'UNCHANGED FILE DRIFT '+name
for r in rows:
 p=Path(r['path']);assert not p.is_symlink()
 assert (sha(p) if p.exists() else None)==r['before'],'DRIFT '+str(p)
backup=Path('/root/jarvis-voice7-rollback-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
with tarfile.open(bundle) as tar:
 for r in rows:
  p=Path(r['path']);data=tar.extractfile(r['source']).read();assert hashlib.sha256(data).hexdigest()==r['after']
  candidate=backup/'candidate'/r['source'];candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_bytes(data)
  if p.exists():
   st=p.stat();r.update(uid=st.st_uid,gid=st.st_gid,mode=st.st_mode&0o777)
   old=backup/'before'/r['source'];old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,old)
  else:r.update(uid=0,gid=0,mode=0o644)
  if p.suffix=='.php':subprocess.run(['php','-l',str(candidate)],check=True,capture_output=True)
manifest={'rollback_dir':str(backup),'files':rows,'preserved':PRESERVED}
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
changed=[]
try:
 for r in rows:
  p=Path(r['path']);p.parent.mkdir(parents=True,exist_ok=True)
  tmp=p.with_name(p.name+'.phase7-tmp');tmp.write_bytes((backup/'candidate'/r['source']).read_bytes());os.chmod(tmp,r['mode']);os.chown(tmp,r['uid'],r['gid']);os.replace(tmp,p);changed.append(r)
 for r in rows:assert sha(r['path'])==r['after']
except Exception:
 for r in reversed(changed):
  p=Path(r['path'])
  if r['before'] is None:p.unlink()
  else:
   tmp=p.with_name(p.name+'.phase7-revert');shutil.copy2(backup/'before'/r['source'],tmp);os.chown(tmp,r['uid'],r['gid']);os.replace(tmp,p)
 raise
finally:bundle.unlink(missing_ok=True)
print(json.dumps(manifest,indent=2))
'''.replace('ROWS',repr(rows)).replace('BUNDLE',repr(remote_bundle)).replace('PRESERVED',repr(checks['preserved']))
 result=subprocess.run(SSH+['python3 -'],input=code,text=True,capture_output=True,timeout=90)
 if result.returncode:print(result.stdout,result.stderr);raise SystemExit(result.returncode)
 manifest=json.loads(result.stdout);(ROOT/'docs/evidence/phase7/deployment-manifest.json').write_text(json.dumps(manifest,indent=2));print(result.stdout)
