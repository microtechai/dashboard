"""Anonymous edge+origin surface verification and fresh SSH hash check. Never logs cookies."""
from pathlib import Path
import json,subprocess,tempfile,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/call'
manifest=json.loads((OUT/'deployment-manifest.json').read_text());report=[]
initial=json.loads((OUT/'deployment-initial.json').read_text())
private=['/'+r['source'] for r in manifest['files']+initial['files'] if r['source'].startswith('chat/')]+['/chat/chat.js?v=20260908-chat4','/fire/shaders.js','/api/stats.php']
previous=json.loads((ROOT/'docs/evidence/phase7/deployment-manifest.json').read_text())
private=sorted(set(private+['/'+r['source'] for r in previous['files'] if r['source'].startswith('chat/')]))
for target in ['edge','origin']:
 for path in ['/', '/index.html','/login.html',*private]:
  with tempfile.TemporaryDirectory() as tmp:
   headers=Path(tmp)/'headers';body=Path(tmp)/'body'
   cmd=['curl','--silent','--show-error','--max-time','20','-D',str(headers),'-o',str(body),'-w','%{http_code}']
   if target=='origin':cmd+=['--resolve','dashboard.microtechai.es:443:178.104.253.211']
   r=subprocess.run(cmd+['https://dashboard.microtechai.es'+path],capture_output=True,text=True,timeout=25)
   h={k.strip().lower():v.strip() for line in headers.read_text().splitlines() if ':' in line for k,v in [line.split(':',1)]} if headers.exists() else {}
   status=int(r.stdout or 0);expected=200 if path=='/login.html' else 303 if path in ['/','/index.html'] else 401
   record={'target':target,'path':path,'status':status,'expected':expected,'bytes':body.stat().st_size if body.exists() else 0,'headers':{k:h[k] for k in ['content-type','cache-control','location','cf-cache-status'] if k in h},'exit_code':r.returncode}
   report.append(record);print(target,path,status,flush=True)
(OUT/'anonymous.json').write_text(json.dumps(report,indent=2))
assert all(x['status']==x['expected'] and x['exit_code']==0 for x in report)
checks={r['path']:r['after'] for r in initial['files']+manifest['files']};checks.update({'/var/www/dashboard/'+p:h for p,h in manifest['preserved'].items()})
code='import pathlib,hashlib,json\nexpected='+repr(checks)+'\nactual={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in expected}\nassert expected==actual\nprint(json.dumps(actual,indent=2))'
r=subprocess.run(['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','StrictHostKeyChecking=yes','root@178.104.253.211','python3 -'],input=code,text=True,capture_output=True,check=True)
(OUT/'live-hashes.json').write_text(r.stdout);print('Live hashes MATCH:',len(checks))
