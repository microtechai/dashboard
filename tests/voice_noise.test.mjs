import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Segmenter} from '../chat/voice/core.mjs';
const f=level=>new Float32Array(512).fill(level);
test('neural false positives at noise floor and short knocks do not interrupt; voice twice retains onset',()=>{
 const events=[],s=new Segmenter(e=>events.push(e));
 // Probabilities are deterministic classifier seam fixtures, NOT an ONNX benchmark.
 for(let i=0;i<100;i++)s.push(f(.008),.05);
 for(let i=0;i<10;i++)s.push(f(.009),.92);
 assert.equal(events.length,0,'false neural confidence at learned noise floor must not barge in');
 for(let j=0;j<3;j++){for(let i=0;i<3;i++)s.push(f(.4),.99);for(let i=0;i<25;i++)s.push(f(.008),.05);}
 assert.equal(events.length,0,'96ms impact bursts must not barge in');
 for(let turn=0;turn<2;turn++){
  s.push(f(.012),.4); // onset retained, not enough by itself to interrupt
  for(let i=0;i<4;i++)s.push(f(.08),.95);
  assert.equal(events.filter(e=>e.type==='start').length,turn+1,'voice interrupts within 128ms classifier evidence');
  for(let i=0;i<22;i++)s.push(f(.008),.05);
  const end=events.at(-1);assert.equal(end.type,'end');assert.ok(end.samples.some(x=>Math.abs(x-.012)<.00001),'first syllable pre-roll preserved');
 }
});
