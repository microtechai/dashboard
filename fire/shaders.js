// JARVIS electric fire — classic-script namespace, Three.js r128.
// Qwen proposed scoped crossed planes + coherent fbm; reviewed/corrected by Hermes.
(function (root) {
  'use strict';
  const vertexShader = `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `;
  const fragmentShader = `
    uniform float uTime;
    uniform float uSpeed;
    uniform float uIntensity;
    uniform float uSeed;
    varying vec2 vUv;

    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
    }
    // Interpolate all four lattice corners; no cell-boundary discontinuities.
    float noise(vec2 p) {
      vec2 i = floor(p), f = fract(p);
      vec2 w = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), w.x),
                 mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0)), w.x), w.y);
    }
    float fbm(vec2 p) {
      float n = 0.0, a = 0.5;
      for (int i = 0; i < 3; i++) {
        n += a * noise(p);
        p = p * 2.03 + vec2(19.1, 7.7);
        a *= 0.5;
      }
      return n / 0.875;
    }
    void main() {
      float h = vUv.y;
      float x = vUv.x * 2.0 - 1.0;
      float t = uTime * uSpeed;
      // Negative time in the vertical coordinate advects features UP the plane.
      vec2 p = vec2(x * 3.8 + uSeed, h * 4.8 - t * 1.6);
      float warp = fbm(p * 0.65 + vec2(0.0, -t * 0.18));
      float n = fbm(p + vec2((warp - 0.5) * 1.5, 0.0));
      float curl = (warp - 0.5) * 0.38 * h;
      float width = 0.82 * pow(max(1.0 - h, 0.0), 0.65);
      float edge = width - abs(x + curl) + (n - 0.5) * 0.36;
      float silhouette = smoothstep(-0.035, 0.10, edge);
      // Height-dependent erosion splits the crest into moving tapered tongues.
      float tongues = smoothstep(h * 0.78, h * 0.78 + 0.18, n + (1.0 - h) * 0.23);
      float baseFade = smoothstep(0.0, 0.12, h);
      float topFade = 1.0 - smoothstep(0.90, 1.0, h);
      float density = silhouette * tongues * baseFade * topFade;
      float heat = clamp(n * 0.6 + (1.0 - h) * 0.5, 0.0, 1.0);
      vec3 color = mix(vec3(0.015, 0.13, 1.0), vec3(0.02, 0.8, 1.0),
                       smoothstep(0.25, 0.7, heat));
      color = mix(color, vec3(0.65, 0.9, 1.0), smoothstep(0.7, 1.0, heat));
      float alpha = clamp(density * uIntensity * 0.46, 0.0, 0.85);
      if (alpha < 0.003) discard;
      gl_FragColor = vec4(color, alpha);
    }
  `;

  function createFire({THREE, coreGroup}) {
    if (!THREE || !coreGroup || !coreGroup.isObject3D) {
      throw new TypeError('JarvisFire.createFire requires THREE and coreGroup');
    }
    const geometry = new THREE.PlaneGeometry(16, 19, 1, 1);
    const meshes = [];
    const materials = [];
    let disposed = false;
    // Four planes about Y (not Z): visible from the existing orbit camera.
    // Lower edge -5, upper edge +14: flame silhouettes extend past core radius 4.5.
    for (let i = 0; i < 4; i++) {
      const material = new THREE.ShaderMaterial({
        vertexShader, fragmentShader,
        uniforms: {
          uTime: {value: 0}, uSpeed: {value: 1},
          uIntensity: {value: 1}, uSeed: {value: i * 7.31}
        },
        transparent: true, side: THREE.DoubleSide,
        depthWrite: false, depthTest: true, blending: THREE.AdditiveBlending
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.name = 'jarvis-fire-tongues-' + i;
      mesh.position.y = 4.5;
      mesh.rotation.y = i * Math.PI / 4;
      // Draw after the transparent core; retain depth testing against opaque objects.
      mesh.renderOrder = 2;
      coreGroup.add(mesh);
      meshes.push(mesh); materials.push(material);
    }
    return {
      update(delta) {
        if (disposed || !Number.isFinite(delta) || delta <= 0) return;
        // Bound tab-resume jumps; time is caller-driven, never a private RAF.
        const step = Math.min(delta, 0.1);
        materials.forEach(m => { m.uniforms.uTime.value += step; });
      },
      setState(state = {}) {
        if (disposed || !state) return;
        materials.forEach(m => {
          if (Number.isFinite(state.intensity)) m.uniforms.uIntensity.value = Math.max(0, Math.min(2, state.intensity));
          if (Number.isFinite(state.speed)) m.uniforms.uSpeed.value = Math.max(0, Math.min(3, state.speed));
        });
      },
      dispose() {
        if (disposed) return;
        disposed = true;
        meshes.forEach(m => { if (m.parent) m.parent.remove(m); });
        geometry.dispose();
        materials.forEach(m => m.dispose());
      }
    };
  }
  root.JarvisFire = Object.freeze({createFire});
})(typeof window !== 'undefined' ? window : globalThis);
