"""Direct, selective phase5 deployment. No credentials, account or service changes.
Run only after local fixtures pass. nginx reload is graceful after nginx -t.
"""
from pathlib import Path
import base64, hashlib, json, shlex, subprocess
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=Path('/home/ddr/.hermes/phase5-private')
SSH=['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','StrictHostKeyChecking=yes','root@178.104.253.211']
def remote(code):
    return subprocess.run(SSH+['python3 -'],input=code,text=True,capture_output=True,check=True).stdout
old=(PRIVATE/'nginx.before').read_text()
marker='# Dashboard - Static files + PHP API'
assert old.count(marker)==1
nginx=old.split(marker)[0]+(ROOT/'server/nginx-dashboard.conf').read_text()
files={
 '/etc/nginx/sites-available/microtechai':nginx.encode(),
 '/var/www/dashboard/index.html':(ROOT/'index.html').read_bytes(),
 '/var/www/dashboard/api/chat.php':(ROOT/'api/chat.php').read_bytes(),
 '/var/www/dashboard/chat/chat.js':(ROOT/'chat/chat.js').read_bytes(),
 '/var/www/dashboard/login.html':(ROOT/'login.html').read_bytes(),
 '/opt/jarvis-access/session.php':(ROOT/'server/session.php').read_bytes(),
 '/opt/jarvis-access/gate.php':(ROOT/'server/gate.php').read_bytes(),
}
expected={
 '/etc/nginx/sites-available/microtechai':hashlib.sha256((PRIVATE/'nginx.before').read_bytes()).hexdigest(),
 '/var/www/dashboard/index.html':hashlib.sha256((PRIVATE/'index.before').read_bytes()).hexdigest(),
 '/var/www/dashboard/api/chat.php':hashlib.sha256((PRIVATE/'chat.before').read_bytes()).hexdigest(),
 '/var/www/dashboard/chat/chat.js':hashlib.sha256(subprocess.check_output(['git','show','40c64f2:chat/chat.js'],cwd=ROOT)).hexdigest(),
}
payload={p:base64.b64encode(b).decode() for p,b in files.items()}
code='''from pathlib import Path
import base64,datetime,hashlib,json,os,shutil,subprocess,pwd
files=PAYLOAD
expected=EXPECTED
assert str(Path('/etc/nginx/sites-enabled/microtechai').resolve())=='/etc/nginx/sites-available/microtechai'
for p in files:
 f=Path(p)
 if p in expected: assert hashlib.sha256(f.read_bytes()).hexdigest()==expected[p], 'DRIFT '+p
 else: assert not f.exists(), 'NEW PATH EXISTS '+p
backup=Path('/root/jarvis-access5-rollback-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
manifest={'rollback_dir':str(backup),'files':[]}
for p,data in files.items():
 f=Path(p); rec={'path':p,'before':None,'after':hashlib.sha256(base64.b64decode(data)).hexdigest()}
 if f.exists():
  st=f.stat(); rec.update(before=hashlib.sha256(f.read_bytes()).hexdigest(),mode=oct(st.st_mode & 0o777),uid=st.st_uid,gid=st.st_gid)
  dest=backup/p.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);os.chown(dest,st.st_uid,st.st_gid)
 manifest['files'].append(rec)
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
# Validate the exact candidate with all real vhosts BEFORE changing live files.
candidate=backup/'microtechai.candidate';candidate.write_bytes(base64.b64decode(files['/etc/nginx/sites-available/microtechai']))
main=Path('/etc/nginx/nginx.conf').read_text();needle='include /etc/nginx/sites-enabled/*;';assert main.count(needle)==1
includes='\\n'.join('include '+str(candidate if p.name=='microtechai' else p)+';' for p in sorted(Path('/etc/nginx/sites-enabled').iterdir()))
testconf=backup/'nginx-test.conf';testconf.write_text(main.replace(needle,includes))
# nginx resolves relative includes against -c's directory, not only -p.
for name in ['snippets','fastcgi_params','fastcgi.conf','mime.types','proxy_params','uwsgi_params','scgi_params','modules-enabled']:
 source=Path('/etc/nginx')/name
 if source.exists(): (backup/name).symlink_to(source)
subprocess.run(['nginx','-t','-c',str(testconf),'-p','/etc/nginx/'],check=True)
www=pwd.getpwnam('www-data')
# Private modules first, nginx configuration last. Atomic replacement per file.
for p in sorted(files,key=lambda p: (p.startswith('/etc/nginx'),not p.startswith('/opt/'))):
 f=Path(p);f.parent.mkdir(parents=True,exist_ok=True)
 if p.startswith('/opt/jarvis-access/'):
  os.chown(f.parent,0,www.pw_gid);os.chmod(f.parent,0o750)
 tmp=f.with_name(f.name+'.access5-tmp');tmp.write_bytes(base64.b64decode(files[p]));os.chmod(tmp,0o640 if p.startswith('/opt/') else 0o644);os.chown(tmp,0,www.pw_gid if p.startswith('/opt/') else 0)
 if p.endswith('.php'): subprocess.run(['php','-l',str(tmp)],check=True,capture_output=True)
 os.replace(tmp,f)
subprocess.run(['nginx','-t'],check=True)
subprocess.run(['systemctl','reload','nginx'],check=True)
for rec in manifest['files']: assert hashlib.sha256(Path(rec['path']).read_bytes()).hexdigest()==rec['after']
print(json.dumps(manifest,indent=2))
'''.replace('PAYLOAD',repr(payload)).replace('EXPECTED',repr(expected))
try:
 out=remote(code)
except subprocess.CalledProcessError as e:
 print(e.stdout); print(e.stderr); raise
manifest=json.loads(out)
outpath=ROOT/'docs/evidence/phase5/deployment-manifest.json';outpath.parent.mkdir(parents=True,exist_ok=True);outpath.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
