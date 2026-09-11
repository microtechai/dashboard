"""Diagnostic cost isolation only; release benchmark remains unchanged."""
import json, statistics
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/home/ddr/jarvis-phase6-artifacts/profile-before.json')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1200,'height':800})
 def route(r):
  key=r.request.url.split('test')[-1]
  f={'/':'tests/fire-webgl.html','/three.js':'tests/vendor/three-r128.cjs','/fire/shaders.js':'fire/shaders.js'}.get(key)
  import subprocess
  body=subprocess.check_output(['git','show','c931da9acc14f0a950be5321bdc372032f1e8186:fire/shaders.js'],cwd=ROOT) if key=='/fire/shaders.js' else (ROOT/f).read_bytes() if f else b''
  r.fulfill(body=body,content_type='text/html' if key=='/' else 'text/javascript') if f else r.abort()
 page.route('**/*',route);page.goto('http://isolated-fire.test/')
 result=page.evaluate('''()=>{sample(30,0,90);const out={};for(const mode of ['original','no-fire','flat-fragment']){flames[0].visible=mode!=='no-fire';if(mode==='flat-fragment'){flames[0].material.fragmentShader='void main(){gl_FragColor=vec4(0.,.2,1.,.5);}';flames[0].material.needsUpdate=true;}renderer.render(scene,camera);pixels();const rows=[];for(let i=0;i<8;i++){const t=performance.now();renderer.render(scene,camera);const submitted=performance.now();pixels();rows.push({submit:submitted-t,total:performance.now()-t});}out[mode]=rows;}return out;}''')
 OUT.write_text(json.dumps(result,indent=2));print({k:{'submitMedian':statistics.median(x['submit'] for x in v),'renderReadbackMedian':statistics.median(x['total'] for x in v)} for k,v in result.items()});b.close()
