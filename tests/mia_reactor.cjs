const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const T=require('./vendor/three-r128.cjs');
test('viewport pixel budget bounds buffer cost without changing CSS or input coordinates',()=>{
 const html=fs.readFileSync('index.html','utf8');
 const source=html.match(/function miaPixelRatio\(width, height, dpr\) \{[\s\S]*?\n\}/);
 assert.ok(source,'production viewport pixel budget is required');
 const context={};vm.runInNewContext(source[0],context);
 assert.equal(context.miaPixelRatio(1440,1120,1)>=.65,true);
 assert.equal(context.miaPixelRatio(1440,1120,1)<=1,true);
 assert.ok(context.miaPixelRatio(390,844,3)>=1);
 assert.ok(context.miaPixelRatio(390,844,3)<=1.5);
 assert.equal(context.miaPixelRatio(1920,1080,2)>=.65,true);
});
test('reactor owns no loop; real channels are independent, bounded, expire and dispose',()=>{
 let now=0;const handlers={};const w={performance:{now:()=>now},addEventListener:(n,f)=>handlers[n]=f,removeEventListener:n=>delete handlers[n]};
 vm.runInNewContext(fs.readFileSync('reactor/reactor.js','utf8'),{window:w,requestAnimationFrame(){throw Error('no RAF')},setTimeout(){throw Error('no timers')}});
 const parent=new T.Group(),c=w.MiaReactor.create({THREE:T,coreGroup:parent});
 handlers['mia-audio-level']({detail:{channel:'input',level:.2}});handlers['jarvis-chat-state']({detail:{state:'speaking',level:.4}});c.update(.016);
 assert.equal(c.levels.input,0);assert.equal(c.levels.output,.4);
 handlers['jarvis-chat-state']({detail:{state:'idle',level:0}});c.update(.016);assert.equal(c.levels.input,0);assert.equal(c.levels.output,0);
 handlers['jarvis-chat-state']({detail:{state:'listening',level:.3,micActive:true}});c.update(.016);assert.equal(c.levels.input,.3);
 handlers['jarvis-chat-state']({detail:{state:'thinking',level:0,micActive:false}});c.update(.016);assert.equal(c.levels.input,0);
 handlers['mia-audio-level']({detail:{channel:'input',level:NaN}});c.update(.016);assert.equal(c.levels.input,0);assert.equal(c.levels.output,0);
 now=1001;c.update(.016);assert.equal(c.levels.output,0);
 const count=parent.children.length;for(let i=0;i<500;i++)c.update(.016);assert.equal(parent.children.length,count);c.dispose();c.dispose();assert.equal(parent.children.length,0);assert.equal(Object.keys(handlers).length,0);
});
