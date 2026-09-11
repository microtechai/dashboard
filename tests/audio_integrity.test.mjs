import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeSpeech,SpeechQueue} from '../chat/voice/speech.mjs';
test('emoji between words leaves a spoken boundary, not a fused word',()=>{
 assert.equal(normalizeSpeech('Buenos👩🏽‍💻días. Revisa🇪🇸mañana. 10❤️25.'),'Buenos días. Revisa mañana. 10 25.');
});
test('a long sentence within the request budget retains every whole word',async()=>{
 const original='Inicio '+('palabra '.repeat(150))+'final.';
 const sent=[];let limited=0;
 const q=new SpeechQueue({play:async text=>sent.push(text),onLimit:()=>limited++});
 q.push(original,true);await new Promise(r=>setImmediate(r));
 assert.equal(sent.join(' '),original);assert.equal(limited,0);
 assert.ok(sent.every(text=>text.length<=1000));assert.ok(sent.length<=3);
});
test('stream partitions preserve final words, decimals and Unicode spaces',async()=>{
 const original='El Sr. Pérez paga 3.14 euros, −5% y 42 mensajes. Buenos\u00a0días. Última palabra naranja.';
 for(const size of [1,7,31,original.length]){
  const sent=[];const q=new SpeechQueue({play:async text=>sent.push(text)});
  for(let i=0;i<original.length;i+=size)q.push(original.slice(i,i+size));q.push('',true);
  await new Promise(r=>setImmediate(r));assert.equal(sent.join(' '),normalizeSpeech(original));
 }
});
test('over-budget output warns once and never synthesizes half a word',async()=>{
 for(const original of ['palabra '.repeat(600),'x'.repeat(1001)]){
  const sent=[];let limited=0;const q=new SpeechQueue({play:async text=>sent.push(text),onLimit:()=>limited++});
  q.push(original,true);q.push('Nunca.',true);await new Promise(r=>setImmediate(r));
  assert.equal(limited,1);assert.ok(sent.length<=3);assert.ok(sent.every(x=>x.length<=1000));
  if(sent.length)assert.ok(sent.every(x=>x.split(' ').every(w=>w==='palabra')));
 }
});
