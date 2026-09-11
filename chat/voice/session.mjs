import {Segmenter} from './core.mjs';
// A microphone lease, independent from response generations. Only start() asks permission.
export class ContinuousVoice {
 constructor({onStart=()=>{},onEnd=()=>{},onMic=()=>{},onLevel=()=>{},onError=()=>{},getStream=()=>navigator.mediaDevices.getUserMedia({video:false,audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true}})}={}){
  Object.assign(this,{onStart,onEnd,onMic,onLevel,onError,getStream});this.epoch=0;this.active=false;this.pending=false;
 }
 async start(){
  if(this.active||this.pending)return;
  const id=++this.epoch;this.pending=true;this.onMic('pending');
  this.timer=setTimeout(()=>this.fail(id,Error('Tiempo de espera del micrófono/VAD agotado. Usa Hablar.')),20000);
  try{
   const stream=await this.getStream();
   if(id!==this.epoch){stream.getTracks().forEach(t=>t.stop());return;}
   this.stream=stream;this.onMic('loading',stream.getAudioTracks()[0]?.getSettings());
   for(const track of stream.getTracks())track.onended=()=>this.fail(id,Error('Micrófono desconectado.'));
   this.context=new AudioContext();await this.context.resume();
   if(id!==this.epoch)return;
   if(this.context.state!=='running'||this.context.sampleRate<16000)throw Error('Audio no disponible. Usa Hablar.');
   const worker=new Worker(new URL('./worker.js',import.meta.url));this.worker=worker;
   const segmenter=new Segmenter(event=>{if(id!==this.epoch)return;if(event.type==='start')this.onStart();else this.onEnd({reason:event.reason,wav:event.wav});});this.segmenter=segmenter;
   await new Promise((resolve,reject)=>{
    this.rejectLoad=reject;worker.onerror=()=>reject(Error('No se pudo cargar VAD local. Usa Hablar.'));
    worker.onmessage=({data})=>{if(data.type==='ready')resolve();else if(data.type==='error')reject(Error(data.message));};worker.postMessage({type:'init'});
   });this.rejectLoad=null;
   if(id!==this.epoch)return;
   await this.context.audioWorklet.addModule(new URL('./capture.js',import.meta.url));
   if(id!==this.epoch)return;
   const node=new AudioWorkletNode(this.context,'jarvis-pcm',{numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[1]});this.node=node;
   this.source=this.context.createMediaStreamSource(stream);this.source.connect(node);
   // Processor outputs zeros. Mic input is NEVER copied to output/speakers.
   this.sink=this.context.createGain();this.sink.gain.value=0;node.connect(this.sink);this.sink.connect(this.context.destination);
   node.onprocessorerror=()=>this.fail(id,Error('Captura interrumpida. Usa Hablar.'));
   node.port.onmessage=({data})=>{if(id!==this.epoch)return;if(data.type==='error')this.fail(id,Error(data.message));else worker.postMessage(data,[data.frame.buffer]);};
   worker.onerror=()=>this.fail(id,Error('VAD falló. Usa Hablar.'));
   worker.onmessage=({data})=>{
    if(id!==this.epoch)return;
    if(data.type==='error'){this.fail(id,Error(data.message));return;}
    if(data.type!=='frame')return;
    clearTimeout(this.watchdog);this.watchdog=setTimeout(()=>this.fail(id,Error('VAD sin respuesta. Usa Hablar.')),2000);
    node.port.postMessage('ack');let sum=0;for(const x of data.frame)sum+=x*x;
    this.onLevel(Math.sqrt(sum/512));segmenter.push(data.frame,data.probability);
   };
   clearTimeout(this.timer);this.pending=false;this.active=true;this.onMic('active',stream.getAudioTracks()[0]?.getSettings());
   this.watchdog=setTimeout(()=>this.fail(id,Error('Captura sin respuesta. Usa Hablar.')),2000);
  }catch(error){this.fail(id,error);}
 }
 fail(id,error){if(id!==this.epoch)return;this.shutdown();this.onError(error);}
 shutdown(){
  this.epoch++;this.active=false;this.pending=false;
  this.stream?.getTracks().forEach(t=>{t.onended=null;t.stop();});this.stream=null;
  clearTimeout(this.timer);clearTimeout(this.watchdog);
  this.rejectLoad?.(Error('Sesión cerrada'));this.rejectLoad=null;
  if(this.node){this.node.port.onmessage=null;this.node.disconnect();this.node.port.close();}this.node=null;
  this.source?.disconnect();this.source=null;this.sink?.disconnect();this.sink=null;
  this.worker?.terminate();this.worker=null;this.segmenter?.reset();this.segmenter=null;
  this.context?.close().catch(()=>{});this.context=null;this.onMic('off');
 }
}
