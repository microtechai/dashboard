// ═══════════════════════════════════════════════════════════
// FIRE INTEGRATION - Dashboard microtechai.es
// Reemplaza el shader de fuego simplificado en el HTML
// ═══════════════════════════════════════════════════════════

// === FIRE VERTEX SHADER - Mejorado ===
const fireVertexShader = `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;
    
    void main() {
        vUv = uv;
        vNormal = normalize(normalMatrix * normal);
        vec4 worldPosition = modelViewMatrix * vec4(position, 1.0);
        vWorldPosition = worldPosition.xyz;
        gl_Position = projectionMatrix * worldPosition;
    }
`;

// === FIRE FRAGMENT SHADER - Realista con turbulence ===
const fireFragmentShader = `
    uniform float uTime;
    uniform vec3 uColor1;
    uniform vec3 uColor2;
    uniform vec3 uColor3;
    uniform float uSpeed;
    uniform float uIntensity;
    
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;
    
    // Perlin noise simplificado
    vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }
    
    float snoise(vec2 v) {
        const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                           -0.577350269189626, 0.024390243902439);
        vec2 i  = floor(v + dot(v, C.yy) );
        vec2 x0 = v -   i + dot(i, C.xx);
        vec2 i1;
        i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
        vec4 x12 = x0.xyxy + C.xxzz;
        x12.xy -= i1;
        i = mod289(i);
        vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
                        + i.x + vec3(0.0, i1.x, 1.0 ));
        vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
        m = m*m;
        m = m*m;
        vec3 x = 2.0 * fract(p * C.www) - 1.0;
        vec3 h = abs(x) - 0.5;
        vec3 ox = floor(x + 0.5);
        vec3 a0 = x - ox;
        m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
        vec3 g;
        g.x  = a0.x  * x0.x  + h.x  * x0.y;
        g.yz = a0.yz * x12.xz + h.yz * x12.yw;
        return 130.0 * dot(m, g);
    }
    
    float noise3D(vec3 p) {
        vec3 i = floor(p);
        vec3 f = fract(p);
        float n = snoise(i.xy) * f.z + snoise(i.xy + vec2(5.0)) * (1.0 - f.z);
        return n;
    }
    
    void main() {
        vec2 uv = vUv * 3.0;
        float time = uTime * uSpeed;
        
        // Multiple noise layers para turbulence realista
        float noiseVal = 0.0;
        noiseVal += snoise(uv * 1.0 + time * 0.3) * 0.5;
        noiseVal += snoise(uv * 2.0 + time * 0.5) * 0.25;
        noiseVal += snoise(uv * 4.0 + time * 0.8) * 0.125;
        noiseVal += noise3D(vec3(uv, time * 0.2)) * 0.1;
        
        float dist = distance(vUv, vec2(0.5));
        float mask = 1.0 - smoothstep(0.35, 0.5, dist);
        float heightFactor = 1.0 - smoothstep(0.0, 0.45, dist);
        
        float fireNoise = noiseVal * heightFactor * mask;
        float t = smoothstep(-0.2, 1.0, fireNoise + time * 0.1);
        
        vec3 color = mix(uColor1, uColor2, smoothstep(0.0, 0.6, fireNoise));
        color = mix(color, uColor3, smoothstep(0.3, 0.9, fireNoise));
        
        // Sparks eléctricos
        float spark = step(0.95, noiseVal) * (1.0 - dist) * 0.5;
        color += vec3(0.15, 0.6, 1.0) * spark;
        
        float emission = fireNoise * uIntensity * 0.8;
        color += vec3(0.5, 0.3, 0.1) * emission;
        
        float normalLight = dot(vNormal, vec3(0.0, 0.0, 1.0));
        color *= (0.3 + 0.7 * normalLight);
        
        float alpha = mask * 0.9 * (0.3 + 0.7 * fireNoise);
        float glow = smoothstep(0.3, 0.45, dist) * (0.2 + 0.3 * fireNoise);
        alpha += glow;
        
        gl_FragColor = vec4(color, alpha);
    }
`;

// === PARTICLE SYSTEM ===
const particleGeometry = new THREE.BufferGeometry();
const particleCount = 3000;
const particlePositions = [];
const particleSizes = [];
const particleSpeeds = [];
const particleLifetimes = [];
const particleMaxLifetimes = [];

// Initialize particles
for (let i = 0; i < particleCount; i++) {
    const angle = Math.random() * Math.PI * 2;
    const radius = Math.random() * 2.5;
    
    particlePositions.push(
        Math.cos(angle) * radius,
        -3.0 + Math.random() * 0.5,
        Math.sin(angle) * radius
    );
    
    particleSizes.push(Math.random() * 1.2 + 0.3);
    particleSpeeds.push(Math.random() * 0.3 + 0.1);
    particleLifetimes.push(Math.random() * 1.0 + 0.5);
    particleMaxLifetimes.push(particleLifetimes[i]);
}

particleGeometry.setAttribute('position', new THREE.Float32BufferAttribute(particlePositions, 3));
particleGeometry.setAttribute('aSize', new THREE.Float32BufferAttribute(particleSizes, 1));
particleGeometry.setAttribute('aSpeed', new THREE.Float32BufferAttribute(particleSpeeds, 1));
particleGeometry.setAttribute('aLifetime', new THREE.Float32BufferAttribute(particleLifetimes, 1));
particleGeometry.setAttribute('aMaxLifetime', new THREE.Float32BufferAttribute(particleMaxLifetimes, 1));

// Create particle texture (canvas)
function createParticleTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    
    const gradient = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
    gradient.addColorStop(0, 'rgba(255, 200, 100, 1)');
    gradient.addColorStop(0.3, 'rgba(255, 100, 0, 0.8)');
    gradient.addColorStop(0.6, 'rgba(255, 50, 0, 0.4)');
    gradient.addColorStop(1, 'rgba(255, 0, 0, 0)');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 32, 32);
    
    return new THREE.CanvasTexture(canvas);
}

const particleMaterial = new THREE.PointsMaterial({
    color: 0xff6600,
    size: 1.0,
    map: createParticleTexture(),
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending
});

const particleMesh = new THREE.Points(particleGeometry, particleMaterial);
particleMesh.position.set(0, 0, 0);

// ═══════════════════════════════════════════════════════════
// FIRE INITIALIZATION (reemplaza el código existente en lines 598-672)
// ═══════════════════════════════════════════════════════════

// Crear material de fuego con nuevo shader
const fireMaterial = new THREE.ShaderMaterial({
    vertexShader: fireVertexShader,
    fragmentShader: fireFragmentShader,
    uniforms: {
        uTime: { value: 0 },
        uColor1: { value: new THREE.Color(0xffcc00) },
        uColor2: { value: new THREE.Color(0xff6600) },
        uColor3: { value: new THREE.Color(0xff0000) },
        uSpeed: { value: 2.5 },
        uIntensity: { value: 2.0 }
    },
    transparent: true,
    side: THREE.DoubleSide,
    depthWrite: false,
    blending: THREE.AdditiveBlending
});

// Crear mesh de fuego
const fireGeo = new THREE.SphereGeometry(4.5, 64, 64);
const fireMesh = new THREE.Mesh(fireGeo, fireMaterial);
fireMesh.position.set(0, 0, 0);
coreGroup.add(fireMesh);

// Luz de fuego (naranja brillante)
const fireLight = new THREE.PointLight(0xff6600, 8, 200);
fireLight.position.set(0, 0, 0);
coreGroup.add(fireLight);

// Luz eléctrica (azul para sparks)
const electricLight = new THREE.PointLight(0x00ccff, 5, 150);
electricLight.position.set(3, 3, 3);
coreGroup.add(electricLight);

// Añadir partículas al coreGroup
coreGroup.add(particleMesh);

console.log('✅ Fuego realista inicializado con shader mejorado + partículas');

// ═══════════════════════════════════════════════════════════
// FIRE UPDATE (agregar en la función de animación principal)
// ═══════════════════════════════════════════════════════════

function updateFire(delta, time) {
    // Actualizar shader
    if (fireMaterial) {
        fireMaterial.uniforms.uTime.value = time;
    }
    
    // Actualizar partículas
    const positions = particleGeometry.attributes.position.array;
    const sizes = particleGeometry.attributes.aSize.array;
    const lifetimes = particleGeometry.attributes.aLifetime.array;
    
    for (let i = 0; i < particleCount; i++) {
        const x = positions[i * 3];
        const y = positions[i * 3 + 1];
        const z = positions[i * 3 + 2];
        
        lifetimes[i] -= delta * 0.5;
        
        if (lifetimes[i] <= 0) {
            // Respawn
            const angle = Math.random() * Math.PI * 2;
            const radius = Math.random() * 2.5;
            positions[i * 3] = Math.cos(angle) * radius;
            positions[i * 3 + 1] = -3.0 + Math.random() * 0.5;
            positions[i * 3 + 2] = Math.sin(angle) * radius;
            lifetimes[i] = 1.0;
        } else {
            // Mover hacia arriba con turbulence
            positions[i * 3 + 1] += particleSpeeds[i] * delta * 5;
            positions[i * 3] += Math.sin(time * 2.0 + x) * 0.1;
            positions[i * 3 + 2] += Math.cos(time * 2.0 + z) * 0.1;
            
            // Escalar según altura
            const heightFactor = Math.min(1.0, (positions[i * 3 + 1] + 3) / 8);
            sizes[i] = 1.2 * (1.0 - heightFactor * 0.7);
        }
    }
    
    particleGeometry.attributes.position.needsUpdate = true;
    particleGeometry.attributes.aSize.needsUpdate = true;
    particleGeometry.attributes.aLifetime.needsUpdate = true;
    
    // Rotación dinámica del coreGroup
    coreGroup.rotation.y = Math.sin(time * 0.3) * 0.1;
    coreGroup.rotation.z = Math.cos(time * 0.2) * 0.05;
}
