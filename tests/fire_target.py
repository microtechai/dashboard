"""Real GL target budget, renderer restoration and disposal regression."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1200,'height':800})
 def route(r):
  key=r.request.url.split('test')[-1]
  f={'/':'tests/fire-webgl.html','/three.js':'tests/vendor/three-r128.cjs','/fire/shaders.js':'fire/shaders.js'}.get(key)
  r.fulfill(body=(ROOT/f).read_bytes(),content_type='text/html' if key=='/' else 'text/javascript') if f else r.abort()
 page.route('**/*',route);page.goto('http://isolated-fire.test/')
 result=page.evaluate('''()=>{sample(30,.78,90);const texture=flames[0].material.uniforms.uFireBuffer?.value;return {calls:renderer.info.render.calls,hasTarget:!!texture,width:texture?.image.width,height:texture?.image.height,targetRestored:renderer.getRenderTarget()===null,clearAlpha:renderer.getClearAlpha(),autoClear:renderer.autoClear,viewport:renderer.getViewport(new THREE.Vector4()).toArray()};}''')
 assert result['calls']==5,'Nested render must not reset outer scene draw counters'
 assert result['hasTarget'],'Missing bounded offscreen fire target'
 assert result['width']<=512 and result['width']*result['height']<=1200*800/8,result
 assert result['targetRestored'] and result['clearAlpha']==1 and result['autoClear'] and result['viewport']==[0,0,1200,800],result
 extra=page.evaluate('''()=>{
   let buffer;const original=renderer.setRenderTarget.bind(renderer);
   renderer.setRenderTarget=(t,...args)=>{if(t)buffer=t;return original(t,...args);};
   sample(30,.78,0);const rgba=new Uint8Array(buffer.width*buffer.height*4);
   renderer.readRenderTargetPixels(buffer,0,0,buffer.width,buffer.height,rgba);
   const alphaClear=rgba[3]===0,alphaVisible=rgba.some((v,i)=>i%4===3&&v>0);
   let disposed=0;buffer.addEventListener('dispose',()=>disposed++);
   renderer.setPixelRatio(2);renderer.setSize(900,600);camera.aspect=1.5;camera.updateProjectionMatrix();renderer.render(scene,camera);
   const resized=buffer.width<=512&&buffer.height<=512;
   const occluder=new THREE.Mesh(new THREE.PlaneGeometry(10000,10000),new THREE.MeshBasicMaterial({color:0xff0000}));
   camera.getWorldDirection(occluder.position);occluder.position.multiplyScalar(2).add(camera.position);occluder.quaternion.copy(camera.quaternion);scene.add(occluder);
   renderer.render(scene,camera);const gl=renderer.getContext(),pixel=new Uint8Array(4);gl.readPixels(900,600,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
   const depthOccluded=pixel[0]===255&&pixel[1]===0&&pixel[2]===0;
   scene.remove(occluder);occluder.geometry.dispose();occluder.material.dispose();
   const texturesBefore=renderer.info.memory.textures;fire.dispose();fire.dispose();
   return {alphaClear,alphaVisible,resized,depthOccluded,disposed,removed:flames[0].parent===null,texturesReleased:texturesBefore-renderer.info.memory.textures,glError:gl.getError()};
 }''')
 assert all(extra[k] for k in ['alphaClear','alphaVisible','resized','depthOccluded','removed']),extra
 # Resize also disposes the old target storage; final disposal happens once.
 assert extra['disposed']==2 and extra['texturesReleased']==2 and extra['glError']==0,extra
 print('PASS alpha, opaque depth, DPR2 resize, GPU texture release',extra)
 print('PASS real GL: bounded target, original viewport/target/clear restored, idempotent disposal',result)
 b.close()
