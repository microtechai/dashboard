// ═══════════════════════════════════════════════════════════
// FIRE ANIMATION - Three.js Real-time Shader
// Dashboard microtechai.es - Fase 1: Fuego Realista
// ═══════════════════════════════════════════════════════════

// === FIRE VERTEX SHADER ===
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

// === FIRE FRAGMENT SHADER - Realistic Flame ===
const fireFragmentShader = `
    uniform float uTime;
    uniform vec3 uColor1;
    uniform vec3 uColor2;
    uniform vec3 uColor3;
    uniform float uSpeed;
    uniform float uIntensity;
    uniform vec2 uResolution;
    
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;
    
    // Simplex noise function (simplified 3D noise)
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
        m = m*m ;
        m = m*m ;
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
    
    // 3D noise for turbulence
    float noise3D(vec3 p) {
        vec3 i = floor(p);
        vec3 f = fract(p);
        float n = snoise(i.xy) * f.z + snoise(i.xy + vec2(5.0)) * (1.0 - f.z);
        return n;
    }
    
    void main() {
        // Normalized coordinates
        vec2 uv = vUv * 3.0; // Scale up noise
        
        // Time-based animation
        float time = uTime * uSpeed;
        
        // 3D turbulence noise
        float noiseVal = 0.0;
        noiseVal += snoise(uv * 1.0 + time * 0.3) * 0.5;
        noiseVal += snoise(uv * 2.0 + time * 0.5) * 0.25;
        noiseVal += snoise(uv * 4.0 + time * 0.8) * 0.125;
        noiseVal += noise3D(vec3(uv, time * 0.2)) * 0.1;
        
        // Distance from center
        float dist = distance(vUv, vec2(0.5));
        
        // Mask - keep within circular area
        float mask = 1.0 - smoothstep(0.35, 0.5, dist);
        
        // Flame shape - taller at center, tapering at edges
        float heightFactor = 1.0 - smoothstep(0.0, 0.45, dist);
        
        // Base noise modulation
        float fireNoise = noiseVal * heightFactor * mask;
        
        // Color gradient mapping
        float t = smoothstep(-0.2, 1.0, fireNoise + time * 0.1);
        
        // Core (yellow) -> Mid (orange) -> Edge (red)
        vec3 color = mix(uColor1, uColor2, smoothstep(0.0, 0.6, fireNoise));
        color = mix(color, uColor3, smoothstep(0.3, 0.9, fireNoise));
        
        // Add electric sparks (blue flashes)
        float spark = step(0.95, noiseVal) * (1.0 - dist) * 0.5;
        color += vec3(0.15, 0.6, 1.0) * spark;
        
        // Light emission based on intensity
        float emission = fireNoise * uIntensity * 0.8;
        color += vec3(0.5, 0.3, 0.1) * emission;
        
        // Normal-based lighting
        float normalLight = dot(vNormal, vec3(0.0, 0.0, 1.0));
        color *= (0.3 + 0.7 * normalLight);
        
        // Alpha - flame is transparent
        float alpha = mask * 0.9 * (0.3 + 0.7 * fireNoise);
        
        // Glow effect at edges
        float glow = smoothstep(0.3, 0.45, dist) * (0.2 + 0.3 * fireNoise);
        alpha += glow;
        
        gl_FragColor = vec4(color, alpha);
    }
`;

// === PARTICLE SYSTEM ===
class FireParticles {
    constructor(scene, coreGroup) {
        this.scene = scene;
        this.coreGroup = coreGroup;
        this.count = 3000;
        this.particles = [];
        this.geometry = null;
        this.material = null;
        this.mesh = null;
        this.time = 0;
        
        this.init();
    }
    
    init() {
        // Particle geometry
        this.geometry = new THREE.BufferGeometry();
        const positions = [];
        const sizes = [];
        const speeds = [];
        const lifetimes = [];
        const maxLifetimes = [];
        
        for (let i = 0; i < this.count; i++) {
            // Spawn in a disc at bottom
            const angle = Math.random() * Math.PI * 2;
            const radius = Math.random() * 2.5;
            
            positions.push(
                Math.cos(angle) * radius,
                -3.0 + Math.random() * 0.5, // Start slightly below core
                Math.sin(angle) * radius
            );
            
            sizes.push(Math.random() * 1.2 + 0.3);
            speeds.push(Math.random() * 0.3 + 0.1);
            lifetimes.push(Math.random() * 1.0 + 0.5);
            maxLifetimes.push(lifetimes[i]);
        }
        
        this.geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        this.geometry.setAttribute('aSize', new THREE.Float32BufferAttribute(sizes, 1));
        this.geometry.setAttribute('aSpeed', new THREE.Float32BufferAttribute(speeds, 1));
        this.geometry.setAttribute('aLifetime', new THREE.Float32BufferAttribute(lifetimes, 1));
        this.geometry.setAttribute('aMaxLifetime', new THREE.Float32BufferAttribute(maxLifetimes, 1));
        
        // Particle material (sprite-based)
        const texture = this.createParticleTexture();
        this.material = new THREE.PointsMaterial({
            color: 0xff6600,
            size: 1.0,
            map: texture,
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });
        
        this.mesh = new THREE.Points(this.geometry, this.material);
        this.coreGroup.add(this.mesh);
    }
    
    createParticleTexture() {
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
        
        const texture = new THREE.CanvasTexture(canvas);
        return texture;
    }
    
    update(time, delta) {
        const positions = this.geometry.attributes.position.array;
        const sizes = this.geometry.attributes.aSize.array;
        const speeds = this.geometry.attributes.aSpeed.array;
        const lifetimes = this.geometry.attributes.aLifetime.array;
        
        for (let i = 0; i < this.count; i++) {
            const x = positions[i * 3];
            const y = positions[i * 3 + 1];
            const z = positions[i * 3 + 2];
            
            // Move upward with turbulence
            lifetimes[i] -= delta * 0.5; // Decay
            
            if (lifetimes[i] <= 0) {
                // Respawn particle
                const angle = Math.random() * Math.PI * 2;
                const radius = Math.random() * 2.5;
                positions[i * 3] = Math.cos(angle) * radius;
                positions[i * 3 + 1] = -3.0 + Math.random() * 0.5;
                positions[i * 3 + 2] = Math.sin(angle) * radius;
                lifetimes[i] = 1.0;
            } else {
                // Move up with turbulence
                positions[i * 3 + 1] += speeds[i] * delta * 5;
                
                // Add turbulence
                const turbulence = Math.sin(time * 2.0 + x) * 0.1;
                positions[i * 3] += turbulence;
                positions[i * 3 + 2] += Math.cos(time * 2.0 + z) * 0.1;
                
                // Scale based on height (taller = smaller)
                const heightFactor = Math.min(1.0, (positions[i * 3 + 1] + 3) / 8);
                sizes[i] = 1.2 * (1.0 - heightFactor * 0.7);
            }
        }
        
        this.geometry.attributes.position.needsUpdate = true;
        this.geometry.attributes.aSize.needsUpdate = true;
        this.geometry.attributes.aLifetime.needsUpdate = true;
    }
    
    dispose() {
        this.geometry.dispose();
        this.material.dispose();
        this.coreGroup.remove(this.mesh);
    }
}

// === FIRE CONTROLLER ===
class FireController {
    constructor(scene, coreGroup, renderer) {
        this.scene = scene;
        this.coreGroup = coreGroup;
        this.renderer = renderer;
        
        this.fireMaterial = null;
        this.fireMesh = null;
        this.fireLight = null;
        this.particles = null;
        
        this.time = 0;
        this.isInitialized = false;
    }
    
    init() {
        if (this.isInitialized) return;
        
        // Create fire shader material
        this.fireMaterial = new THREE.ShaderMaterial({
            vertexShader: fireVertexShader,
            fragmentShader: fireFragmentShader,
            uniforms: {
                uTime: { value: 0 },
                uColor1: { value: new THREE.Color(0xffcc00) }, // Yellow
                uColor2: { value: new THREE.Color(0xff6600) }, // Orange
                uColor3: { value: new THREE.Color(0xff0000) }, // Red
                uSpeed: { value: 2.5 },
                uIntensity: { value: 1.8 },
                uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) }
            },
            transparent: true,
            side: THREE.DoubleSide,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });
        
        // Create fire mesh
        this.fireMesh = new THREE.Mesh(new THREE.SphereGeometry(4.5, 64, 64), this.fireMaterial);
        this.coreGroup.add(this.fireMesh);
        
        // Fire light (orange)
        this.fireLight = new THREE.PointLight(0xff6600, 6, 200);
        this.fireLight.position.set(0, 0, 0);
        this.coreGroup.add(this.fireLight);
        
        // Electric light (blue sparks)
        this.electricLight = new THREE.PointLight(0x00ccff, 3, 150);
        this.electricLight.position.set(3, 3, 3);
        this.coreGroup.add(this.electricLight);
        
        // Initialize particles
        this.particles = new FireParticles(this.scene, this.coreGroup);
        
        this.isInitialized = true;
        
        console.log('✅ Fire animation initialized');
    }
    
    update(delta, time) {
        this.time += delta;
        
        if (this.isInitialized) {
            // Update shader uniform
            if (this.fireMaterial) {
                this.fireMaterial.uniforms.uTime.value = this.time;
            }
            
            // Update particles
            if (this.particles) {
                this.particles.update(this.time, delta);
            }
            
            // Rotate core group slightly for more dynamic effect
            this.coreGroup.rotation.y = Math.sin(time * 0.3) * 0.1;
            this.coreGroup.rotation.z = Math.cos(time * 0.2) * 0.05;
        }
    }
    
    resize(width, height) {
        if (this.fireMaterial) {
            this.fireMaterial.uniforms.uResolution.value.set(width, height);
        }
    }
    
    dispose() {
        if (this.fireMesh) {
            this.coreGroup.remove(this.fireMesh);
            this.fireMesh.geometry.dispose();
            this.fireMesh.material.dispose();
        }
        if (this.fireLight) {
            this.coreGroup.remove(this.fireLight);
        }
        if (this.electricLight) {
            this.coreGroup.remove(this.electricLight);
        }
        if (this.particles) {
            this.particles.dispose();
        }
    }
}

// Export for use in main script
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FireController;
}
