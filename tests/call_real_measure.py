"""Real private local CPU STT/Piper and existing Qwen review, no public auth bypass.
One model request only, skipped if live metrics indicate another request. No credentials.
This is a heavy code-review benchmark, NOT owner mic/HTTP end-to-end latency.
"""
from pathlib import Path
import subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/call';OUT.mkdir(parents=True,exist_ok=True)
SSH=['ssh','-i','/home/ddr/.ssh/hetzner-admin','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','root@178.104.253.211']
fixture=ROOT/'tests/fixtures/voice-check.wav'
remote='/tmp/jarvis-call-measure.wav'
subprocess.run(['scp',*SSH[1:-1],str(fixture),'root@178.104.253.211:'+remote],check=True)
source='\n'.join('FILE '+name+'\n'+(ROOT/name).read_text() for name in ['chat/chat.js','chat/voice/speech.mjs','chat/voice/session.mjs','chat/voice/core.mjs'])
code=r'''
import subprocess,json,time,datetime,urllib.request,re,hashlib,wave,pathlib,os
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
result={'scope':'Real direct private worker/model benchmark; synthetic input, no owner mic or public login. Qwen heavy review, serial stage timings, not incremental latency claim.','started':now(),'events':[]}
def runstage(name,argv,text=None):
 t=time.perf_counter();start=now();p=subprocess.run(argv,input=text,text=True,capture_output=True,timeout=60)
 d={'name':name,'started':start,'finished':now(),'seconds':time.perf_counter()-t,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 result['events'].append(d);assert p.returncode==0,d;return p.stdout
try:
 transcript=runstage('real CPU1 STT',['taskset','-c','1','/opt/jarvis-stt/venv/bin/python','/opt/jarvis-stt/stt_worker.py',INPUT])
 metrics=urllib.request.urlopen('http://127.0.0.1:18010/metrics',timeout=10).read().decode()
 relevant=[s for s in metrics.splitlines() if not s.startswith('#') and ('num_requests_running' in s or 'num_requests_waiting' in s)]
 result['pre_request_metrics']={'timestamp':now(),'lines':relevant}
 assert relevant and all(float(s.rsplit(' ',1)[-1])==0 for s in relevant),'Qwen busy: do not overlap'
 prompt='Revisa este cambio de llamada MIA como revisor técnico. Empieza con una frase breve en español. Después devuelve solo fallos reales verificables, ubicación y solución, o SIN HALLAZGOS. No inventes. Analiza mute sin grabación, SSE/TTS concurrentes, épocas, deadlines, barge-in y colas. Backend conserva 6STT/6mensajes/20TTS por minuto y máximo1000 caracteres TTS. El fixture STT real produjo: '+transcript+'\n'+SOURCE
 payload={'model':'qwen3-coder-next','messages':[{'role':'user','content':prompt}],'max_tokens':1400,'temperature':0.1,'stream':True}
 start=now();t=time.perf_counter();first=None;events=[];answer='';first_sentence=None
 req=urllib.request.Request('http://127.0.0.1:18010/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=180) as response:
  for line in response:
   if not line.startswith(b'data: '):continue
   raw=line[6:].strip()
   if raw==b'[DONE]':break
   data=json.loads(raw);delta=data.get('choices',[{}])[0].get('delta',{}).get('content') or ''
   if not delta:continue
   if first is None:first=time.perf_counter()-t
   answer+=delta;events.append({'elapsed':time.perf_counter()-t,'timestamp':now(),'delta':delta})
   if first_sentence is None and re.search(r'[.!?]\s',answer):first_sentence=time.perf_counter()-t
 result['qwen']={'model':'qwen3-coder-next','started':start,'finished':now(),'seconds':time.perf_counter()-t,'first_content_seconds':first,'first_sentence_seconds':first_sentence,'output':answer,'deltas':events,'source_sha256':hashlib.sha256(SOURCE.encode()).hexdigest()}
 text=re.split(r'(?<=[.!?])\s',answer.strip(),maxsplit=1)[0].replace('**','').replace('#','').strip()[:800]
 assert text
 runstage('real CPU0 Piper Qwen first sentence',['taskset','-c','0','/opt/jarvis-tts/venv/bin/python','-m','piper','--model','/opt/jarvis-tts/models/es_ES-davefx-medium.onnx','--output_file','/tmp/jarvis-call-qwen.wav'],text)
 result['tts_input']=text
 result['voices']=[p.name for p in pathlib.Path('/opt/jarvis-tts/models').glob('*.onnx')]
 cfg=json.loads(pathlib.Path('/opt/jarvis-tts/models/es_ES-davefx-medium.onnx.json').read_text());result['voice_config']={k:cfg[k] for k in ['audio','inference','num_speakers','language'] if k in cfg}
 sample='Hola, soy MIA. La llamada está activa. Puedes hablar con calma e interrumpirme cuando quieras.'
 for name,extra in [('default',[]),('pace-090',['--length-scale','0.90'])]:
  path='/tmp/jarvis-call-'+name+'.wav'
  runstage('Piper comparison '+name,['taskset','-c','0','/opt/jarvis-tts/venv/bin/python','-m','piper','--model','/opt/jarvis-tts/models/es_ES-davefx-medium.onnx','--output_file',path,*extra],sample)
 result['sample_input']=sample
 for p in ['/tmp/jarvis-call-qwen.wav','/tmp/jarvis-call-default.wav','/tmp/jarvis-call-pace-090.wav']:
  with wave.open(p) as w:d={'file':p,'duration':w.getnframes()/w.getframerate(),'rate':w.getframerate(),'sha256':hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()}
  result.setdefault('wav',[]).append(d)
finally:
 pathlib.Path(INPUT).unlink(missing_ok=True)
 print(json.dumps(result,ensure_ascii=False))
'''.replace('INPUT',repr(remote)).replace('SOURCE',repr(source))
r=subprocess.run(SSH+['python3 -'],input=code,text=True,capture_output=True,timeout=300)
(OUT/'real-measure.stderr.txt').write_text(r.stderr)
if r.stdout:
 data=json.loads(r.stdout);(OUT/'real-measure.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in data.items() if k!='qwen'},ensure_ascii=False,indent=2));print('QWEN',json.dumps({k:v for k,v in data.get('qwen',{}).items() if k!='deltas'},ensure_ascii=False,indent=2))
assert r.returncode==0,r.stderr
for name in ['qwen','default','pace-090']:
 subprocess.run(['scp',*SSH[1:-1],'root@178.104.253.211:/tmp/jarvis-call-'+name+'.wav',str(OUT/('voice-'+name+'.wav'))],check=True)
subprocess.run(SSH+['rm -- /tmp/jarvis-call-qwen.wav /tmp/jarvis-call-default.wav /tmp/jarvis-call-pace-090.wav'],check=True)
