/* JARVIS: same-origin authenticated chat. Never executes assistant content. */
(() => {
  'use strict';
  function mount() {
    if (document.getElementById('jarvis-chat')) return;
    const root = document.createElement('section');
    root.id = 'jarvis-chat';
    root.setAttribute('aria-label', 'Chat JARVIS');
    // Static template only. Every server/user string is assigned with textContent.
    root.innerHTML = `
      <button id="jarvis-chat-toggle" aria-expanded="false" aria-controls="jarvis-chat-panel">JARVIS · Chat</button>
      <section id="jarvis-chat-panel" aria-label="Conversación JARVIS" hidden>
        <header><strong>JARVIS <small>Qwen</small></strong><button id="jarvis-chat-minimize" aria-label="Minimizar chat">−</button></header>
        <p id="jarvis-chat-status" role="status" aria-live="polite">Conectando sesión…</p>
        <button type="button" id="jarvis-chat-retry" hidden>Actualizar sesión</button>
        <div id="jarvis-chat-conversation" hidden>
          <div id="jarvis-chat-history" role="log" aria-label="Mensajes" aria-live="polite"></div>
          <form id="jarvis-chat-compose"><label for="jarvis-chat-input">Mensaje</label><textarea id="jarvis-chat-input" maxlength="4000" rows="2" placeholder="Escribe a JARVIS…"></textarea><div class="jarvis-chat-actions"><button type="submit">Enviar</button><button type="button" id="jarvis-chat-talk">Hablar</button><button type="button" id="jarvis-chat-logout">Salir</button></div></form>
        </div>
        <footer><label><input id="jarvis-chat-autoread" type="checkbox"> Responder con voz (solo micrófono)</label><button id="jarvis-chat-stop" type="button">Detener</button></footer>
      </section>`;
    document.body.append(root);
    const el = name => root.querySelector('#jarvis-chat-' + name);
    let csrf = '', authenticated = false, authBusy = false;
    const status = text => { el('status').textContent = text; };
    async function api(action, body, signal) {
      const response = await fetch('/api/chat.php?action=' + action, {
        method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store', signal,
        headers: body === undefined ? {} : body instanceof FormData ? { 'X-CSRF-Token': csrf } : { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body)
      });
      if (!response.ok) {
        let message = 'Error HTTP ' + response.status;
        try { const data = await response.json(); if (typeof data.error === 'string') message = data.error; } catch (_) { /* non-JSON failure */ }
        const error = new Error(message); error.status = response.status; throw error;
      }
      return response;
    }
    function showError(error) {
      if (error.status === 401) {
        stop(); authenticated = false; el('conversation').hidden = true; location.replace('/login.html');
        el('history').replaceChildren(); el('input').value = '';
      }
      if ([401, 403, 503].includes(error.status)) el('retry').hidden = false;
      status(error.message);
    }
    function addMessage(role, text) {
      const row = document.createElement('article');
      row.className = 'jarvis-chat-message'; row.dataset.role = role;
      const author = document.createElement('strong'); author.textContent = role === 'user' ? 'TÚ' : 'JARVIS';
      const content = document.createElement('p'); content.textContent = text;
      row.append(author, content); el('history').append(row);
      while (el('history').children.length > 40) el('history').firstElementChild.remove();
      el('history').scrollTop = el('history').scrollHeight;
      return { row, content };
    }
    async function session() {
      const data = await (await api('session')).json();
      el('retry').hidden = false;
      if (typeof data.csrf !== 'string' || !data.csrf) throw new Error('Sesión sin token CSRF. Actualiza la sesión.');
      el('retry').hidden = true;
      csrf = typeof data.csrf === 'string' ? data.csrf : '';
      authenticated = data.authenticated === true;
      if (!authenticated) { stop(); location.replace('/login.html'); return; }
      el('conversation').hidden = false;
      el('history').replaceChildren();
      if (authenticated && Array.isArray(data.history)) {
        for (const item of data.history.slice(-40)) {
          if (['user', 'assistant'].includes(item.role) && typeof (item.content ?? item.text) === 'string') {
            const message = addMessage(item.role, (item.content ?? item.text).slice(0, 32000));
            if (item.role === 'assistant') readButton(message);
          }
        }
      }
      status(authenticated ? 'Sesión MC: ' + (data.username || 'conectada') : 'Inicia sesión con tu cuenta MC.');
    }
    async function logout() {
      if (authBusy) return; authBusy = true;
      stop();
      el('compose').querySelector('button').disabled = true;
      try {
        await api('logout', {});
        authenticated = false; el('history').replaceChildren(); el('input').value = '';
        location.replace('/login.html');
      } catch (error) { showError(error); }
      finally { authBusy = false; el('compose').querySelector('button').disabled = false; }
    }
    el('logout').addEventListener('click', logout);
    document.querySelectorAll('.sidebar-logout').forEach(button => button.addEventListener('click', logout));
    window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
    let generation = 0, controller = null, busy = false;
    let audio = null, audioURL = null, audioContext = null, source = null, analyser = null, raf = 0, finishAudio = null;
    let mic = null, recorder = null, micContext = null, micSource = null, micAnalyser = null, micRAF = 0, micTimer = 0;
    function releaseMic() {
      clearTimeout(micTimer); micTimer = 0;
      cancelAnimationFrame(micRAF); micRAF = 0;
      if (mic) mic.getTracks().forEach(track => track.stop()); mic = null;
      if (micSource) micSource.disconnect(); if (micAnalyser) micAnalyser.disconnect(); micSource = micAnalyser = null;
      if (micContext) micContext.close().catch(() => {}); micContext = null;
      el('talk').textContent = 'Hablar';
    }
    function cleanupMic() {
      if (recorder) {
        recorder.onstop = recorder.ondataavailable = recorder.onerror = null;
        if (recorder.state !== 'inactive') recorder.stop();
      }
      recorder = null; releaseMic();
    }
    function finishRecording() {
      if (!recorder || recorder.state === 'inactive') return;
      recorder.stop(); releaseMic();
    }
    el('talk').addEventListener('click', async () => {
      if (!authenticated || authBusy) return;
      if (recorder?.state === 'recording') { finishRecording(); return; }
      stop(); const id = generation;
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { status('Micrófono no compatible. Usa texto.'); return; }
      const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'].find(type => MediaRecorder.isTypeSupported(type));
      if (!mimeType) { status('Formato de micrófono no compatible.'); return; }
      status('Esperando permiso de micrófono…');
      try {
        // The only getUserMedia call: synchronously initiated by this explicit button click.
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        if (id !== generation) { stream.getTracks().forEach(track => track.stop()); return; }
        mic = stream;
        const Context = window.AudioContext || window.webkitAudioContext;
        if (Context) {
          micContext = new Context(); micContext.resume().catch(() => {});
          micSource = micContext.createMediaStreamSource(stream); micAnalyser = micContext.createAnalyser(); micAnalyser.fftSize = 256;
          micSource.connect(micAnalyser); // Never connect microphone to speakers.
          const samples = new Float32Array(256);
          const tick = () => {
            if (id !== generation || !micAnalyser) return;
            micAnalyser.getFloatTimeDomainData(samples);
            let sum = 0; for (const sample of samples) sum += sample * sample;
            state('listening', Math.sqrt(sum / samples.length)); micRAF = requestAnimationFrame(tick);
          }; tick();
        }
        const active = new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 64000 });
        recorder = active; const parts = []; let bytes = 0;
        active.ondataavailable = event => {
          if (id !== generation || !event.data.size) return;
          bytes += event.data.size;
          if (bytes > 2097152) { stop(); status('Audio demasiado grande. Máximo 2 MB.'); return; }
          parts.push(event.data);
        };
        active.onerror = () => { if (id === generation) { stop(); status('No se pudo grabar el micrófono.'); } };
        active.onstop = async () => {
          if (id !== generation) return;
          releaseMic(); recorder = null;
          if (!bytes) { state('idle'); status('No se grabó audio.'); return; }
          controller = new AbortController(); state('transcribing'); status('Transcribiendo audio local…');
          const form = new FormData(); form.append('audio', new Blob(parts, { type: active.mimeType }), 'voice.' + (mimeType.includes('mp4') ? 'mp4' : mimeType.includes('ogg') ? 'ogg' : 'webm'));
          try {
            const data = await (await api('transcribe', form, controller.signal)).json();
            if (id !== generation) return;
            if (typeof data.text !== 'string' || data.text.length > 4000) throw new Error('Transcripción inválida.');
            if (!data.text.trim()) { state('idle'); status('No se detectó voz.'); return; }
            await sendText(data.text.trim(), true);
          } catch (error) {
            if (id === generation && error.name !== 'AbortError') { state('idle'); showError(error); }
          } finally { if (id === generation) { controller = null; state('idle'); } }
        };
        active.start(250); micTimer = setTimeout(finishRecording, 20000);
        el('talk').textContent = 'Terminar y enviar'; state('listening'); status('Escuchando · máximo 20 s. Detener cancela.');
      } catch (error) {
        if (id === generation) { cleanupMic(); state('idle'); status('No se pudo acceder al micrófono. Pulsa Hablar y autorízalo en el navegador.'); }
      }
    });
    function cleanupAudio() {
      if (raf) cancelAnimationFrame(raf); raf = 0;
      if (audio) { audio.onended = null; audio.onerror = null; audio.pause(); audio.removeAttribute('src'); audio.load(); audio = null; }
      if (source) source.disconnect(); if (analyser) analyser.disconnect(); source = analyser = null;
      if (audioURL) URL.revokeObjectURL(audioURL); audioURL = null;
      if (finishAudio) { const finish = finishAudio; finishAudio = null; finish(); }
    }
    function chunks(text) {
      const result = []; let rest = text.trim();
      while (rest) {
        let end = Math.min(1000, rest.length);
        if (rest.length > end) {
          const sample = rest.slice(0, end), sentences = [...sample.matchAll(/[.!?][\s]+/g)];
          const sentence = sentences.at(-1);
          const boundary = sentence ? sentence.index + 1 : sample.lastIndexOf(' ');
          if (boundary > 0) end = boundary;
          if (end > 0 && /[\uD800-\uDBFF]/.test(rest[end - 1])) end--;
        }
        const part = rest.slice(0, end).trim(); if (part) result.push(part);
        rest = rest.slice(end).trim();
      }
      return result;
    }
    function readButton(message) {
      if (!message.content.textContent.trim() || message.row.querySelector('.jarvis-chat-read')) return;
      const button = document.createElement('button'); button.type = 'button'; button.className = 'jarvis-chat-read'; button.textContent = 'Leer';
      button.addEventListener('click', () => speak(message.content.textContent)); message.row.append(button);
    }
    async function speak(text) {
      if (!authenticated || authBusy) return;
      stop(); const id = generation; controller = new AbortController();
      try {
        // Resume in the user click, before waiting for the authenticated WAV.
        const Context = window.AudioContext || window.webkitAudioContext;
        if (Context && !audioContext) audioContext = new Context();
        if (audioContext) {
          status('Pulsa Leer si el navegador solicita permitir audio.');
          await audioContext.resume();
        }
        if (id !== generation) return;
        if (audioContext && audioContext.state !== 'running') throw new Error('Pulsa Leer para permitir la reproducción de audio.');
        for (const part of chunks(text.slice(0, 32000))) {
          if (id !== generation) return;
          state('thinking'); status('Preparando voz…');
          const response = await api('tts', { text: part }, controller.signal);
          if (id !== generation) { await response.body?.cancel(); return; }
          if (!/audio\/(?:wav|wave|x-wav)/i.test(response.headers.get('content-type') || '')) throw new Error('El servidor no devolvió audio WAV.');
          const blob = await response.blob(); if (id !== generation) return;
          if (!blob.size || blob.size > 20000000) throw new Error('Audio vacío o demasiado grande.');
          audioURL = URL.createObjectURL(blob); audio = new Audio(audioURL);
          if (audioContext) {
            source = audioContext.createMediaElementSource(audio); analyser = audioContext.createAnalyser(); analyser.fftSize = 256;
            source.connect(analyser); analyser.connect(audioContext.destination);
          }
          await new Promise((resolve, reject) => {
            finishAudio = resolve;
            audio.onended = resolve; audio.onerror = () => reject(new Error('No se pudo reproducir el audio WAV.'));
            const samples = analyser ? new Float32Array(analyser.fftSize) : null;
            const tick = () => {
              if (id !== generation || !audio || audio.paused) { raf = 0; return; }
              let level = 0;
              if (analyser && samples) { analyser.getFloatTimeDomainData(samples); for (const x of samples) level += x * x; level = Math.sqrt(level / samples.length); }
              state('speaking', level); raf = requestAnimationFrame(tick);
            };
            audio.play().then(() => {
              if (id !== generation) return;
              status('Leyendo respuesta…'); tick();
            }).catch(() => reject(new Error('Audio bloqueado. Pulsa Leer para reintentar.')));
          });
          if (id !== generation) return;
          cleanupAudio();
        }
        if (id === generation) status('Lectura completada.');
      } catch (error) {
        if (id === generation && error.name !== 'AbortError') showError(error);
      } finally {
        if (id === generation) { cleanupAudio(); controller = null; state('idle'); }
      }
    }
    function state(value, level = 0) {
      window.dispatchEvent(new CustomEvent('jarvis-chat-state', { detail: { state: value, level: Math.max(0, Math.min(1, Number(level) || 0)) } }));
    }
    function stop() {
      generation++; if (controller) controller.abort(); controller = null; busy = false;
      cleanupAudio(); cleanupMic();
      el('compose').querySelector('button').disabled = false;
      state('idle');
    }
    el('stop').addEventListener('click', () => { stop(); status('Detenido.'); });
    async function consume(response, id, update) {
      if (!response.headers.get('content-type')?.includes('text/event-stream') || !response.body) throw new Error('Respuesta de streaming no válida.');
      const reader = response.body.getReader(), decoder = new TextDecoder();
      let buffer = '', event = '', lines = [], complete = false, total = 0;
      function dispatch() {
        if (!lines.length) { event = ''; return; }
        const type = event || 'message', raw = lines.join('\n'); lines = []; event = '';
        if (!['delta', 'done', 'error'].includes(type)) return;
        let data; try { data = JSON.parse(raw); } catch (_) { throw new Error('Evento SSE no válido.'); }
        if (type === 'error') throw new Error(typeof data.error === 'string' ? data.error : 'Error del modelo.');
        if (typeof data.text !== 'string') throw new Error('Texto SSE no válido.');
        update(type, data.text);
        if (type === 'done') complete = true;
      }
      function line(text) {
        if (!text) return dispatch();
        if (text.startsWith(':')) return;
        const i = text.indexOf(':'), key = i < 0 ? text : text.slice(0, i);
        let value = i < 0 ? '' : text.slice(i + 1); if (value.startsWith(' ')) value = value.slice(1);
        if (key === 'event') event = value;
        if (key === 'data') lines.push(value);
      }
      try {
        while (!complete && id === generation) {
          const { value, done } = await reader.read();
          if (id !== generation) return false;
          total += value?.byteLength || 0; if (total > 256000) throw new Error('Respuesta demasiado larga.');
          buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
          // Preserve a trailing CR until the next byte so split CRLF is one newline.
          while (!complete) {
            const match = /\r\n|\r|\n/.exec(buffer); if (!match) break;
            if (!done && match[0] === '\r' && match.index === buffer.length - 1) break;
            const text = buffer.slice(0, match.index); buffer = buffer.slice(match.index + match[0].length); line(text);
          }
          if (done) { if (buffer && !complete) line(buffer); if (!complete) dispatch(); break; }
        }
        if (id !== generation) return false;
        if (!complete) throw new Error('La conexión terminó sin completar la respuesta.');
        return true;
      } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
    }
    async function sendText(text, fromVoice = false) {
      if (!authenticated || authBusy || busy || !text || text.length > 4000) return;
      stop(); const id = generation; controller = new AbortController(); busy = true;
      el('compose').querySelector('button').disabled = true;
      el('input').value = ''; addMessage('user', text);
      const message = addMessage('assistant', ''); let answer = '';
      state('thinking'); status('Qwen está respondiendo…');
      try {
        const response = await api('message', { text }, controller.signal);
        if (id !== generation) { await response.body?.cancel(); return; }
        await consume(response, id, (type, part) => {
          if (id !== generation) return;
          answer = type === 'done' ? part : answer + part;
          if (answer.length > 32000) throw new Error('Respuesta demasiado larga.');
          message.content.textContent = answer;
          el('history').scrollTop = el('history').scrollHeight;
        });
        if (id === generation) { status('Respuesta completada.'); readButton(message); }
      } catch (error) {
        if (id === generation && error.name !== 'AbortError') showError(error);
      } finally {
        if (id === generation) { busy = false; controller = null; el('compose').querySelector('button').disabled = false; state('idle'); }
      }
      if (id === generation && message.row.querySelector('.jarvis-chat-read') && fromVoice && el('autoread').checked) speak(answer);
    }
    el('compose').addEventListener('submit', e => { e.preventDefault(); sendText(el('input').value.trim()); });
    el('input').addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); el('compose').requestSubmit(); }
    });
    window.addEventListener('pagehide', stop);
    state('idle');
    async function refreshSession() {
      if (authBusy) return; authBusy = true;
      stop(); el('retry').disabled = true;
      try { await session(); }
      catch (error) { el('retry').hidden = false; status('No se pudo cargar la sesión: ' + error.message); }
      finally { authBusy = false; el('retry').disabled = false; }
    }
    el('retry').addEventListener('click', refreshSession);
    refreshSession();
    function expand(value) {
      el('panel').hidden = !value;
      el('toggle').hidden = value;
      el('toggle').setAttribute('aria-expanded', String(value));
      (value ? el(authenticated ? 'input' : 'username') : el('toggle')).focus();
    }
    el('toggle').addEventListener('click', () => expand(true));
    el('minimize').addEventListener('click', () => expand(false));
    root.addEventListener('keydown', e => { if (e.key === 'Escape') expand(false); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
