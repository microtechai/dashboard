/* Microtech AI / MIA. Procedural r128 port of approved reactor, no RAF/network/audio ownership. */
(function(root){
'use strict';
function create({THREE:T,coreGroup}) {
 const reactor=new T.Group();reactor.name='mia-reactor';reactor.scale.setScalar(10);reactor.rotation.set(.23,-.25,-.08);coreGroup.add(reactor);
 const metal=new T.MeshStandardMaterial({color:0x202a33,metalness:.88,roughness:.36});
 const dark=new T.MeshStandardMaterial({color:0x070b11,metalness:.7,roughness:.48});
 const edge=new T.MeshStandardMaterial({color:0x45505a,metalness:.85,roughness:.3});
 const blue=new T.MeshStandardMaterial({color:0x164b67,emissive:0x087bb5,emissiveIntensity:.6,metalness:.5,roughness:.3});
 const white=new T.MeshStandardMaterial({color:0x4693ba,emissive:0x1a91d0,emissiveIntensity:1.3,roughness:.3});
 function mesh(g,m,parent,x=0,y=0,z=0){const o=new T.Mesh(g,m);o.position.set(x,y,z);parent.add(o);return o;}
 function ring(r,t,depth,z,mat,parent=reactor,arc=Math.PI*2,start=0){const s=new T.Shape();s.absarc(0,0,r,start,start+arc,false);if(arc>=Math.PI*2-.01){const hole=new T.Path();hole.absarc(0,0,r-t,0,Math.PI*2,true);s.holes.push(hole);}else{s.lineTo(Math.cos(start+arc)*(r-t),Math.sin(start+arc)*(r-t));s.absarc(0,0,r-t,start+arc,start,true);s.closePath();}return mesh(new T.ExtrudeGeometry(s,{depth,bevelEnabled:true,bevelSize:.025,bevelThickness:.025,bevelSegments:1,steps:1,curveSegments:Math.max(2,Math.ceil(32*arc/(Math.PI*2)))}),mat,parent,0,0,z);}
 ring(1.92,.22,.32,-.35,dark);ring(1.93,.065,.12,-.02,edge);ring(1.76,.12,.22,0,metal);ring(1.56,.018,.07,.22,blue);ring(1.39,.23,.18,.14,dark);ring(1.18,.07,.26,.24,metal);ring(.99,.022,.16,.30,edge);ring(.79,.12,.26,.36,dark);ring(.64,.028,.1,.49,edge);
 mesh(new T.CircleGeometry(.65,48),dark,reactor,0,0,-.28);
 for(let i=0;i<4;i++)ring(.59-i*.09,.025,.06,.30-i*.13,metal);
 const core=mesh(new T.IcosahedronGeometry(.12,2),white,reactor,0,0,-.03);ring(.22,.012,.02,-.13,blue);
 const rotor=new T.Group();reactor.add(rotor);
 for(let i=0;i<18;i++){const angle=i*Math.PI*2/18;ring(1.73,.25,.25,.1,i%3===0?edge:metal,rotor,.19,angle);ring(1.48,.045,.08,.38,i%2===0?blue:metal,reactor,.055,angle+.055);const bolt=mesh(new T.CylinderGeometry(.045,.045,.08,8),dark,reactor,Math.cos(angle)*1.84,Math.sin(angle)*1.84,.16);bolt.rotation.x=Math.PI/2;}
 for(let i=0;i<6;i++){const a=i*Math.PI/3;const bridge=mesh(new T.BoxGeometry(.17,.58,.25),metal,reactor,Math.cos(a)*1.04,Math.sin(a)*1.04,.73);bridge.rotation.z=a-Math.PI/2;mesh(new T.SphereGeometry(.04,8,6),edge,reactor,Math.cos(a)*1.23,Math.sin(a)*1.23,.88);}
 for(let i=0;i<3;i++)ring(2.15+i*.08,.008,.008,-.45,new T.MeshBasicMaterial({color:0x24445c,transparent:true,opacity:.45}),reactor,Math.PI*.42,i*2.1);
 // Batch immutable metal pieces by material. Geometry/appearance is unchanged;
 // one draw per material instead of one per bolt/coil. Dynamic core/arcs stay separate.
 function batchStatic(parent,exclude){
  const groups=new Map();
  for(const object of parent.children.slice()){
   if(!object.isMesh||object===exclude)continue;
   object.updateMatrix();
   const geometry=object.geometry.index?object.geometry.toNonIndexed():object.geometry.clone();
   geometry.applyMatrix4(object.matrix);
   if(!groups.has(object.material))groups.set(object.material,[]);
   groups.get(object.material).push(geometry);
   parent.remove(object);object.geometry.dispose();
  }
  for(const [material,parts] of groups){
   const total=parts.reduce((sum,g)=>sum+g.attributes.position.count,0),combined=new T.BufferGeometry();
   for(const [name,size] of [['position',3],['normal',3],['uv',2]]){
    const data=new Float32Array(total*size);let offset=0;
    for(const part of parts){const a=part.attributes[name];if(a)data.set(a.array,offset);offset+=part.attributes.position.count*size;}
    combined.setAttribute(name,new T.BufferAttribute(data,size));
   }
   combined.computeBoundingSphere();parent.add(new T.Mesh(combined,material));parts.forEach(g=>g.dispose());
  }
 }
 batchStatic(reactor,core);batchStatic(rotor);
 const key=new T.DirectionalLight(0xcfe5ff,2.8);key.position.set(-3,5,6);reactor.add(key);
 const rim=new T.DirectionalLight(0x277cff,1.4);rim.position.set(4,-1,2);reactor.add(rim);
 const arcs=createArcs(T,reactor);let time=0,disposed=false,reduced=false,input=0,output=0,inputAt=0,outputAt=0;
 function inputEvent(e){if(e.detail?.channel!=='input')return;input=clamp(e.detail.level);inputAt=root.performance.now();}
 function stateEvent(e){const s=e.detail;if(!s)return;if(s.state==='listening'){input=clamp(s.level);inputAt=root.performance.now();}if(s.state==='speaking'){output=clamp(s.level);outputAt=root.performance.now();}else if(['idle','transcribing','thinking'].includes(s.state)){output=0;}if(s.micActive===false&&s.state!=='listening')input=0;}
 root.addEventListener('mia-audio-level',inputEvent);root.addEventListener('jarvis-chat-state',stateEvent);
 return {group:reactor,stats:arcs.stats,
  get levels(){return {input,output};},
  setState(s={}){reduced=!!s.reducedMotion;},
  update(delta){if(disposed||!Number.isFinite(delta)||delta<0)return;const now=root.performance.now();if(now-inputAt>1000)input=0;if(now-outputAt>1000)output=0;if(!reduced)time+=Math.min(delta,.06);const level=Math.max(input,output);rotor.rotation.z=time*.022;white.emissiveIntensity=1.3+level;core.scale.setScalar(1+level*.12);blue.emissiveIntensity=.5+level*.6;arcs.update(time,level);},
  dispose(){if(disposed)return;disposed=true;root.removeEventListener('mia-audio-level',inputEvent);root.removeEventListener('jarvis-chat-state',stateEvent);const geos=new Set(),mats=new Set();reactor.traverse(o=>{if(o.geometry)geos.add(o.geometry);if(o.material)mats.add(o.material);});geos.forEach(g=>g.dispose());mats.forEach(m=>m.dispose());reactor.removeFromParent?reactor.removeFromParent():coreGroup.remove(reactor);}
 };
}
function clamp(v){return Number.isFinite(v)?Math.max(0,Math.min(1,v)):0;}
function createArcs(T,parent){
 const segments=32,count=18,points=segments+1,paths=[];
 const polar=(r,a,z)=>new T.Vector3(r*Math.cos(a),r*Math.sin(a),z);
 for(let i=0;i<9;i++){const a=i*Math.PI*2/9+.08;paths.push({start:polar(1.46,a,.48),end:polar(.66,a+.35,.66),seed:i*2.73,branch:false});paths.push({start:null,end:polar(1.46,a+.37,.48),seed:i*2.73+1.2,branch:true,parent:i*2});}
 const center=new Float32Array(count*points*3),position=new Float32Array(count*points*2*3),glowPosition=new Float32Array(position.length),uv=new Float32Array(count*points*4),indices=[];
 for(let k=0;k<count;k++)for(let j=0;j<points;j++){let v=(k*points+j)*2;uv.set([j/segments,0,j/segments,1],v*2);if(j<segments)indices.push(v,v+1,v+2,v+1,v+3,v+2);}
 function geometry(array){let g=new T.BufferGeometry();g.setAttribute('position',new T.BufferAttribute(array,3).setUsage(T.DynamicDrawUsage));g.setAttribute('uv',new T.BufferAttribute(uv,2));g.setIndex(indices);return g;}
 const main=geometry(position),halo=geometry(glowPosition);
 const makeMat=opacity=>new T.ShaderMaterial({transparent:true,depthWrite:false,depthTest:true,side:T.DoubleSide,blending:T.AdditiveBlending,uniforms:{power:{value:opacity}},vertexShader:'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'varying vec2 vUv; uniform float power; void main(){float edge=pow(max(0.,1.-abs(vUv.y*2.-1.)),1.4);gl_FragColor=vec4(vec3(.22,.66,1.),edge*power);}'});
 const coreMat=makeMat(.9),haloMat=makeMat(.13);
 for(const [g,m] of [[halo,haloMat],[main,coreMat]]){const mesh=new T.Mesh(g,m);mesh.frustumCulled=false;mesh.userData.arc=true;parent.add(mesh);}
 const a=new T.Vector3(),b=new T.Vector3(),p=new T.Vector3(),tangent=new T.Vector3(),side=new T.Vector3(),normal=new T.Vector3(0,0,1);
 function update(time,level){
  for(let k=0;k<count;k++){
   const d=paths[k];if(d.branch)a.fromArray(center,(d.parent*points+19)*3);else a.copy(d.start);b.copy(d.end);
   for(let j=0;j<points;j++){const s=j/segments,envelope=Math.sin(Math.PI*s),seed=d.seed;const n=Math.sin(s*23+seed+time*1.5)*.055+Math.sin(s*57-seed+time*.8)*.026+Math.sin(s*101+seed-time*1.9)*.014;p.lerpVectors(a,b,s);const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;p.x+=-dy/len*n*envelope;p.y+=dx/len*n*envelope;p.z+=envelope*(.12+Math.sin(s*29+seed+time)*.055);p.toArray(center,(k*points+j)*3);}
   for(let j=0;j<points;j++){const idx=(k*points+j)*3;p.fromArray(center,idx);a.fromArray(center,(k*points+Math.max(0,j-1))*3);b.fromArray(center,(k*points+Math.min(segments,j+1))*3);tangent.subVectors(b,a).normalize();side.crossVectors(tangent,normal);if(side.lengthSq()<.001)side.set(1,0,0);else side.normalize();const s=j/segments,taper=d.branch?Math.max(.12,1-s):.45+.55*Math.sin(Math.PI*s);const w=(d.branch?.006:.009)*taper*(1+level*.32);
    for(let edge=0;edge<2;edge++)for(let c=0;c<3;c++){const value=p.getComponent(c),offset=side.getComponent(c)*w*(edge?1:-1),out=(k*points*2+j*2+edge)*3+c;position[out]=value+offset;glowPosition[out]=value+offset*4.2;}
   }
  }
  main.attributes.position.needsUpdate=true;halo.attributes.position.needsUpdate=true;coreMat.uniforms.power.value=.85+level*.5;haloMat.uniforms.power.value=.12+level*.09;
 }
 update(0,0);return {update,stats:{paths:count,segments}};
}
root.MiaReactor=Object.freeze({create});
})(window);
