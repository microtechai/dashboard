"""Selective reversal. Default check only. --apply requires deliberate operator authorization."""
import json,subprocess,sys
from pathlib import Path
m=json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/mia/deployment-manifest.json').read_text())
script="""import pathlib,json,hashlib,shutil,os,sys
m=json.loads(sys.stdin.readline());apply=sys.stdin.readline().strip()=='apply'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
for i in m['items']:
 assert sha(pathlib.Path(i['path']))==i['after'], 'Live drift blocks rollback'
 if i['before'] is not None:assert sha(pathlib.Path(m['backup'])/i['upload'])==i['before'],'Backup mismatch'
if apply:
 for i in reversed(m['items']):
  p=pathlib.Path(i['path'])
  if i['before'] is None:p.unlink()
  else:
   st=p.stat();tmp=p.parent/('.mia-rollback-'+p.name);shutil.copy2(pathlib.Path(m['backup'])/i['upload'],tmp);os.chown(tmp,st.st_uid,st.st_gid);os.replace(tmp,p)
  assert sha(p)==i['before']
print('PASS selective rollback '+('APPLIED' if apply else 'CHECK ONLY'))
"""
import shlex
r=subprocess.run(['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','root@178.104.253.211','python3 -c '+shlex.quote(script)],input=json.dumps(m)+'\n'+('apply' if '--apply' in sys.argv else 'check')+'\n',text=True,capture_output=True,check=True)
print(r.stdout)
