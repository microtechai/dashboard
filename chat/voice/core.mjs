// PCM frames at 16 kHz / 512 samples (32 ms). Fixed 20-second utterance budget.
export function wav16(samples) {
 if(samples.length>320000) throw new Error('20 second cap');
 const out=new ArrayBuffer(44+samples.length*2),d=new DataView(out);
 const str=(o,s)=>[...s].forEach((c,i)=>d.setUint8(o+i,c.charCodeAt(0)));
 str(0,'RIFF');d.setUint32(4,out.byteLength-8,true);str(8,'WAVE');str(12,'fmt ');
 d.setUint32(16,16,true);d.setUint16(20,1,true);d.setUint16(22,1,true);
 d.setUint32(24,16000,true);d.setUint32(28,32000,true);d.setUint16(32,2,true);d.setUint16(34,16,true);
 str(36,'data');d.setUint32(40,samples.length*2,true);
 samples.forEach((s,i)=>{s=Number.isFinite(s)?Math.max(-1,Math.min(1,s)):0;d.setInt16(44+i*2,Math.round(s*(s<0?32768:32767)),true);});
 return out;
}
export class Segmenter {
 constructor(emit=()=>{}) {this.emit=emit;this.reset();}
 reset() {this.ring=[];this.buffer=null;this.active=false;this.positive=0;this.quiet=0;this.total=0;this.blocked=false;}
 push(frame,p) {
  if(frame.length!==512) throw new Error('Expected 512 samples at 16 kHz');
  if(this.blocked) {this.quiet=p<.35?this.quiet+1:0;if(this.quiet>=22)this.reset();return;}
  frame=frame.slice();
  if(!this.active) {
   this.ring.push(frame);if(this.ring.length>16)this.ring.shift(); // 512 ms including confirmation
   this.positive=p>=.65?this.positive+1:0;
   if(this.positive<3)return; // 96 ms evidence; NOT guaranteed end-to-end latency
   this.active=true;this.buffer=new Float32Array(320000);this.total=0;
   for(const f of this.ring){this.buffer.set(f,this.total);this.total+=f.length;}this.ring=[];
   this.emit({type:'start'});return;
  }
  const n=Math.min(frame.length,320000-this.total);this.buffer.set(frame.subarray(0,n),this.total);this.total+=n;
  this.quiet=p<.35?this.quiet+1:0;
  if(this.total===320000 || this.quiet>=22) {
   const samples=this.buffer.subarray(0,this.total);
   const reason=this.total===320000?'limit':'silence';this.reset();this.blocked=reason==='limit';
   this.emit({type:'end',reason,samples,wav:wav16(samples)});
  }
 }
}
