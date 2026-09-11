"""Private voice-config rollback only; model files stay private. Check by default."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];m=json.loads((ROOT/'docs/evidence/call/female-live.json').read_text());apply=sys.argv[1:]==['--apply'];assert sys.argv[1:] in [[],['--check'],['--apply']]
code='''from pathlib import Path
import hashlib,json,os,shutil
m=MANIFEST
apply=APPLY
p=Path('/etc/jarvis-chat/config.php');old=Path(m['rollbackDir'])/'config.php'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert str(old).startswith('/root/mia-voice-rollback-')
assert sha(p)==m['configAfterSHA256'] and sha(old)==m['configBeforeSHA256'],'config drift'
if apply:
 st=p.stat();tmp=p.with_suffix('.mia-rollback');shutil.copyfile(old,tmp);os.chmod(tmp,st.st_mode&0o777);os.chown(tmp,st.st_uid,st.st_gid);os.replace(tmp,p);assert sha(p)==m['configBeforeSHA256']
print(json.dumps({'mode':'applied' if apply else 'check-only','privateConfig':True,'modelsRemoved':False}))
'''.replace('MANIFEST',repr(m)).replace('APPLY',repr(apply))
r=subprocess.run(['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','StrictHostKeyChecking=yes','root@178.104.253.211','python3 -'],input=code,text=True,capture_output=True,check=True);print(r.stdout)
if not apply:(ROOT/'docs/evidence/call/voice-rollback-check.json').write_text(r.stdout)
