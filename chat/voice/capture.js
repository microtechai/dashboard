/* Bounded PCM transport: ACK only after sequential ONNX inference. No audible output. */
class Capture extends AudioWorkletProcessor {
 constructor(){super();this.frame=new Float32Array(512);this.pos=0;this.phase=0;this.sum=0;this.count=0;this.pending=0;this.failed=false;this.port.onmessage=()=>{this.pending=Math.max(0,this.pending-1);};}
 process(inputs){
  if(this.failed)return false;
  const input=inputs[0]?.[0];if(!input)return true;
  for(const value of input){
   this.sum+=value;this.count++;this.phase+=16000;
   if(this.phase>=sampleRate){this.phase-=sampleRate;this.frame[this.pos++]=this.sum/this.count;this.sum=0;this.count=0;}
   if(this.pos===512){
    if(this.pending>=16){this.failed=true;this.port.postMessage({type:'error',message:'VAD sobrecargado. Usa Hablar.'});return false;}
    this.pending++;this.port.postMessage({type:'frame',frame:this.frame},[this.frame.buffer]);this.frame=new Float32Array(512);this.pos=0;
   }
  }return true;
 }
}
registerProcessor('jarvis-pcm',Capture);
