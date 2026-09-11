"""Isolated real software-WebGL comparison, NOT authenticated production QA.
Run from repo. Baseline is read from Git, never a public authenticated page.
All routed content is test-only; no runtime assets or credentials are exposed.
"""
import json, subprocess, statistics
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops, ImageStat
ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/home/ddr/jarvis-phase6-artifacts'); OUT.mkdir(exist_ok=True)
BASE='710159086df80ed6f5956714dd2187264f7e1a95'
report={'backend':'Chromium ANGLE SwiftShader, software only; isolated component, no authentication','samples':[]}
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    for version in ['baseline','new']:
        shader=subprocess.check_output(['git','show',BASE+':fire/shaders.js'],cwd=ROOT) if version=='baseline' else (ROOT/'fire/shaders.js').read_bytes()
        folder=OUT/version;folder.mkdir(exist_ok=True)
        for profile,distance,angle in [('normal',100,0),('close',30,0),('oblique',30,.78),('side',30,1.57),('back',30,3.14),('low',30,.78),('reduced',30,0)]:
            page=browser.new_page(viewport={'width':1200,'height':800})
            def route(r):
                key=urlparse(r.request.url).path
                data={'/':((ROOT/'tests/fire-webgl.html').read_bytes(),'text/html'),'/three.js':((ROOT/'tests/vendor/three-r128.cjs').read_bytes(),'text/javascript'),'/fire/shaders.js':(shader,'text/javascript')}.get(key)
                if data:r.fulfill(body=data[0],content_type=data[1])
                else:r.abort()
            page.route('**/*',route)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
            page.goto('http://isolated-fire.test/')
            if version=='new' and profile=='low':page.evaluate('for(let i=0;i<180;i++) fire.update(.06)')
            if profile=='reduced':page.evaluate('fire.setState({speed:.2,reducedMotion:true})')
            page.evaluate('for(let i=0;i<90;i++) fire.update(1/60)')
            before=page.evaluate('([d,a])=>sample(d,a,0)',[distance,angle]);a=folder/f'{profile}-t0.png';page.screenshot(path=str(a))
            after=page.evaluate('([d,a])=>sample(d,a,60)',[distance,angle]);b=folder/f'{profile}-t1.png';page.screenshot(path=str(b))
            assert after['checksum']!=before['checksum'] and after['time']>before['time']
            assert after['outsideCore']>50 and after['blue']>after['changed']*.95
            assert after['glError']==0 and all(x['runnable'] for x in after['programs'])
            timing=page.evaluate('''()=>{const times=[];for(let i=0;i<8;i++){fire.update(1/60);const t=performance.now();renderer.render(scene,camera);pixels();times.push(performance.now()-t)}return times}''')
            im=Image.open(b).convert('RGB');rgb_data=im.tobytes();active=[tuple(rgb_data[i:i+3]) for i in range(0,len(rgb_data),3) if rgb_data[i+2]>60 and rgb_data[i+2]>rgb_data[i]*2]
            cyan=sum(1 for r,g,blue in active if g>220 and blue>220)/max(1,len(active))
            delta=ImageStat.Stat(ImageChops.difference(Image.open(a),Image.open(b))).mean
            if version=='new':assert cyan<.02,'No flat clipped cyan'
            report['samples'].append({'version':version,'profile':profile,'before':before,'after':after,'cyanClipFraction':cyan,'temporalMeanRGB':delta,'renderMsMedian':statistics.median(timing),'renderMsSamples':timing,'screenshots':[str(a),str(b)]})
            page.close()
    browser.close()
assert not errors,errors
report['errors']=errors;report['visualContracts']='PASS'
# Conservative release gate: do not ship a >3x synchronized render/readback
# regression in the only measured environment; this is not physical-GPU FPS.
baseline={r['profile']:r['renderMsMedian'] for r in report['samples'] if r['version']=='baseline'}
report['performanceFailures']=[{'profile':r['profile'],'ratio':r['renderMsMedian']/baseline[r['profile']]} for r in report['samples'] if r['version']=='new' and r['renderMsMedian']>baseline[r['profile']]*3]
report['result']='NO-GO: performance' if report['performanceFailures'] else 'PASS'
(OUT/'quality-results.json').write_text(json.dumps(report,indent=2))
for row in report['samples']:print(row['version'],row['profile'],'ms',round(row['renderMsMedian'],2),'cyan',round(row['cyanClipFraction'],4),'outside',row['after']['outsideCore'])
print('PASS: 14 cases, 28 actual frames, linked WebGL programs, motion/blue/outside-core/clipping guards')
print(report['result'])
if report['performanceFailures']:raise SystemExit(1)
