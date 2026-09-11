import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {SpeechQueue} from '../chat/voice/speech.mjs';
test('manual read sends complete message to bounded queue, never silently slices',()=>{
 const source=fs.readFileSync(new URL('../chat/chat.js',import.meta.url),'utf8');
 assert.ok(!source.includes('speech.push(text.slice('),'manual read must report long input, not silently truncate');
 const q=new SpeechQueue({play:async()=>{throw Error('must not synthesize oversized input')}});
 assert.throws(()=>q.push('x'.repeat(32001),true),/demasiado larga/);
});
