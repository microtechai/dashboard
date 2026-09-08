// JARVIS blue combustion volume, Three.js r128. No private loop/network assets.
(function (root) {
  'use strict';
  const vertexShader = `
    varying vec3 vPosition;
    void main() {
      vPosition = position;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `;
  const fragmentShader = `
    uniform vec3 uCamera;
    uniform sampler2D uNoise;
    uniform float uTime, uSpeed, uIntensity, uSteps;
    varying vec3 vPosition;
    float noise(vec3 p) {
      vec3 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
      // RG contains adjacent Z slices. Hardware bilinear + Z interpolation:
      // one fetch instead of eight procedural hashes, with continuous cell edges.
      vec2 uv=i.xy+vec2(37.0,17.0)*i.z+f.xy;
      vec2 slices=texture2D(uNoise,(uv+0.5)/256.0).rg;
      return mix(slices.r,slices.g,f.z);
    }
    float turbulence(vec3 p) {
      return noise(p)*0.57 + noise(p*2.07+7.1)*0.29 + noise(p*4.13+19.7)*0.14;
    }
    void main() {
      vec3 rd=normalize(vPosition-uCamera);
      // Signed epsilon: stable slab intersection for axis-aligned rays.
      vec3 safe=sign(rd)*max(abs(rd),vec3(0.00001));
      safe += (vec3(1.0)-abs(sign(rd)))*0.00001;
      vec3 a=(-vec3(1.0)-uCamera)/safe, b=(vec3(1.0)-uCamera)/safe;
      vec3 nearV=min(a,b), farV=max(a,b);
      float nearT=max(max(nearV.x,nearV.y),nearV.z);
      float farT=min(min(farV.x,farV.y),farV.z);
      nearT=max(nearT,0.0);
      if(farT<=nearT) discard;
      float dt=(farT-nearT)/uSteps;
      // Fixed pixel dither removes marching bands without temporal sparkle.
      float jitter=0.5+0.15*(fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233)))*43758.5453)-0.5);
      vec4 sum=vec4(0.0);
      float t=uTime;
      for(int i=0;i<48;i++) {
        if(float(i)>=uSteps || sum.a>0.97) break;
        vec3 p=uCamera+rd*(nearT+(float(i)+jitter)*dt);
        float h=(p.y+1.0)*0.5;
        vec2 center=vec2(sin(h*7.0-t*0.65),cos(h*5.0+t*0.5))*h*h*0.17;
        float r=length(p.xz-center);
        float width=0.67*pow(max(1.0-h,0.0),0.72);
        // Conservative density support: avoid all noise fetches in empty space.
        if(h<0.04 || h>0.99 || r>width+0.52*(0.38+0.3*h)+0.025) continue;
        vec3 q=p*vec3(3.7,4.6,3.7)-vec3(0,t*1.25,0);
        float warp=noise(q*0.56+vec3(t*0.1,0,-t*0.08));
        float n=turbulence(q+vec3(warp*1.7,0,warp*0.9));
        float shape=width-r+(n-0.48)*(0.38+0.3*h);
        float envelope=smoothstep(-0.025,0.07,shape)*smoothstep(0.04,0.20,h)*(1.0-smoothstep(0.87,0.99,h));
        float crest=smoothstep(h*0.68,h*0.68+0.13,n);
        // Thin folded sheets throughout the volume, not a solid glowing ball.
        float sheet=pow(max(1.0-abs(n-0.52)*7.0,0.0),3.0);
        float density=envelope*crest*(0.13+sheet*1.9);
        float heat=clamp(sheet*0.8+(1.0-h)*0.16,0.0,1.0);
        vec3 color=mix(vec3(0.018,0.12,1.0),vec3(0.04,0.85,1.5),heat);
        color=mix(color,vec3(0.20,0.78,1.0),pow(heat,12.0)*0.6);
        float alpha=1.0-exp(-density*dt*4.2*uIntensity);
        sum.rgb+=(1.0-sum.a)*alpha*color;
        sum.a+=(1.0-sum.a)*alpha;
      }
      if(sum.a<0.003) discard;
      // Straight alpha for NormalBlending (no additive cyan clipping).
      gl_FragColor=vec4(sum.rgb/max(sum.a,0.001),sum.a);
    }
  `;
  function createFire({THREE, coreGroup, quality='auto'}) {
    if (!THREE || !coreGroup || !coreGroup.isObject3D) throw new TypeError('JarvisFire.createFire requires THREE and coreGroup');
    const values=new Uint8Array(256*256), data=new Uint8Array(256*256*4);
    let seed=0x6d2b79f5;
    for(let i=0;i<values.length;i++) {seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;values[i]=seed>>>24;}
    for(let y=0;y<256;y++) for(let x=0;x<256;x++) {
      const j=(y*256+x)*4;data[j]=values[y*256+x];data[j+1]=values[((y+17)&255)*256+((x+37)&255)];data[j+3]=255;
    }
    const noiseTexture=new THREE.DataTexture(data,256,256,THREE.RGBAFormat);
    noiseTexture.wrapS=noiseTexture.wrapT=THREE.RepeatWrapping;
    noiseTexture.minFilter=noiseTexture.magFilter=THREE.LinearFilter;
    noiseTexture.generateMipmaps=false;noiseTexture.needsUpdate=true;
    const geometry=new THREE.BoxGeometry(2,2,2);
    const material=new THREE.ShaderMaterial({vertexShader,fragmentShader,
      uniforms:{uNoise:{value:noiseTexture},uCamera:{value:new THREE.Vector3()},uTime:{value:0},uSpeed:{value:1},uIntensity:{value:1},uSteps:{value:40}},
      transparent:true,side:THREE.BackSide,depthWrite:false,depthTest:true,blending:THREE.NormalBlending});
    const mesh=new THREE.Mesh(geometry,material);
    mesh.name='jarvis-fire-volume';mesh.scale.set(9,13,9);mesh.position.y=5;mesh.renderOrder=2;
    const inverse=new THREE.Matrix4();
    mesh.onBeforeRender=function(renderer,scene,camera) {
      inverse.copy(mesh.matrixWorld).invert();
      material.uniforms.uCamera.value.setFromMatrixPosition(camera.matrixWorld).applyMatrix4(inverse);
    };
    coreGroup.add(mesh);
    let disposed=false, reducedMotion=false, targetIntensity=1, targetSpeed=1;
    let averageDelta=1/60, slowFrames=0, fastFrames=0;
    material.uniforms.uSteps.value=quality==='low'?24:40;
    return {
      update(delta) {
        if(disposed || !Number.isFinite(delta) || delta<=0) return;
        const step=Math.min(delta,0.1), u=material.uniforms;
        const ease=1-Math.exp(-step*5);
        u.uIntensity.value+=(targetIntensity-u.uIntensity.value)*ease;
        u.uSpeed.value+=(targetSpeed-u.uSpeed.value)*ease;
        u.uTime.value+=step*(reducedMotion?Math.min(u.uSpeed.value,0.2):u.uSpeed.value);
        // Ignore tab-resume outliers; caller frame pressure is a conservative proxy,
        // not a claim to measure GPU time. Hysteresis avoids quality thrashing.
        if(delta<1) {
          averageDelta+=(step-averageDelta)*0.06;
          slowFrames=averageDelta>0.028?slowFrames+1:0;
          fastFrames=averageDelta<0.019?fastFrames+1:0;
        }
        if(reducedMotion || quality==='low' || slowFrames>45) u.uSteps.value=24;
        else if(fastFrames>240) u.uSteps.value=40;
      },
      setState(state={}) {
        if(disposed || !state) return;
        if(Number.isFinite(state.intensity)) targetIntensity=Math.max(0,Math.min(2,state.intensity));
        if(Number.isFinite(state.speed)) targetSpeed=Math.max(0,Math.min(3,state.speed));
        if(typeof state.reducedMotion==='boolean') reducedMotion=state.reducedMotion;
      },
      dispose() {
        if(disposed) return;disposed=true;
        if(mesh.parent) mesh.parent.remove(mesh);geometry.dispose();material.dispose();noiseTexture.dispose();
      }
    };
  }
  root.JarvisFire=Object.freeze({createFire});
})(typeof window!=='undefined'?window:globalThis);
