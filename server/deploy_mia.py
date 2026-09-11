"""Selective release or explicitly authorized operator preview; never waive security or source guards."""
from pathlib import Path
import subprocess,json,hashlib,datetime,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/mia'
SSH=['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','root@178.104.253.211']
SCP=['scp','-i','/home/ddr/.ssh/hetzner-admin','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes']
FILES=['reactor/reactor.js','chat/chat.css','chat/chat.js','integration.js','server/gate.php','login.html','index.html']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'regressions.json').read_text());assert r['sourceStableDuringRun'] and all(t['exit_code']==0 for t in r['tests'])
assert all(sha(ROOT/f)==s for f,s in r['hashes'].items()),'Tested source drift'
decision=json.loads((OUT/'architectural-cycle.json').read_text())
preview='--operator-preview' in sys.argv
assert decision['decision']=='PASS' or preview, 'Release decision is NO-GO; a permissive timing baseline cannot authorize publication'
candidate=json.loads((OUT/'candidate-manifest.json').read_text())
assert set(candidate['candidateHashes'])==set(FILES), 'Candidate scope mismatch'
assert all(sha(ROOT/f)==h for f,h in candidate['candidateHashes'].items()), 'Candidate manifest drift'
if preview:
 # This exception is deliberately tied to the reviewed aesthetic candidate and
 # its known performance-only decision, not arbitrary future NO-GO evidence.
 assert sha(OUT/'architectural-cycle.json')=='08cf851731fc7d06087678a698883b6c59989fa48d1c0b3149c8bc6c9b7d3bdc', 'Unreviewed release decision'
 assert candidate['finalQA']['navigation']==24 and candidate['finalQA']['nodes']==17
 assert len(r['tests'])==9 and set(FILES).issubset(r['hashes']), 'Incomplete functional evidence'
 print('OPERATOR PREVIEW authorized: despliegala para probarla; hardware performance pending; technical decision remains NO-GO',flush=True)
# Fresh syntax checks are mandatory even for preview (no source modifications).
for f in ['reactor/reactor.js','chat/chat.js','integration.js']:
 subprocess.run(['node','--check',str(ROOT/f)],check=True)
subprocess.run(['php','-l',str(ROOT/'server/gate.php')],check=True)
if '--check-local' in sys.argv:raise SystemExit(0)
baseline=json.loads((OUT/'live-baseline.json').read_text())
assert baseline==candidate['productionUnchanged'], 'Baseline manifest mismatch'
items=[{'local':f,'path':'/opt/jarvis-access/gate.php' if f=='server/gate.php' else '/var/www/dashboard/'+f,'after':sha(ROOT/f)} for f in FILES]
code="""import pathlib,hashlib,json,sys
files=json.loads(sys.stdin.read());out={}
for f in files:
 p=pathlib.Path(f);out[f]=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
print(json.dumps(out))
"""
# Use a fixed argv script; file paths originate only in the frozen local manifest.
import shlex
query=subprocess.run(SSH+['python3 -c '+shlex.quote(code)],input=json.dumps(list(baseline)+['/var/www/dashboard/reactor/reactor.js']),text=True,capture_output=True,check=True)
actual=json.loads(query.stdout);assert all(actual[p]==h for p,h in baseline.items()),'LIVE DRIFT';assert actual['/var/www/dashboard/reactor/reactor.js'] is None,'New asset already exists'
print('PASS baseline: all protected/candidate hashes unchanged; seven-file selective publish ready')
if '--deploy' not in sys.argv:raise SystemExit(0)
# Never trade access control for a preview. Probe both edge and origin before writes.
for origin in [False,True]:
 for path,expected in [('/',303),('/login.html',200),('/chat/chat.js',401),('/reactor/reactor.js',401)]:
  cmd=['curl','--silent','--show-error','--max-time','20','-o','/dev/null','-w','%{http_code}']
  if origin:cmd+=['--resolve','dashboard.microtechai.es:443:178.104.253.211']
  result=subprocess.run(cmd+['https://dashboard.microtechai.es'+path],capture_output=True,text=True,check=True)
  assert result.stdout==str(expected),'Authentication preflight failed'
ts=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');stage='/root/mia-integration-upload-'+ts;backup='/root/mia-integration-rollback-'+ts
subprocess.run(SSH+['mkdir -m 700 '+stage],check=True)
for i,item in enumerate(items):
 item['before']=actual[item['path']];item['upload']=str(i)
 subprocess.run(SCP+[str(ROOT/item['local']),'root@178.104.253.211:'+stage+'/'+str(i)],check=True)
manifest={'backup':backup,'stage':stage,'items':items,'baseline':baseline,'noRestarts':True,'mode':'operator-preview' if preview else 'technical-release','technicalDecision':decision['decision'],'hardwarePerformance':'pending' if preview else 'accepted','operatorAuthorization':'despliegala para probarla' if preview else None,'candidateManifestSHA256':sha(OUT/'candidate-manifest.json'),'decisionSHA256':sha(OUT/'architectural-cycle.json')}
mp=OUT/'deployment-pending.json';mp.write_text(json.dumps(manifest,indent=2))
subprocess.run(SCP+[str(mp),'root@178.104.253.211:'+stage+'/manifest.json'],check=True)
remote="""import pathlib,json,hashlib,shutil,os,sys
stage=pathlib.Path(sys.argv[1]);m=json.loads((stage/'manifest.json').read_text());backup=pathlib.Path(m['backup']);backup.mkdir(mode=0o700)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
for p,h in m['baseline'].items():assert sha(pathlib.Path(p))==h, 'Baseline changed '+p
for item in m['items']:
 target=pathlib.Path(item['path']);assert sha(target)==item['before'], 'Target drift';assert sha(stage/item['upload'])==item['after'], 'Upload mismatch'
 if target.exists():shutil.copy2(target,backup/item['upload'])
(backup/'manifest.json').write_text(json.dumps(m,indent=2))
applied=[]
try:
 for item in m['items']:
  target=pathlib.Path(item['path']);assert sha(target)==item['before'], 'Target drift before replace'
  target.parent.mkdir(parents=True,exist_ok=True)
  temp=target.parent/('.mia-'+target.name+'.tmp');shutil.copyfile(stage/item['upload'],temp)
  if target.exists():
   st=target.stat();os.chmod(temp,st.st_mode);os.chown(temp,st.st_uid,st.st_gid)
  else:os.chmod(temp,0o644)
  os.replace(temp,target);applied.append(item);assert sha(target)==item['after']
except Exception:
 for item in reversed(applied):
  target=pathlib.Path(item['path']);assert sha(target)==item['after'],'Concurrent drift blocks rollback'
  if item['before'] is None:target.unlink()
  else:shutil.copy2(backup/item['upload'],target)
 raise
m['verified']={i['path']:sha(pathlib.Path(i['path'])) for i in m['items']}
for p,h in m['baseline'].items():
 if p not in m['verified']:assert sha(pathlib.Path(p))==h,'Unrelated drift '+p
(backup/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps(m))
"""
res=subprocess.run(SSH+['python3 - '+stage],input=remote,text=True,capture_output=True,check=True)
verified=json.loads(res.stdout);(OUT/'deployment-manifest.json').write_text(json.dumps(verified,indent=2));print('PASS published and hashes verified',backup)
