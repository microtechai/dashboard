"""Six-file redesign, explicit operator preview. No security/performance waiver or restarts."""
from pathlib import Path
import subprocess,json,hashlib,datetime,shlex,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/mia/redesign'
FILES=['chat/voice/speech.mjs','api/chat.php','chat/chat.css','chat/chat.js','integration.js','index.html']
SSH=['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','root@178.104.253.211']
SCP=['scp','-i','/home/ddr/.ssh/hetzner-admin','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def validate_report(report,actual,preview):
 assert preview,'Explicit operator-preview required; physical GPU acceptance remains pending'
 expected=16
 if report.get('verificationMode')=='full-plus-targeted':
  expected=31
  assert report.get('productionSourceChangedAfterFullRun') is False,'Targeted rechecks cannot cover production-source drift'
 assert report['sourceStableDuringRun'] and len(report['tests'])==expected and all(t['exit_code']==0 for t in report['tests']),'Incomplete/failing functional evidence'
 assert set(FILES).issubset(report['hashes']) and all(actual.get(f)==h for f,h in report['hashes'].items()),'Tested-source drift'
def remote_hashes(paths):
 code='import json,pathlib,hashlib,sys; ps=json.load(sys.stdin); print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in ps}))'
 r=subprocess.run(SSH+['python3 -c '+shlex.quote(code)],input=json.dumps(paths),text=True,capture_output=True,check=True)
 return json.loads(r.stdout)
def probes():
 results=[]
 paths=[('/',303),('/index.html',303),('/login.html',200)]
 for f in ['chat/chat.js','chat/chat.css','chat/voice/speech.mjs','reactor/reactor.js','voice/speech.js']:
  for version in ['', '?v=20260908-mia1','?v=20260909-redesign2']:
   paths.append(('/'+f+version,401))
 paths.append(('/chat/voice/speech.mjs?v=20260909-emoji2',401))
 for origin in [False,True]:
  for path,expected in paths:
   cmd=['curl','--silent','--show-error','--max-time','20','-o','/dev/null','-w','%{http_code}']
   if origin:cmd+=['--resolve','dashboard.microtechai.es:443:178.104.253.211']
   status=int(subprocess.check_output(cmd+['https://dashboard.microtechai.es'+path],text=True));results.append({'origin':origin,'path':path,'status':status})
   assert status==expected,'AUTH DRIFT '+path+' '+str(status)
 return results
REMOTE=r'''import pathlib,json,hashlib,shutil,os,sys
stage=pathlib.Path(sys.argv[1]);m=json.loads((stage/'manifest.json').read_text());backup=pathlib.Path(m['backup'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['baseline'].items():assert sha(pathlib.Path(p))==h,'LIVE DRIFT '+p
for item in m['items']:assert sha(stage/item['upload'])==item['after'],'UPLOAD DRIFT'
backup.mkdir(mode=0o700)
for item in m['items']:shutil.copy2(item['path'],backup/item['upload'])
(backup/'manifest.json').write_text(json.dumps(m,indent=2));applied=[]
try:
 for item in m['items']:
  target=pathlib.Path(item['path']);assert sha(target)==item['before'],'TARGET DRIFT'
  tmp=target.parent/('.mia-redesign-'+target.name+'.tmp');shutil.copyfile(stage/item['upload'],tmp);st=target.stat();os.chmod(tmp,st.st_mode);os.chown(tmp,st.st_uid,st.st_gid);os.replace(tmp,target);applied.append(item);assert sha(target)==item['after']
except Exception:
 for item in reversed(applied):
  target=pathlib.Path(item['path']);assert sha(target)==item['after'],'CONCURRENT DRIFT'
  shutil.copy2(backup/item['upload'],target)
 raise
print('Applied '+str(len(applied))+' guarded files; no restarts')
'''
def main():
 report=json.loads((OUT/'release-validation.json').read_text());validate_report(report,{f:sha(ROOT/f) for f in report['hashes']},'--operator-preview' in sys.argv)
 if report.get('verificationMode')=='full-plus-targeted':
  assert sha(OUT/'regressions.json')==report['baseFullRunSHA256'] and sha(OUT/'call-regression/tests.json')==report['baseCallRunSHA256'],'Historical evidence drift'
  base=json.loads((OUT/'regressions.json').read_text());calls=json.loads((OUT/'call-regression/tests.json').read_text())
  assert base['hashes']==report['hashes'] and [i for i,t in enumerate(base['tests']) if t['exit_code']]==[6,10]
  assert [i for i,t in enumerate(calls['tests']) if t['exit_code']]==[6]
 for f in ['chat/chat.js','integration.js','chat/voice/speech.mjs']:subprocess.run(['node','--check',str(ROOT/f)],check=True)
 subprocess.run(['php','-l',str(ROOT/'api/chat.php')],check=True)
 baseline=json.loads((OUT/'live-baseline.json').read_text());assert remote_hashes(list(baseline))==baseline,'LIVE SECURITY/SOURCE DRIFT'
 before=probes();print('PASS preflight: 18 hashes and '+str(len(before))+' anonymous probes')
 if '--deploy' not in sys.argv:return
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');stage='/root/mia-redesign-upload-'+stamp;backup='/root/mia-redesign-rollback-'+stamp
 items=[{'local':f,'path':'/var/www/dashboard/'+f,'before':baseline['/var/www/dashboard/'+f],'after':sha(ROOT/f),'upload':str(i)} for i,f in enumerate(FILES)]
 manifest={'mode':'operator-preview','hardwarePerformance':'pending','technicalRelease':False,'operatorAuthorization':'rediseño y publicación directa autorizados','timestamp':stamp,'stage':stage,'backup':backup,'items':items,'baseline':baseline,'noRestarts':True,'qaSHA256':sha(OUT/'release-validation.json')}
 subprocess.run(SSH+['mkdir -m 700 '+stage],check=True)
 for item in items:subprocess.run(SCP+[str(ROOT/item['local']),'root@178.104.253.211:'+stage+'/'+item['upload']],check=True)
 private=Path('/home/ddr/mia-redesign-release');private.mkdir(mode=0o700,exist_ok=True);mp=private/'deployment-manifest.json';mp.write_text(json.dumps(manifest,indent=2))
 subprocess.run(SCP+[str(mp),'root@178.104.253.211:'+stage+'/manifest.json'],check=True)
 subprocess.run(SSH+['php -l '+stage+'/1'],check=True)
 subprocess.run(SSH+['python3 -c '+shlex.quote(REMOTE)+' '+shlex.quote(stage)],check=True)
 after=remote_hashes(list(baseline));expected={**baseline,**{i['path']:i['after'] for i in items}};assert after==expected,'POST-DEPLOY DRIFT'
 post=probes();(private/'live-hashes.json').write_text(json.dumps(after,indent=2))
 public={k:v for k,v in manifest.items() if k not in ['baseline','stage']};public['protectedFilesUnchanged']=len(baseline)-len(items);public['verifiedHashes']=len(after);public['probes']=post;public['manifestSHA256']=sha(mp)
 (OUT/'operator-preview.json').write_text(json.dumps(public,indent=2));print('Verified '+str(len(after))+' remote hashes, '+str(len(post))+' anonymous probes; OPERATOR PREVIEW, hardware pending')
if __name__=='__main__':main()
