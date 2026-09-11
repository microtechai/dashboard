import {test} from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import vm from 'node:vm';
test('worker rejects fifth queued frame rather than overlap or accumulate inference',async()=>{
 const f=new URL('../chat/voice/worker.js',import.meta.url);assert.ok(fs.existsSync(f),'sequential ONNX worker required');
 const out=[];const self={postMessage:m=>out.push(m)};let resolve;let runs=0;
 class Tensor {constructor(t,data){this.data=data;}dispose(){}}
 const ort={env:{wasm:{}},Tensor,InferenceSession:{create:async()=>({run:()=>{runs++;return new Promise(r=>resolve=r);}})}};
 vm.runInNewContext(fs.readFileSync(f,'utf8'),{self,importScripts:()=>{},ort,URL,location:{href:'http://localhost/chat/voice/worker.js'},Float32Array,BigInt64Array,Number,Error});
 await self.onmessage({data:{type:'init'}});assert.equal(out[0].type,'ready');
 for(let i=0;i<6;i++)self.onmessage({data:{type:'frame',frame:new Float32Array(512)}});
 assert.equal(runs,1);assert.equal(out.filter(m=>m.type==='error').length,1);
 resolve({stateN:new Tensor('',[]),output:new Tensor('',[.9])});await new Promise(r=>setTimeout(r,0));
 assert.equal(out.filter(m=>m.type==='frame').length,0);
});
