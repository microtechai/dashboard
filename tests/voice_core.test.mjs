import {test} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
test('continuous segmentation preserves pre-roll, closes once and bounds 20 seconds',async()=>{
 assert.ok(existsSync(new URL('../chat/voice/core.mjs',import.meta.url)),'production segmenter required');
 const {Segmenter}=await import('../chat/voice/core.mjs'); const events=[]; const seg=new Segmenter(e=>events.push(e));
 for(let i=0;i<20;i++)seg.push(new Float32Array(512).fill(.01),0);
 for(let i=0;i<10;i++)seg.push(new Float32Array(512).fill(.5),.95);
 for(let i=0;i<22;i++)seg.push(new Float32Array(512),0);
 assert.equal(events.length,2);assert.ok(events[1].samples[0]<.1);
 events.length=0;for(let i=0;i<2000;i++)seg.push(new Float32Array(512),.99);
 assert.ok(seg.frames === undefined, 'do not accumulate chunks plus a second full PCM copy');
 assert.equal(events.length,2);assert.equal(events[1].samples.length,320000);assert.equal(events[1].wav.byteLength,640044);
 for(let i=0;i<100;i++)seg.push(new Float32Array(512),0);
 assert.equal(events.length,2);
});
