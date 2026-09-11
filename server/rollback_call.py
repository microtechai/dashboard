"""Selective call rollback, --check by default. --apply explicitly restores only manifest files."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'docs/evidence/call/deployment-manifest.json').read_text())
apply=sys.argv[1:]==['--apply'];assert not sys.argv[1:] or sys.argv[1:] in [['--check'],['--apply']]
code='''from pathlib import Path
import hashlib,json,os,shutil
m=MANIFEST
apply=APPLY
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
backup=Path(m['rollback_dir'])
assert str(backup).startswith('/root/jarvis-call-rollback-')
for r in m['files']:
 p=Path(r['path']);assert str(p).startswith('/var/www/dashboard/chat/') or str(p) in ['/opt/jarvis-access/gate.php','/var/www/dashboard/api/chat.php']
 assert not p.is_symlink() and sha(p)==r['after'],'LIVE DRIFT '+str(p)
 if r['before'] is not None:assert sha(backup/'before'/r['source'])==r['before']
if apply:
 for r in reversed(m['files']):
  p=Path(r['path'])
  if r['before'] is None:p.unlink()
  else:
   tmp=p.with_name(p.name+'.call-restore');shutil.copy2(backup/'before'/r['source'],tmp);os.chmod(tmp,r['mode']);os.chown(tmp,r['uid'],r['gid']);os.replace(tmp,p)
 for r in m['files']:assert (sha(r['path']) if Path(r['path']).exists() else None)==r['before']
for p,h in m['preserved'].items():assert sha('/var/www/dashboard/'+p)==h
print(json.dumps({'mode':'applied' if apply else 'check-only','files':len(m['files']),'rollback_dir':str(backup),'preserved':True}))
'''.replace('MANIFEST',repr(manifest)).replace('APPLY',repr(apply))
r=subprocess.run(['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','StrictHostKeyChecking=yes','root@178.104.253.211','python3 -'],input=code,text=True,capture_output=True,check=True)
print(r.stdout)
if not apply:(ROOT/'docs/evidence/call/rollback-check.json').write_text(r.stdout)
