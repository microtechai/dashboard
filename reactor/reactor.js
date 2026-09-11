/* Microtech AI / MIA — dark cyberpunk galaxy reactor candidate.
 * Owns scene objects and state only. The host owns the single RAF and audio.
 */
(function (root) {
  'use strict';
  const STAGES = [
    {id:'idea', label:'IDEA', color:0xd7a63a, pos:[-3.8,-1.4,1.0]},
    {id:'analysis', label:'ANÁLISIS', color:0x00a6bd, pos:[-2.2,2.8,-.6]},
    {id:'proposal', label:'PROPUESTA', color:0xd51f8f, pos:[1.2,3.1,-1.4]},
    {id:'client', label:'CLIENTE', color:0x7650c7, pos:[3.6,1.3,.5]},
    {id:'project', label:'PROYECTO', color:0x2fbf8a, pos:[3.0,-2.1,-.5]},
    {id:'grants', label:'SUBVENCIÓN', color:0xd56f31, pos:[-.2,-3.4,-1.0]},
    {id:'followup', label:'SEGUIMIENTO', color:0xc33a7f, pos:[-3.7,-2.7,-.4]}
  ];
  const PALETTE = {idle:0x00a6bd,listening:0x00c7d9,transcribing:0x00c7d9,thinking:0xd7a63a,speaking:0x2fbf8a};
  let state='idle', level=0, updated=0;

  function clamp(value) { return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0; }
  function color(T, hex) { return new T.Color(hex); }
  function makeLine(T, a, b, material) {
    const geometry = new T.BufferGeometry().setFromPoints([new T.Vector3(...a), new T.Vector3(...b)]);
    return new T.Line(geometry, material);
  }

  function create({THREE:T, coreGroup}) {
    const galaxy = new T.Group();
    galaxy.name = 'mia-galaxy-core';
    galaxy.scale.setScalar(10);
    coreGroup.add(galaxy);

    const coreMaterial = new T.MeshStandardMaterial({color:0x07131d, emissive:0x00a6bd, emissiveIntensity:1.4, metalness:.75, roughness:.28});
    const core = new T.Mesh(new T.IcosahedronGeometry(.52,2), coreMaterial);
    core.name = 'mia-central-star'; core.userData.miaCore = true; galaxy.add(core);

    const coreGlow = new T.Mesh(new T.SphereGeometry(.74,20,12), new T.MeshBasicMaterial({color:0x00a6bd,transparent:true,opacity:.12,depthWrite:false}));
    coreGlow.userData.miaCore = true; galaxy.add(coreGlow);

    const orbitRadii = [4.2,5.0,5.8];
    const orbitMaterials = orbitRadii.map((r,i)=>new T.MeshBasicMaterial({color:i===1?0xd51f8f:0x00a6bd,transparent:true,opacity:.22,depthWrite:false}));
    orbitRadii.forEach((radius,i)=>{
      const ring = new T.Mesh(new T.TorusGeometry(radius,.012,6,96), orbitMaterials[i]);
      ring.rotation.x = .85 + i*.16; ring.rotation.z = i*.22; ring.userData.miaOrbit = true; galaxy.add(ring);
    });

    const links = [];
    const linkMaterial = new T.LineBasicMaterial({color:0x24566a,transparent:true,opacity:.42});
    const activeLinkMaterial = new T.LineBasicMaterial({color:0x00c7d9,transparent:true,opacity:.95});
    const nodes = [];
    const hitTargets = [];
    STAGES.forEach(stage=>{
      const group = new T.Group(); group.name = 'mia-sun-'+stage.id; group.position.set(...stage.pos); group.userData.miaStage = stage.id;
      const material = new T.MeshStandardMaterial({color:stage.color,emissive:stage.color,emissiveIntensity:.45,metalness:.35,roughness:.25});
      const sun = new T.Mesh(new T.SphereGeometry(.28,16,12), material); sun.userData.miaStage=stage.id; group.add(sun);
      const halo = new T.Mesh(new T.SphereGeometry(.46,12,8), new T.MeshBasicMaterial({color:stage.color,transparent:true,opacity:.12,depthWrite:false})); halo.userData.miaStage=stage.id; group.add(halo);
      const ring = new T.Mesh(new T.TorusGeometry(.42,.012,5,24), new T.MeshBasicMaterial({color:stage.color,transparent:true,opacity:.65})); ring.userData.miaStage=stage.id; ring.rotation.x=.8; group.add(ring);
      if(typeof document!=='undefined'){const labelCanvas=document.createElement('canvas'); labelCanvas.width=512; labelCanvas.height=72; const labelCtx=labelCanvas.getContext('2d'); labelCtx.font='700 28px system-ui'; labelCtx.textAlign='center'; labelCtx.fillStyle='#d9f7ff'; labelCtx.shadowColor='#00a6bd'; labelCtx.shadowBlur=10; labelCtx.fillText(stage.label,256,38); const label=new T.Sprite(new T.SpriteMaterial({map:new T.CanvasTexture(labelCanvas),transparent:true,depthTest:false})); label.scale.set(1.7,.24,1); label.position.set(0,-.55,.05); label.userData.miaStage=stage.id; group.add(label);}
      galaxy.add(group); hitTargets.push(sun); nodes.push({stage,group,sun,halo,ring,material,active:false});
      const line = makeLine(T,[0,0,0],stage.pos,linkMaterial); line.userData.miaStage=stage.id; galaxy.add(line); links.push({line,stage,active:false});
    });

    const starField = new T.Points(new T.BufferGeometry(), new T.PointsMaterial({color:0x29e7ff,size:.018,transparent:true,opacity:.42}));
    const positions = new Float32Array(180*3);
    for(let i=0;i<180;i++){positions[i*3]=(Math.random()-.5)*15;positions[i*3+1]=(Math.random()-.5)*12;positions[i*3+2]=(Math.random()-.5)*8;}
    starField.geometry.setAttribute('position',new T.BufferAttribute(positions,3)); galaxy.add(starField);

    const key = new T.PointLight(0x00a6bd,2.3,14); key.position.set(-2,3,5); galaxy.add(key);
    const rim = new T.PointLight(0xd51f8f,1.2,12); rim.position.set(4,-2,-3); galaxy.add(rim);
    let time=0, disposed=false, reduced=false, selected=null, inputLevel=0, outputLevel=0, inputAt=0, outputAt=0;

    function inputEvent(event){const detail=event.detail||{};if(detail.channel!=='input')return;inputLevel=clamp(detail.level);inputAt=root.performance.now();}
    function stateEvent(event){const detail=event.detail||{}; if(!PALETTE[detail.state])return; state=detail.state; level=clamp(detail.level); updated=root.performance.now(); if(detail.state==='listening'){inputLevel=level;inputAt=updated;} else {inputLevel=0;inputAt=0;} if(detail.state==='speaking'){outputLevel=level;outputAt=updated;} else {outputLevel=0;outputAt=0;} if(!['listening','speaking'].includes(detail.state))level=0; }
    root.addEventListener('mia-audio-level',inputEvent);
    root.addEventListener('jarvis-chat-state',stateEvent);

    function focusStage(id){
      selected=id;
      nodes.forEach(n=>{n.active=n.stage.id===id;n.group.scale.setScalar(n.active?1.35:1);});
      links.forEach(l=>{l.active=l.stage.id===id;l.line.material=l.active?activeLinkMaterial:linkMaterial;});
      return STAGES.some(s=>s.id===id);
    }

    const controller = {
      group: galaxy,
      hitTargets,
      stats:{paths:STAGES.length,segments:1,nodes:STAGES.length},
      get levels(){return {input:inputLevel,output:outputLevel};},
      focusStage,
      setState(options={}){reduced=!!options.reducedMotion;},
      update(delta){
        if(disposed||!Number.isFinite(delta)||delta<0)return;
        const now=root.performance.now(); if(now-updated>1000)level=0; if(now-inputAt>1000)inputLevel=0; if(now-outputAt>1000)outputLevel=0;
        if(!reduced)time+=Math.min(delta,.06);
        const pulse=reduced?0:(state==='thinking'?.18+Math.sin(time*4)*.06:Math.max(level,inputLevel,outputLevel));
        galaxy.rotation.z += reduced?0:delta*.018;
        starField.rotation.y = time*.008;
        core.rotation.y = time*.35;
        coreMaterial.color.setHex(PALETTE[state]||PALETTE.idle); coreMaterial.emissive.setHex(PALETTE[state]||PALETTE.idle); coreMaterial.emissiveIntensity=1.1+pulse*1.8;
        core.scale.setScalar(1+pulse*.18); coreGlow.material.opacity=.10+pulse*.12; key.intensity=2.0+pulse*2.0;
        nodes.forEach(node=>{const amount=node.active?pulse*.8:0;node.material.emissiveIntensity=.35+amount;node.halo.material.opacity=node.active?.16+amount*.2:.08;node.ring.rotation.z=time*(node.active?1.4:.35);});
      },
      dispose(){
        if(disposed)return;disposed=true;root.removeEventListener('mia-audio-level',inputEvent);root.removeEventListener('jarvis-chat-state',stateEvent);
        const geometries=new Set(),materials=new Set();galaxy.traverse(object=>{if(object.geometry)geometries.add(object.geometry);if(object.material)materials.add(object.material);});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());galaxy.removeFromParent?galaxy.removeFromParent():coreGroup.remove(galaxy);
      }
    };
    return controller;
  }
  root.MiaReactor=Object.freeze({create,stages:STAGES.map(stage=>Object.freeze({...stage}))});
})(window);
