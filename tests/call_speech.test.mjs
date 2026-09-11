import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
test('ordered bounded speech queue starts early and double cancel drops stale requests',async()=>{
 const {SpeechQueue}=await import('../chat/voice/speech.mjs');assert.equal(typeof SpeechQueue,'function');
 let release;const sent=[],stops=[],errors=[],limits=[];
 const q=new SpeechQueue({play:(text,signal)=>{sent.push({text,signal});return new Promise(r=>release=r);},stop:()=>stops.push(1),onError:e=>errors.push(e),onLimit:()=>limits.push(1)});
 q.push('Primera frase. Segunda'); await new Promise(r=>setImmediate(r));assert.equal(sent[0].text,'Primera frase.');
 q.push(' frase. '+('Texto bastante largo completo. '.repeat(180)),true);
 assert.ok(q.queue.length<=2);assert.ok(q.queue.every(x=>x.length<=1000));assert.equal(limits.length,1);
 q.cancel();q.cancel();assert.equal(sent[0].signal.aborted,true);assert.equal(q.queue.length,0);assert.equal(stops.length,2);
 release();await new Promise(r=>setImmediate(r));assert.equal(sent.length,1);assert.deepEqual(errors,[]);
});
test('TTS network error and 429 cancel without retry',async()=>{
 const {SpeechQueue}=await import('../chat/voice/speech.mjs');assert.equal(typeof SpeechQueue,'function');
 for(const status of [429,503]){let calls=0,errors=0;
 const q=new SpeechQueue({play:async()=>{calls++;throw Object.assign(Error('fixture'),{status});},onError:()=>errors++});
 q.push('Primero. Segundo. Tercero.',true);await new Promise(r=>setImmediate(r));q.push('No reenviar.',true);
 assert.equal(calls,1);assert.equal(errors,1);assert.equal(q.queue.length,0);}
});
test('sentence boundaries wait for lookahead and preserve decimal/abbreviation',async()=>{
 const {SentenceBuffer}=await import('../chat/voice/speech.mjs');
 assert.equal(typeof SentenceBuffer,'function');
 const s=new SentenceBuffer();
 assert.deepEqual(s.push('El Sr. Pérez paga 3.'),[]);
 assert.deepEqual(s.push('14 euros. Otra'),['El Sr. Pérez paga 3.14 euros.']);
 assert.deepEqual(s.push(' frase! Fin',true),['Otra frase!','Fin']);
 const a=new SentenceBuffer(); assert.deepEqual(a.push('P. ej. usa 2.5. Sí.',true),['P. ej. usa 2.5.','Sí.']);
});
test('speech normalizes decorative Markdown without deleting numbers or code operators',async()=>{
 assert.ok(fs.existsSync(new URL('../chat/voice/speech.mjs',import.meta.url)),'speech normalization module required');
 const {normalizeSpeech}=await import('../chat/voice/speech.mjs');
 assert.equal(normalizeSpeech('## 🟦 Estado\n**Precio**: 3.14 €, -5% y C++.\n`x < 3 && y > 2`'),'Estado Precio: 3.14 €, -5% y C++. x < 3 && y > 2');
 assert.equal(normalizeSpeech('[Manual](https://example.com) y ![decoración](x)'), 'Manual y');
 assert.equal(normalizeSpeech('Usa icono, icon y symbols. 1️⃣ es uno; 👍 significa sí.'),'Usa icono, icon y symbols. es uno; significa sí.');
 assert.equal(normalizeSpeech('Hola 👩🏽‍💻 mundo 🇪🇸 🏳️‍🌈 2️⃣ #️⃣ *️⃣ ❤️ ☀︎ 🫠 fin'),'Hola mundo fin');
 assert.equal(normalizeSpeech('3.14 € $ £ ¥ −5% π × ÷ ± ∑ ∞ ≤ ≥ = + 42 # * C++ © texto'),'3.14 € $ £ ¥ −5% π × ÷ ± ∑ ∞ ≤ ≥ = + 42 # * C++ texto');
 assert.equal(normalizeSpeech('A\uFE0FB\u200DC\u{E0067}\u{E007F}D'), 'ABCD');
 assert.equal(normalizeSpeech('<img src=x onerror=alert(1)>'),' <img src=x onerror=alert(1)>'.trim());
});
