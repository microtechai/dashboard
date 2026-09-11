async () => {
 const c=dashboardFireController,gl=renderer.getContext(),dpr=renderer.getPixelRatio(),results=[];
 const pixel=new Uint8Array(4);
 async function sample(name,setup,restore){
  setup();for(let i=0;i<3;i++)await new Promise(requestAnimationFrame);
  const frames=[],sync=[];let last=performance.now();
  for(let i=0;i<16;i++){
   await new Promise(requestAnimationFrame);const now=performance.now();frames.push(now-last);last=now;
   const t=performance.now();renderer.render(scene,camera);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);sync.push(performance.now()-t);
  }
  frames.sort((a,b)=>a-b);sync.sort((a,b)=>a-b);
  results.push({name,frameMedian:frames[8],frameP95:frames[15],renderReadbackMedian:sync[8],renderReadbackP95:sync[15],calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,dpr:renderer.getPixelRatio()});restore();
 }
 await sample('all',()=>{},()=>{});
 await sample('three-quarter-resolution',()=>renderer.setPixelRatio(dpr*.75),()=>renderer.setPixelRatio(dpr));
 await sample('half-resolution',()=>renderer.setPixelRatio(dpr*.5),()=>renderer.setPixelRatio(dpr));
 const original=new Map();c.group.traverse(o=>{if(o.material?.isMeshStandardMaterial)original.set(o,o.material);});
 const cheap=new THREE.MeshBasicMaterial({color:0x202a33});
 await sample('reactor-unlit-diagnostic-only',()=>original.forEach((m,o)=>o.material=cheap),()=>original.forEach((m,o)=>o.material=m));cheap.dispose();
 return {viewport:[innerWidth,innerHeight],dpr,software:true,results,scope:'diagnostic only; readPixels retained to synchronize GPU, sixteen samples per variant. RAF includes explicit additional render and is not release timing.'};
}
