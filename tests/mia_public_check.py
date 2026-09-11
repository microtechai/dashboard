"""Anonymous only: edge/origin old and current assets + selective live hashes. No login attempts."""
from pathlib import Path
import subprocess,tempfile,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/mia'
m=json.loads((OUT/'deployment-manifest.json').read_text());report=[]
private=['/reactor/reactor.js','/reactor/reactor.js?v=20260908-mia1','/reactor/reactor.js?v=old','/chat/chat.js?v=20260908-mia1','/chat/chat.css?v=20260908-mia1','/chat/chat.js?v=20260908-access5','/chat/chat.js?v=20260908-chat4','/chat/chat.css?v=20260908-chat4','/chat/core-state.js','/chat/voice/speech.mjs','/chat/voice/core.mjs','/fire/shaders.js?v=20260908-volume6-target','/voice/speech.js','/api/stats.php','/integration.js?v=20260908-executor3']
for target in ['edge','origin']:
 for path in ['/', '/index.html','/login.html',*private]:
  with tempfile.TemporaryDirectory() as tmp:
   headers=Path(tmp)/'headers';body=Path(tmp)/'body'
   cmd=['curl','--silent','--show-error','--max-time','20','-D',str(headers),'-o',str(body),'-w','%{http_code}']
   if target=='origin':cmd+=['--resolve','dashboard.microtechai.es:443:178.104.253.211']
   r=subprocess.run(cmd+['https://dashboard.microtechai.es'+path],capture_output=True,text=True,timeout=25)
   h={k.strip().lower():v.strip() for line in headers.read_text().splitlines() if ':' in line for k,v in [line.split(':',1)]} if headers.exists() else {}
   status=int(r.stdout or 0);expected=200 if path=='/login.html' else 303 if path in ['/','/index.html'] else 401
   report.append({'target':target,'path':path,'status':status,'expected':expected,'bytes':body.stat().st_size if body.exists() else 0,'headers':{k:h[k] for k in ['content-type','cache-control','location','cf-cache-status'] if k in h},'exit_code':r.returncode})
   if path=='/login.html':assert b'Microtech AI' in body.read_bytes() and b'JARVIS' not in body.read_bytes()
   print(target,path,status,flush=True)
(OUT/'anonymous.json').write_text(json.dumps(report,indent=2));assert all(x['status']==x['expected'] and x['exit_code']==0 for x in report)
checks={**m['baseline'],**m['verified']}
code='import pathlib,hashlib,json\nexpected='+repr(checks)+'\nactual={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in expected}\nassert expected==actual\nprint(json.dumps(actual,indent=2))'
r=subprocess.run(['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','root@178.104.253.211','python3 -'],input=code,text=True,capture_output=True,check=True)
(OUT/'live-hashes.json').write_text(r.stdout);print('PASS LIVE HASHES',len(checks))
