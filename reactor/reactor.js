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
    const grid = new T.GridHelper(14,28,0x00a6bd,0x09253a); grid.position.y=-4.4; grid.material.transparent=true; grid.material.opacity=.12; galaxy.add(grid);
    const aura = new T.Mesh(new T.SphereGeometry(1.05,24,16), new T.MeshBasicMaterial({color:0xd51f8f,transparent:true,opacity:.035,depthWrite:false})); aura.userData.miaCore=true; galaxy.add(aura);

    const links = [];
    const energyDots = [];
    const nodes = [];
    const hitTargets = [];
    STAGES.forEach(stage=>{
      const group = new T.Group(); group.name = 'mia-sun-'+stage.id; group.position.set(...stage.pos); group.userData.miaStage = stage.id;
      const material = new T.MeshStandardMaterial({color:stage.color,emissive:stage.color,emissiveIntensity:1.25,metalness:.25,roughness:.2});
      const sun = new T.Mesh(new T.SphereGeometry(.28,16,12), material); sun.userData.miaStage=stage.id; group.add(sun);
      const shell = new T.Mesh(new T.SphereGeometry(.37,14,10), new T.MeshBasicMaterial({color:stage.color,transparent:true,opacity:.28,depthWrite:false,blending:T.AdditiveBlending})); shell.userData.miaStage=stage.id; group.add(shell);
      const halo = new T.Mesh(new T.SphereGeometry(.52,12,8), new T.MeshBasicMaterial({color:stage.color,transparent:true,opacity:.24,depthWrite:false,blending:T.AdditiveBlending})); halo.userData.miaStage=stage.id; group.add(halo);
      const ring = new T.Mesh(new T.TorusGeometry(.46,.018,6,32), new T.MeshBasicMaterial({color:stage.color,transparent:true,opacity:.92,blending:T.AdditiveBlending})); ring.userData.miaStage=stage.id; ring.rotation.x=.8; group.add(ring);
      galaxy.add(group); hitTargets.push(sun); nodes.push({stage,group,sun,halo,ring,material,active:false});
      const lineMaterial = new T.LineBasicMaterial({color:stage.color,transparent:true,opacity:.72,blending:T.AdditiveBlending});
      const activeLineMaterial = new T.LineBasicMaterial({color:stage.color,transparent:true,opacity:1,blending:T.AdditiveBlending});
      const line = makeLine(T,[0,0,0],stage.pos,lineMaterial); line.userData.miaStage=stage.id; galaxy.add(line); links.push({line,stage,active:false,lineMaterial,activeLineMaterial});
      for(let q=0;q<3;q++){const dot = new T.Mesh(new T.SphereGeometry(.065,8,6), new T.MeshBasicMaterial({color:stage.color,transparent:true,opacity:.35,depthWrite:false,blending:T.AdditiveBlending})); dot.userData.miaStage=stage.id; galaxy.add(dot); energyDots.push({dot,stage,phase:q/3});}
    });

    const starField = new T.Points(new T.BufferGeometry(), new T.PointsMaterial({color:0x29e7ff,size:.018,transparent:true,opacity:.42}));
    const positions = new Float32Array(320*3);
    for(let i=0;i<320;i++){positions[i*3]=(Math.random()-.5)*15;positions[i*3+1]=(Math.random()-.5)*12;positions[i*3+2]=(Math.random()-.5)*8;}
    starField.geometry.setAttribute('position',new T.BufferAttribute(positions,3)); galaxy.add(starField);

    const key = new T.PointLight(0x00a6bd,2.3,14); key.position.set(-2,3,5); galaxy.add(key);
    const rim = new T.PointLight(0xd51f8f,1.2,12); rim.position.set(4,-2,-3); galaxy.add(rim);
    let time=0, disposed=false, reduced=false, selected=null, inputLevel=0, outputLevel=0, inputAt=0, outputAt=0, targetRotation=0, zoomFactor=1, targetZoom=1;

    function inputEvent(event){const detail=event.detail||{};if(detail.channel!=='input')return;inputLevel=clamp(detail.level);inputAt=root.performance.now();}
    function stateEvent(event){const detail=event.detail||{}; if(!PALETTE[detail.state])return; state=detail.state; level=clamp(detail.level); updated=root.performance.now(); if(detail.state==='listening'){inputLevel=level;inputAt=updated;} else {inputLevel=0;inputAt=0;} if(detail.state==='speaking'){outputLevel=level;outputAt=updated;} else {outputLevel=0;outputAt=0;} if(!['listening','speaking'].includes(detail.state))level=0; }
    root.addEventListener('mia-audio-level',inputEvent);
    root.addEventListener('jarvis-chat-state',stateEvent);

    function focusStage(id){
      selected=id;
      const stage=STAGES.find(item=>item.id===id);
      if(stage){targetRotation=-Math.atan2(stage.pos[1],stage.pos[0])+.35;targetZoom=1.38;}
      else {targetRotation=0;targetZoom=1;}
      nodes.forEach(n=>{n.active=n.stage.id===id;n.group.scale.setScalar(n.active?1.35:1);});
      links.forEach(l=>{l.active=l.stage.id===id;l.line.material=l.active?l.activeLineMaterial:l.lineMaterial;});
      return !id || !!stage;
    }

    const controller = {
      group: galaxy,
      hitTargets,
      stats:{paths:STAGES.length,segments:1,nodes:STAGES.length},
      get levels(){return {input:inputLevel,output:outputLevel};},
      get zoomFactor(){return zoomFactor;},
      get stageTargets(){return nodes.map(node=>({id:node.stage.id,label:node.stage.label,group:node.group,sun:node.sun}));},
      focusStage,
      setState(options={}){reduced=!!options.reducedMotion;},
      update(delta){
        if(disposed||!Number.isFinite(delta)||delta<0)return;
        const now=root.performance.now(); if(now-updated>1000)level=0; if(now-inputAt>1000)inputLevel=0; if(now-outputAt>1000)outputLevel=0;
        if(!reduced)time+=Math.min(delta,.06);
        galaxy.rotation.z += reduced?0:(targetRotation-galaxy.rotation.z)*.045;
        zoomFactor += (targetZoom-zoomFactor)*(reduced?1:.045);
        const pulse=reduced?0:(state==='thinking'?.18+Math.sin(time*4)*.06:Math.max(level,inputLevel,outputLevel));
        galaxy.rotation.z += reduced?0:delta*.018;
        starField.rotation.y = time*.008;
        core.rotation.y = time*.35;
        coreMaterial.color.setHex(PALETTE[state]||PALETTE.idle); coreMaterial.emissive.setHex(PALETTE[state]||PALETTE.idle); coreMaterial.emissiveIntensity=1.1+pulse*1.8;
        core.scale.setScalar(1+pulse*.18); coreGlow.material.opacity=.10+pulse*.12; aura.material.opacity=.025+pulse*.08; key.intensity=2.0+pulse*2.0;
        energyDots.forEach(({dot,stage,phase})=>{const t=(time*.42+STAGES.indexOf(stage)*.11+phase)%1; dot.position.set(stage.pos[0]*t,stage.pos[1]*t,stage.pos[2]*t); dot.material.opacity=selected===stage.id?.98:.35; dot.scale.setScalar(selected===stage.id?1.8:1);});
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
