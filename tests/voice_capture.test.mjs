import {test} from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import vm from 'node:vm';
test('worklet resamples real input; bounded 512ms scheduling cushion then fails closed',()=>{
 const file=new URL('../chat/voice/capture.js',import.meta.url);assert.ok(fs.existsSync(file),'bounded worklet required');
 let Processor;const sent=[];class Base {constructor(){this.port={postMessage:m=>sent.push(m)};}}
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{AudioWorkletProcessor:Base,sampleRate:48000,registerProcessor:(n,p)=>Processor=p,Float32Array,Math});
 const p=new Processor();for(let i=0;i<220;i++)p.process([[new Float32Array(128).fill(.25)]]);
 assert.equal(sent.filter(x=>x.type==='frame').length,16);assert.equal(sent.filter(x=>x.type==='error').length,1);
 assert.equal(sent[0].frame.length,512);assert.ok(sent[0].frame.every(x=>x===.25));assert.equal(p.process([[new Float32Array(128)]]),false);
});
