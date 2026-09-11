const test=require('node:test'), assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const THREE=require('./vendor/three-r128.cjs');
function make(options={}) { const c={};c.window=c;vm.runInNewContext(fs.readFileSync('fire/shaders.js','utf8'),c);const group=new THREE.Group();return {group,fire:c.JarvisFire.createFire({THREE,coreGroup:group,...options})}; }
test('one bounded volume instead of crossed billboards; coherent camera in object coordinates',()=>{
 const {group,fire}=make();assert.equal(group.children.length,1,'one volume draw');const mesh=group.children[0];
 assert.equal(mesh.geometry.type,'BoxGeometry');assert.equal(mesh.material.blending,THREE.NormalBlending);assert.equal(mesh.material.side,THREE.BackSide);assert.equal(mesh.material.depthWrite,false);
 group.rotation.y=.7;group.updateMatrixWorld(true);const camera=new THREE.PerspectiveCamera();camera.position.set(0,10,100);camera.updateMatrixWorld();mesh.onBeforeRender(null,null,camera);
 const expected=camera.position.clone().applyMatrix4(new THREE.Matrix4().copy(mesh.matrixWorld).invert());assert.ok(mesh.material.uniforms.uCamera.value.distanceTo(expected)<1e-6);fire.dispose();assert.equal(group.children.length,0);
});
test('production integration supplies responsive and reduced-motion quality without an extra loop',()=>{
 const html=fs.readFileSync('index.html','utf8');assert.match(html,/quality:.*max-width: 760px/);assert.match(html,/reducedMotion: fireMotionPreference.matches/);
});
test('sustained very slow frames also lower quality; long tab resumes are ignored',()=>{
 const {group,fire}=make();const u=group.children[0].material.uniforms;for(let i=0;i<70;i++)fire.update(.3);assert.equal(u.uSteps.value,24);fire.dispose();
 const second=make();for(let i=0;i<70;i++)second.fire.update(10);assert.equal(second.group.children[0].material.uniforms.uSteps.value,40);second.fire.dispose();
});
test('one local noise atlas amortizes turbulence and is disposed exactly once',()=>{
 const {group,fire}=make();const texture=group.children[0].material.uniforms.uNoise?.value;assert.ok(texture?.isDataTexture,'procedural local atlas, no external fetch');assert.equal(texture.image.data.length,256*256*4);assert.equal(texture.wrapS,THREE.RepeatWrapping);assert.equal(texture.minFilter,THREE.LinearFilter);let count=0;texture.addEventListener('dispose',()=>count++);fire.dispose();fire.dispose();assert.equal(count,1);
});
test('smoothed state, bounded automatic quality and reduced-motion profile',()=>{
 const {group,fire}=make();const u=group.children[0].material.uniforms;
 fire.setState({intensity:2,speed:3});assert.equal(u.uIntensity.value,1,'state changes ease rather than jump');fire.update(.016);assert.ok(u.uIntensity.value>1&&u.uIntensity.value<2);
 for(let i=0;i<180;i++)fire.update(.06);assert.equal(u.uSteps.value,24,'slow caller frames lower bounded GPU work');
 for(let i=0;i<600;i++)fire.update(.01);assert.equal(u.uSteps.value,40,'stable recovery with hysteresis');
 fire.setState({reducedMotion:true});fire.update(.016);assert.equal(u.uSteps.value,24);let time=u.uTime.value;fire.update(.1);assert.ok(u.uTime.value-time<=.020001);
 fire.dispose();time=u.uTime.value;fire.update(.1);fire.setState({speed:1});assert.equal(u.uTime.value,time);
 const mobile=make({quality:'low'});assert.equal(mobile.group.children[0].material.uniforms.uSteps.value,24);mobile.fire.dispose();
});
