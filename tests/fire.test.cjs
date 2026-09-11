const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const THREE = require('./vendor/three-r128.cjs');
const root = path.join(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
function context() {
  const c = vm.createContext({THREE, console, requestAnimationFrame() { throw Error('Fire must not own RAF'); }, setTimeout() { throw Error('Fire must not own timers'); }});
  c.window = c;
  return c;
}
test('classic shader script coexists with legacy inline lexical names', () => {
  const c = context();
  vm.runInContext(read('fire/shaders.js'), c);
  // These were the real conflicting global lexical declarations in index.html.
  assert.doesNotThrow(() => vm.runInContext('const fireVertexShader = "legacy"; const fireFragmentShader = "legacy";', c));
});
test('full inline classic script has no declaration collision, without running auth', () => {
  const c = context();
  vm.runInContext(read('fire/shaders.js'), c);
  const inline = [...read('index.html').matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
  const sentinel = {};
  c.stopBeforeRuntime = sentinel;
  // GlobalDeclarationInstantiation precedes execution. Stop before ANY login/DOM code.
  assert.throws(() => vm.runInContext('throw stopBeforeRuntime;\n' + inline, c), e => e === sentinel);
});
test('explicit controller updates real THREE objects without own RAF; state and disposal', () => {
  const c = context();
  vm.runInContext(read('fire/shaders.js'), c);
  assert.equal(typeof c.JarvisFire?.createFire, 'function');
  vm.runInContext(read('fire/integration.js'), c);
  const parent = new THREE.Group();
  const sentinel = new THREE.Object3D(); parent.add(sentinel);
  const f = c.JarvisFire.createFire({THREE, coreGroup:parent});
  for (const name of ['update','setState','dispose']) assert.equal(typeof f[name], 'function');
  const meshes = []; parent.traverse(o => { if(o.isMesh) meshes.push(o); });
  assert.ok(meshes.length > 0 && meshes.length <= 12);
  const mat = meshes[0].material;
  assert.equal(mat.depthWrite, false); assert.equal(mat.blending, THREE.NormalBlending);
  assert.equal(mat.uniforms.uTime.value, 0);
  f.update(0.1); assert.ok(mat.uniforms.uTime.value > 0);
  const t = mat.uniforms.uTime.value; f.update(0); assert.equal(mat.uniforms.uTime.value,t);
  f.update(NaN); f.update(-1); assert.equal(mat.uniforms.uTime.value,t);
  f.setState({intensity:1.4,speed:1.2});
  // Phase6 retains the state contract but eases targets instead of abrupt jumps.
  for(let i=0;i<120;i++) f.update(0.1);
  assert.ok(Math.abs(mat.uniforms.uIntensity.value-1.4)<1e-6);
  assert.ok(Math.abs(mat.uniforms.uSpeed.value-1.2)<1e-6);
  const bounds = new THREE.Box3().setFromObject(parent);
  assert.ok(bounds.max.y > 4.5 && bounds.max.x > 4.5, 'flame geometry extends outside core');
  let disposed = 0;
  const geometries = new Set(meshes.map(m => m.geometry));
  const materials = new Set(meshes.map(m => m.material));
  for(const r of [...geometries,...materials]) r.addEventListener('dispose',()=>disposed++);
  f.dispose(); f.dispose(); f.update(1);
  assert.equal(disposed,geometries.size+materials.size);
  assert.deepEqual(parent.children,[sentinel]);
  assert.equal(parent.rotation.y,0);
});
test('changed classic assets are versioned and fire honors reduced motion without hiding', () => {
  const html = read('index.html');
  for (const asset of ['fire/shaders.js', 'integration.js']) {
    const src = [...html.matchAll(/<script src="([^"]+)"/g)].map(m=>m[1]).find(s=>s.split('?')[0]===asset);
    assert.ok(src?.includes('?v='), asset + ' must have an explicit version');
  }
  assert.ok(html.includes('<script src="voice/speech.js"></script>'));
  assert.ok(html.includes("window.matchMedia('(prefers-reduced-motion: reduce)')"));
  const stateCall = html.match(/fireController\.setState\([^;]+;/)?.[0];
  for (const reduced of [true,false]) {
    let state;
    vm.runInNewContext(stateCall, {coreIntensity:1, chatBoost:0, fireMotionPreference:{matches:reduced}, fireController:{setState(s){state=s;}}});
    assert.equal(state.intensity,1);
    assert.equal(state.speed,reduced ? 0.2 : 1);
  }
});
test('page wires one fire controller into its only render loop', () => {
  const html = read('index.html');
  assert.equal((html.match(/new THREE.Scene\(/g)||[]).length,1);
  assert.equal((html.match(/requestAnimationFrame\(/g)||[]).length,1);
  assert.ok(/fireController\.update\(/.test(html), 'index must call fireController.update');
  assert.doesNotMatch(html,/const fireVertexShader|const fireFragmentShader/);
  assert.doesNotMatch(read('integration.js'),/new THREE.Group\(|import\(['"]\.\/fire/);
});
