/* Fixed local versions; classic worker hosts ONNX WASM, never requests microphone. */
importScripts('./assets/ort.wasm.min.js');
ort.env.wasm.numThreads=1;ort.env.wasm.proxy=false;
ort.env.wasm.wasmPaths=new URL('./assets/',location.href).href;
let session,state,sr,running=false,failed=false,initialized=false;const queue=[];
function fail(error){if(failed)return;failed=true;queue.length=0;self.postMessage({type:'error',message:String(error.message||error)});}
async function drain(){
 if(running||failed)return;running=true;
 try{
  while(queue.length&&!failed){
   const frame=queue.shift(),input=new ort.Tensor('float32',frame,[1,512]);
   let output;
   try{output=await session.run({input,state,sr});}finally{input.dispose();}
   state.dispose();state=output.stateN;
   const probability=Number(output.output.data[0]);output.output.dispose();
   if(!Number.isFinite(probability))throw Error('VAD inválido');
   if(!failed)self.postMessage({type:'frame',frame,probability},[frame.buffer]);
  }
 }catch(e){fail(e);}finally{running=false;}
}
self.onmessage=async({data})=>{
 try{
  if(data.type==='init'){
   if(initialized)throw Error('Duplicate initialization');initialized=true;
   session=await ort.InferenceSession.create(new URL('./assets/silero_vad_v5.onnx',location.href).href,{executionProviders:['wasm']});
   state=new ort.Tensor('float32',new Float32Array(256),[2,1,128]);sr=new ort.Tensor('int64',BigInt64Array.from([16000n]),[1]);
   if(!failed)self.postMessage({type:'ready'});return;
  }
  if(failed)return;
  if(!session||data.type!=='frame'||data.frame?.length!==512)throw Error('Invalid VAD frame');
  if(queue.length+(running?1:0)>=16)throw Error('VAD sobrecargado. Usa Hablar.');
  queue.push(data.frame);void drain();
 }catch(e){fail(e);}
};
