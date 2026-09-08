"""Scoped candidate signature scan; not a guarantee of absence of secrets."""
from pathlib import Path
import subprocess,re,json
ROOT=Path(__file__).resolve().parents[1]
files=set(subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=ROOT,text=True).splitlines())|set(subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines())
patterns={'private-key':r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----','github-token':r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}','openai-key':r'sk-(?:proj-)?[A-Za-z0-9_-]{40,}','aws-key':r'AKIA[A-Z0-9]{16}','credential-url':r'https?://[^\s/@:]+:[^\s/@]+@','bearer-value':r'Bearer\s+[A-Za-z0-9_.-]{25,}'}
hits=[];scanned=[];binary=[]
for f in sorted(files):
 p=ROOT/f
 if not p.is_file():continue
 data=p.read_bytes()
 try:text=data.decode('utf-8')
 except UnicodeDecodeError:binary.append(f);continue
 scanned.append(f)
 for name,pattern in patterns.items():
  for m in re.finditer(pattern,text):hits.append({'file':f,'line':text.count('\n',0,m.start())+1,'rule':name})
report={'scope':'HEAD diff plus untracked candidate UTF8 files, signature-only; synthetic fixture-user/password permitted','textFiles':len(scanned),'binaryFilesNotTextScanned':binary,'hits':hits}
(ROOT/'docs/evidence/call/secret-scan.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(bool(hits))
