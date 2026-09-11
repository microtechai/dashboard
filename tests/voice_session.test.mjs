import {test} from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
test('explicit start only; late permission stopped after shutdown; no automatic restart',async()=>{
 assert.ok(fs.existsSync(new URL('../chat/voice/session.mjs',import.meta.url)),'continuous session required');
 const {ContinuousVoice}=await import('../chat/voice/session.mjs');let calls=0,resolve,stops=0;
 const v=new ContinuousVoice({getStream:()=>{calls++;return new Promise(r=>resolve=r);}});
 assert.equal(calls,0);const pending=v.start();assert.equal(calls,1);v.shutdown();
 resolve({getTracks:()=>[{stop:()=>stops++}]});await pending;assert.equal(stops,1);assert.equal(v.active,false);assert.equal(calls,1);
});
test('pending permission deadline fails closed and late stream is stopped',async()=>{
 const {ContinuousVoice}=await import('../chat/voice/session.mjs');const real=globalThis.setTimeout;let expire,resolve,stops=0,errors=0;
 globalThis.setTimeout=fn=>{expire=fn;return 0;};
 try{const v=new ContinuousVoice({getStream:()=>new Promise(r=>resolve=r),onError:()=>errors++});const pending=v.start();expire();assert.equal(errors,1);resolve({getTracks:()=>[{stop:()=>stops++}]});await pending;assert.equal(stops,1);assert.equal(v.pending,false);}
 finally{globalThis.setTimeout=real;}
});
