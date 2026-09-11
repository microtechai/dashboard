// Speech is derived from message content, never DOM labels or HTML parsing.
// Emoji are omitted from speech everywhere; message display/history stay untouched.
// At most 3 synthesis requests/answer (6 answers/min => 18), one in flight.
// Keep the first complete sentence responsive; coalesce queued sentences to 1000 chars.
// Text beyond the audible budget stays visible with an explicit notice, never retried.
export class SpeechQueue {
 constructor({play,stop=()=>{},onError=()=>{},onLimit=()=>{},onIdle=()=>{}}){
  Object.assign(this,{play,stop,onError,onLimit,onIdle});this.sentences=new SentenceBuffer();
  this.queue=[];this.sent=0;this.epoch=0;this.closed=false;this.running=false;this.limited=false;
 }
 push(delta,final=false){
  if(this.closed||this.limited)return;
  for(const raw of this.sentences.push(delta,final)){
   let remaining=normalizeSpeech(raw);if(!remaining)continue;
   while(remaining){
    // Split only on existing word boundaries; retain the remainder for the next block.
    const end=remaining.length>1000?remaining.lastIndexOf(' ',1000):remaining.length;
    if(end<=0){this.limit();return;} // One oversized token: visible notice, never half a word.
    const text=remaining.slice(0,end);remaining=remaining.slice(end).trimStart();
    const last=this.queue.length-1;
    if(last>=0&&this.queue[last].length+1+text.length<=1000)this.queue[last]+=' '+text;
    else if(this.sent+this.queue.length<3)this.queue.push(text);
    else{this.limit();return;}
    // Start synchronously: an entire SSE delta may contain many sentences.
    if(!this.running)void this.pump();
   }
  }
 }
 limit(){this.limited=true;this.sentences.buffer='';this.onLimit();}
 async pump(){
  if(this.running||this.closed)return;this.running=true;const id=this.epoch;
  try{
   while(this.queue.length&&id===this.epoch&&!this.closed){
    const text=this.queue.shift();this.sent++;this.controller=new AbortController();
    await this.play(text,this.controller.signal);
   }
  }catch(error){if(id===this.epoch){this.cancel();this.onError(error);}}
  finally{if(id===this.epoch){this.running=false;this.controller=null;this.onIdle();}}
 }
 cancel(){this.epoch++;this.closed=true;this.controller?.abort();this.queue=[];this.sentences.buffer='';this.stop();}
}
export class SentenceBuffer {
 constructor(){this.buffer='';}
 push(delta,final=false){
  this.buffer+=delta;
  if(this.buffer.length>32000)throw Error('Respuesta demasiado larga.');
  const out=[]; let start=0;
  for(let i=0;i<this.buffer.length;i++){
   const c=this.buffer[i]; if(!/[.!?]/.test(c))continue;
   const next=this.buffer[i+1];
   if(!next&&!final)break;
   if(next&&!/\s/.test(next))continue;
   const prefix=this.buffer.slice(start,i+1);
   if(c==='.'&&/(?:\b(?:Sr|Sra|Srta|Dr|Dra|Ud|Uds|etc|aprox|núm|pág|ej)|\b[A-ZÁÉÍÓÚ]|\bp)\.$/iu.test(prefix))continue;
   const sentence=this.buffer.slice(start,i+1).trim();if(sentence)out.push(sentence);start=i+1;
  }
  this.buffer=this.buffer.slice(start).trimStart();
  if(final&&this.buffer){out.push(this.buffer);this.buffer='';}
  return out;
 }
}
export function normalizeSpeech(text) {
 return String(text)
  .replace(/^\s*```[^\n]*\n/gm,'').replace(/^\s*```\s*$/gm,'')
  .replace(/!\[[^\]]*\]\([^\n)]*\)/g,'')
  .replace(/\[([^\]]+)\]\([^\n)]*\)/g,'$1')
  .replace(/^\s{0,3}#{1,6}\s+/gm,'').replace(/^\s*[-*+]\s+/gm,'')
  // Remove complete keycaps before their variation selectors; plain digits stay.
  .replace(/[0-9#*]\uFE0F?\u20E3/gu,' ')
  .replace(/[\p{Extended_Pictographic}\p{Regional_Indicator}\p{Emoji_Modifier}]/gu,' ')
  .replace(/[\u200D\uFE0E\uFE0F\u20E3\u{E0020}-\u{E007F}]/gu,'')
  .replace(/\*\*([^\n]+?)\*\*/g,'$1').replace(/__([^\n]+?)__/g,'$1')
  .replace(/`([^`]+)`/g,'$1').replace(/\s+/g,' ').trim();
}
