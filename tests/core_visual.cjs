const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
const T = require('./vendor/three-r128.cjs');
const html = fs.readFileSync('index.html', 'utf8');
const source = fs.readFileSync('chat/core-state.js', 'utf8');
function fixture() {
  let now = 0;
  const handlers = {};
  const window = { performance: { now: () => now }, addEventListener(n, f) { (handlers[n] ||= []).push(f); }, removeEventListener() {} };
  const context = vm.createContext({ window });
  vm.runInContext('const state = "sentinel", level = "sentinel", group = "sentinel";', context);
  vm.runInContext(source, context);
  vm.runInContext(fs.readFileSync('reactor/reactor.js', 'utf8'), context);
  const reactor = window.MiaReactor.create({ THREE: T, coreGroup: new T.Group() });
  const visual = window.JarvisCoreState.createVisualController(reactor.group);
  let core; const rings = [], nodes = [];
  reactor.group.traverse(o => {
    if (o.geometry?.type === 'IcosahedronGeometry') core = o;
    if (o.material?.isMeshBasicMaterial) rings.push(o.material);
    if (o.userData.miaStage) nodes.push(o);
  });
  return { window, context, reactor, visual, core, rings, nodes,
    send(state, level) { handlers['jarvis-chat-state'].forEach(f => f({ detail: { state, level } })); },
    tick(t = 0, reduced = false) { visual.update(now, t, reduced); },
    expire() { now = 1001; } };
}
test('pipeline removed; existing render loop and raycaster retain sole ownership', () => {
  assert.doesNotMatch(html, /mia-pipeline|data-stage=/);
  assert.equal((html.match(/requestAnimationFrame\(/g) || []).length, 1);
  assert.equal((html.match(/new THREE.WebGLRenderer\(/g) || []).length, 1);
  assert.match(html, /intersectObjects\(nodeMeshes.filter\(mesh=>mesh.visible\)\)/);
  assert.match(html, /miaStateVisual.update\(now, time, fireMotionPreference.matches\)/);
  assert.doesNotMatch(source, /requestAnimationFrame|setTimeout|AudioContext|getUserMedia|createAnalyser/);
});
test('real state colors and continuous actual levels; no synthetic voice at zero or stale level', () => {
  const f = fixture();
  assert.equal(f.nodes.length, 21);
  assert.equal(f.reactor.stats.nodes, 7);
  assert.equal(f.reactor.focusStage('project'), true);
  assert.equal(f.reactor.focusStage('missing'), false);
  for (const [state, color] of Object.entries({ idle: 0x249ac2, listening: 0x22d3ee, transcribing: 0x22d3ee, thinking: 0xd6a343, speaking: 0x2dd4a0 })) {
    f.send(state, 0); f.tick();
    assert.equal(f.core.material.emissive.getHex(), color);
  }
  for (const state of ['listening', 'transcribing', 'speaking']) {
    f.send(state, 0); f.tick(0); const silent = f.core.scale.x;
    f.tick(1); assert.equal(f.core.scale.x, silent);
    for (const level of [0.001, 0.2, 0.6, 1]) {
      f.send(state, level); f.tick();
      assert.equal(f.core.scale.x, 1 + level * 0.12);
    }
    f.send(state, NaN); f.tick(); assert.equal(f.core.scale.x, 1);
  }
  f.send('speaking', 1); f.expire(); f.tick(); assert.equal(f.core.scale.x, 1);
  f.send('error', 1); f.tick(); assert.equal(f.core.material.emissive.getHex(), 0x2dd4a0);
});
test('idle and reduced motion stable; state colors survive; no globals or new GPU resources', () => {
  const f = fixture(); const geometries = new Set(), materials = new Set();
  f.reactor.group.traverse(o => { if (o.geometry) geometries.add(o.geometry); if (o.material) materials.add(o.material); });
  for (const state of ['idle', 'thinking', 'listening', 'transcribing', 'speaking']) {
    f.send(state, 0); f.tick(0, true); const color = f.core.material.emissive.getHex();
    f.send(state, 1); f.tick(100, true);
    assert.equal(f.core.scale.x, 1); assert.equal(f.core.material.emissiveIntensity, 0.6);
    assert.equal(f.core.material.emissive.getHex(), color);
  }
  f.send('idle', 1); f.tick(10); assert.equal(f.core.scale.x, 1);
  f.send('thinking', 0); f.tick(); const pulse = f.core.scale.x;
  f.tick(1); assert.notEqual(f.core.scale.x, pulse);
  assert.equal(vm.runInContext('state + level + group', f.context), 'sentinelsentinelsentinel');
  assert.deepEqual(Object.keys(f.window).sort(), ['JarvisCoreState', 'MiaReactor', 'addEventListener', 'performance', 'removeEventListener'].sort());
  f.reactor.group.traverse(o => { if (o.geometry) assert.ok(geometries.has(o.geometry)); if (o.material) assert.ok(materials.has(o.material)); });
  let disposed = 0; materials.forEach(m => m.addEventListener('dispose', () => disposed++));
  f.reactor.dispose(); assert.equal(disposed, materials.size);
});
