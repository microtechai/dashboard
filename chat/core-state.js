// Passive bridge: the existing Three.js RAF owns every core update.
(function (root) {
  'use strict';
  let state = 'idle', level = 0, updated = 0;
  root.addEventListener('jarvis-chat-state', function (event) {
    const detail = event.detail;
    if (!detail || !['idle', 'thinking', 'speaking', 'listening', 'transcribing'].includes(detail.state)) return;
    state = detail.state;
    level = Number.isFinite(detail.level) ? Math.max(0, Math.min(1, detail.level)) : 0;
    updated = root.performance.now();
  });
  root.JarvisCoreState = Object.freeze({
    // No audio ownership, scene objects, timers or animation loop are created here.
    createVisualController(group) {
      const emissive = new Set(), rings = new Set(), arcs = new Set(), nuclei = [];
      group.traverse(object => {
        const material = object.material;
        if (!material) return;
        if (material.emissive && material.emissive.getHex() !== 0) emissive.add(material);
        if (material.isMeshBasicMaterial && material.transparent) rings.add(material);
        if (object.geometry?.type === 'IcosahedronGeometry') nuclei.push(object);
        if (object.userData.arc) arcs.add(material);
      });
      const firstEmissive = [...emissive][0];
      arcs.forEach(material => {
        if (!material.uniforms || !firstEmissive || typeof material.fragmentShader !== 'string') return;
        if (!material.uniforms.stateColor && material.fragmentShader.includes('vec3(.22,.66,1.)')) {
          material.uniforms.stateColor = { value: firstEmissive.emissive.clone() };
          material.fragmentShader = 'uniform vec3 stateColor;\n' + material.fragmentShader.replace('vec3(.22,.66,1.)', 'stateColor');
          material.needsUpdate = true;
        }
      });
      const firstArc = arcs.values().next().value;
      const palette = { idle: 0x249ac2, listening: 0x22d3ee, transcribing: 0x22d3ee,
        thinking: 0xd6a343, speaking: 0x2dd4a0 };
      return Object.freeze({
        update(now, time, reducedMotion) {
          const color = palette[state] ?? palette.idle;
          // Same audio freshness limit as the existing bridge. No noise gate or
          // simulated voice pulse: absent, silent and stale levels stay zero.
          const voice = ['listening', 'transcribing', 'speaking'].includes(state);
          const audio = voice && now - updated <= 1000 ? level : 0;
          const pulse = reducedMotion ? 0 : state === 'thinking' ?
            0.25 + Math.sin(time * 2) * 0.1 : audio;
          emissive.forEach(material => {
            if (material.color?.setHex) material.color.setHex(color);
            if (material.emissive?.setHex) material.emissive.setHex(color);
            if ('emissiveIntensity' in material) material.emissiveIntensity = 0.6 + pulse;
          });
          rings.forEach(material => { if (material.color?.setHex) material.color.setHex(color); material.opacity = 0.45 + pulse * 0.3; });
          arcs.forEach(material => {
            if (material.uniforms?.stateColor?.value?.setHex) material.uniforms.stateColor.value.setHex(color);
            if (material.uniforms?.power) material.uniforms.power.value = (material === firstArc ? 0.12 : 0.85) + pulse * 0.3;
          });
          nuclei.forEach(core => core.scale.setScalar(1 + pulse * 0.12));
        }
      });
    },
    boost(now, time, reducedMotion) {
      // Audio level is supplied by the playing WAV analyser, never invented.
      // A missing stream of audio events must not leave the nucleus "speaking".
      if (['speaking', 'listening'].includes(state) && now - updated > 1000) return 0;
      if (['thinking', 'transcribing'].includes(state) && now - updated > 90000) return 0;
      const amount = ['speaking', 'listening'].includes(state) ? level * 0.8 :
        ['thinking', 'transcribing'].includes(state) ? 0.25 + Math.sin(time * 5) * 0.1 : 0;
      return amount * (reducedMotion ? 0.2 : 1);
    }
  });
})(window);
