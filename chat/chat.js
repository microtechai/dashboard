/* JARVIS: same-origin authenticated chat. Never executes assistant content. */
(() => {
  'use strict';
  function mount() {
    if (document.getElementById('jarvis-chat')) return;
    const root = document.createElement('section');
    root.id = 'jarvis-chat';
    root.setAttribute('aria-label', 'Chat MIA');
    // Static template only. Every server/user string is assigned with textContent.
    root.innerHTML = `
      <button id="jarvis-chat-toggle" aria-expanded="false" aria-controls="jarvis-chat-panel">MIA · Chat</button>
      <section id="jarvis-chat-panel" aria-label="Conversación MIA" hidden>
        <header><strong title="MIA, acrónimo de MicrotechAI">MIA <small>Microtech AI</small></strong><button id="jarvis-chat-minimize" aria-label="Minimizar chat">−</button></header>
        <p id="jarvis-chat-status" role="status" aria-live="polite">Conectando sesión…</p>
        <button type="button" id="jarvis-chat-retry" hidden>Actualizar sesión</button>
        <div id="jarvis-chat-conversation" hidden>
          <div id="jarvis-chat-active-controls" hidden></div>
          <p id="jarvis-chat-mic" data-state="off" role="status">Micrófono cerrado</p>
          <div id="jarvis-chat-history" role="log" aria-label="Mensajes" aria-live="polite"></div>
          <form id="jarvis-chat-compose">
            <label class="jarvis-chat-sr-only" for="jarvis-chat-input">Mensaje</label>
            <textarea id="jarvis-chat-input" maxlength="4000" rows="2" placeholder="Escribe a MIA…"></textarea>
            <button type="submit">Enviar</button>
            <button type="button" id="jarvis-chat-talk" title="Alternativa manual: colgar primero; cada frase requiere pulsar.">Hablar (manual)</button>
          </form>
        </div>
        <footer>
          <details id="jarvis-chat-options">
            <summary>Opciones</summary>
            <div class="jarvis-chat-options-body">
              <div id="jarvis-chat-call-controls">
                <button type="button" id="jarvis-chat-continuous" disabled>Llamar a MIA</button>
                <button type="button" id="jarvis-chat-mute" disabled>Silenciar micrófono</button>
              </div>
              <label><input id="jarvis-chat-autoread" type="checkbox"> Voz al usar Hablar manual</label>
              <details id="jarvis-chat-context">
                <summary>Contexto MC</summary>
                <div>
                  <button type="button" id="jarvis-chat-dashboard">Ver dashboard</button>
                  <button type="button" id="jarvis-chat-projects">Ver proyectos</button>
                  <p id="jarvis-chat-context-status" role="status" aria-live="polite">Consulta de solo lectura.</p>
                  <ul id="jarvis-chat-context-result" aria-label="Resumen de Contexto MC"></ul>
                  <button type="button" id="jarvis-chat-idea">Guardar idea privada</button>
                  <button type="button" id="jarvis-chat-analyze" disabled>Analizar idea</button>
                  <p id="jarvis-chat-analysis-status" role="status" aria-live="polite"></p>
                  <div id="jarvis-chat-analysis-result" aria-label="Análisis de idea"></div>
                  <button type="button" id="jarvis-chat-proposal" disabled>Preparar propuesta</button>
                  <p id="jarvis-chat-proposal-status" role="status" aria-live="polite"></p>
                  <div id="jarvis-chat-proposal-result" aria-label="Propuesta comercial"></div>
                  <button type="button" id="jarvis-chat-client-view" disabled>Preparar vista de cliente</button>
                  <p id="jarvis-chat-client-view-status" role="status" aria-live="polite"></p>
                  <div id="jarvis-chat-client-view-result" aria-label="Vista de cliente"></div>
                  <p id="jarvis-chat-idea-status" role="status" aria-live="polite">Guarda el texto actual como borrador privado de esta sesión. Se pierde al salir; no ejecuta acciones.</p>
                  <div id="jarvis-chat-idea-result" aria-label="Borrador privado"></div>
                </div>
              </details>
              <details class="jarvis-chat-help"><summary>Ayuda de voz</summary><p class="jarvis-voice-notice">Voz continua experimental · usa auriculares. AEC solicitado al navegador; VAD no elimina eco ni garantiza evitar auto-interrupciones con altavoces. Máximo 20 s por frase, 6 envíos/min; sin reintentos automáticos.</p><p>Hablar graba una frase; pulsa de nuevo para enviarla. Detener cancela la respuesta; durante una llamada, Colgar cierra el micrófono.</p></details>
              <details class="mia-workflow"><summary>Flujo observable</summary><div><p id="jarvis-chat-stage" role="status">Sin petición activa</p><p>STT y modelo: petición pendiente, no porcentaje interno. Audio: reproducción local observada.</p><p>Memoria y herramientas: no instrumentado. Obsidian: concepto sin datos importados.</p></div></details>
              <button type="button" id="jarvis-chat-logout">Salir</button>
            </div>
          </details>
          <button id="jarvis-chat-stop" type="button">Detener</button>
        </footer>
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
      if (callOn || continuous?.active || continuous?.pending) stop();
      if (error.status === 401) {
        el('context-result').replaceChildren();
        el('idea-result').replaceChildren(); resetAnalysis();
        stop(); authenticated = false; el('conversation').hidden = true; location.replace('/login.html');
        el('history').replaceChildren(); el('input').value = '';
      }
      if ([401, 403, 503].includes(error.status)) el('retry').hidden = false;
      status(error.message);
    }
    function addMessage(role, text) {
      const row = document.createElement('article');
      row.className = 'jarvis-chat-message'; row.dataset.role = role;
      const author = document.createElement('strong'); author.textContent = role === 'user' ? 'TÚ' : 'MIA';
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
      el('idea-result').replaceChildren(); resetAnalysis();
      el('context-result').replaceChildren();
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
    let contextController = null;
    let ideaController = null, analysisController = null, savedIdeaId = null;
    let proposalController = null, savedAnalysis = null;
    let clientViewController = null, savedProposal = null;
    let lastUserText = '';
    function analysisState(value, text) {
      el('analysis-status').dataset.state = value;
      el('analysis-status').textContent = text;
      el('analysis-result').setAttribute('aria-busy', String(value === 'loading'));
      el('analyze').disabled = !savedIdeaId || value === 'loading';
    }
    function cancelAnalysis() {
      if (!analysisController) return;
      analysisController.abort(); analysisController = null;
      analysisState('idle', 'Análisis detenido.');
    }
    function resetAnalysis() {
      cancelAnalysis(); resetProposal(); savedIdeaId = null;
      el('analysis-result').replaceChildren(); analysisState('idle', '');
    }
    function renderAnalysis(data, ideaId) {
      const value = data?.analysis;
      const fields = { problem: 'Problema', client: 'Cliente', sector: 'Sector', opportunities: 'Oportunidades', risks: 'Riesgos', questions: 'Preguntas' };
      const validString = text => typeof text === 'string' && Array.from(text).length <= 500;
      if (data?.ok !== true || data.idea_id !== ideaId || data.source !== 'qwen3-coder-next' ||
          !value || typeof value !== 'object' || Array.isArray(value) ||
          Object.keys(value).sort().join() !== Object.keys(fields).sort().join() ||
          new TextEncoder().encode(JSON.stringify(value)).length > 6000) throw new Error('Análisis no válido.');
      for (const key of Object.keys(fields)) {
        if (['problem', 'client', 'sector'].includes(key) ? !validString(value[key]) :
            !Array.isArray(value[key]) || value[key].length > 5 || !value[key].every(validString)) throw new Error('Análisis no válido.');
      }
      const fragment = document.createDocumentFragment();
      for (const [key, label] of Object.entries(fields)) {
        const title = document.createElement('strong'); title.textContent = label; fragment.append(title);
        for (const text of Array.isArray(value[key]) ? value[key] : [value[key]]) {
          const row = document.createElement('p'); row.textContent = text; fragment.append(row);
        }
      }
      el('analysis-result').replaceChildren(fragment);
    }
    el('analyze').addEventListener('click', async () => {
      if (!authenticated || authBusy || ideaController || analysisController || !savedIdeaId ||
          el('panel').hidden || !el('options').open || !el('context').open) return;
      const ideaId = savedIdeaId, request = new AbortController(); analysisController = request;
      resetProposal(); el('analysis-result').replaceChildren(); analysisState('loading', 'Analizando idea…');
      try {
        const data = await (await api('analyze_idea', { idea_id: ideaId }, request.signal)).json();
        if (analysisController !== request || request.signal.aborted || savedIdeaId !== ideaId) return;
        renderAnalysis(data, ideaId); savedAnalysis = data.analysis; proposalState('idle', ''); analysisState('success', 'Análisis completado.');
      } catch (error) {
        if (analysisController !== request || request.signal.aborted) return;
        if (error.name === 'AbortError') cancelAnalysis();
        else {
          const safeError = new Error('Análisis no disponible.'); safeError.status = error.status;
          showError(safeError); analysisState('error', safeError.message);
        }
      } finally { if (analysisController === request) analysisController = null; }
    });
    function proposalState(value, text) {
      el('proposal-status').dataset.state = value;
      el('proposal-status').textContent = text;
      el('proposal-result').setAttribute('aria-busy', String(value === 'loading'));
      el('proposal').disabled = !savedAnalysis || value === 'loading';
    }
    function cancelProposal() {
      if (!proposalController) return;
      proposalController.abort(); proposalController = null;
      proposalState('idle', 'Propuesta detenida.');
    }
    function resetProposal() {
      cancelProposal(); resetClientView(); savedAnalysis = null;
      el('proposal-result').replaceChildren(); proposalState('idle', '');
    }
    function renderProposal(data, ideaId) {
      const value = data?.proposal;
      const fields = { title: 'Título', executive_summary: 'Resumen ejecutivo', scope: 'Alcance', deliverables: 'Entregables', assumptions: 'Supuestos', next_steps: 'Próximos pasos', questions: 'Preguntas' };
      const validString = (text, max = 500) => typeof text === 'string' && Array.from(text).length <= max;
      if (data?.ok !== true || data.idea_id !== ideaId || data.source !== 'qwen3-coder-next' ||
          !value || typeof value !== 'object' || Array.isArray(value) ||
          Object.keys(value).sort().join() !== Object.keys(fields).sort().join() ||
          new TextEncoder().encode(JSON.stringify(value)).length > 8000) throw new Error('Propuesta no válida.');
      for (const key of Object.keys(fields)) {
        if (['title', 'executive_summary', 'scope'].includes(key) ? !validString(value[key], 1000) :
            !Array.isArray(value[key]) || value[key].length > 5 || !value[key].every(text => validString(text))) throw new Error('Propuesta no válida.');
      }
      const fragment = document.createDocumentFragment();
      for (const [key, label] of Object.entries(fields)) {
        const title = document.createElement('strong'); title.textContent = label; fragment.append(title);
        for (const text of Array.isArray(value[key]) ? value[key] : [value[key]]) {
          const row = document.createElement('p'); row.textContent = text; fragment.append(row);
        }
      }
      el('proposal-result').replaceChildren(fragment);
    }
    el('proposal').addEventListener('click', async () => {
      if (!authenticated || authBusy || ideaController || analysisController || proposalController || !savedIdeaId || !savedAnalysis ||
          el('panel').hidden || !el('options').open || !el('context').open) return;
      const ideaId = savedIdeaId, analysis = savedAnalysis, request = new AbortController(); proposalController = request;
      resetClientView(); el('proposal-result').replaceChildren(); proposalState('loading', 'Preparando propuesta…');
      try {
        const data = await (await api('prepare_proposal', { idea_id: ideaId, analysis }, request.signal)).json();
        if (proposalController !== request || request.signal.aborted || savedIdeaId !== ideaId || savedAnalysis !== analysis) return;
        renderProposal(data, ideaId); savedProposal = data.proposal; clientViewState('idle', ''); proposalState('success', 'Propuesta preparada; no se guarda ni se envía.');
      } catch (error) {
        if (proposalController !== request || request.signal.aborted) return;
        if (error.name === 'AbortError') cancelProposal();
        else {
          const safeError = new Error('Propuesta no disponible.'); safeError.status = error.status;
          showError(safeError); proposalState('error', safeError.message);
        }
      } finally { if (proposalController === request) proposalController = null; }
    });
    function clientViewState(value, text) {
      el('client-view-status').dataset.state = value;
      el('client-view-status').textContent = text;
      el('client-view-result').setAttribute('aria-busy', String(value === 'loading'));
      el('client-view').disabled = !savedProposal || value === 'loading';
    }
    function cancelClientView() {
      if (!clientViewController) return;
      clientViewController.abort(); clientViewController = null;
      clientViewState('idle', 'Vista de cliente detenida.');
    }
    function resetClientView() {
      cancelClientView(); savedProposal = null;
      el('client-view-result').replaceChildren(); clientViewState('idle', '');
    }
    function renderClientView(data, ideaId) {
      const value = data?.client_view;
      const fields = { title: 'Título', value_proposition: 'Propuesta de valor', scope: 'Alcance', deliverables: 'Entregables', timeline: 'Calendario tentativo', next_steps: 'Próximos pasos', questions: 'Preguntas' };
      const validString = (text, max = 500) => typeof text === 'string' && Array.from(text).length <= max;
      if (data?.ok !== true || data.idea_id !== ideaId || data.source !== 'qwen3-coder-next' ||
          !value || typeof value !== 'object' || Array.isArray(value) ||
          Object.keys(value).sort().join() !== Object.keys(fields).sort().join() ||
          new TextEncoder().encode(JSON.stringify(value)).length > 6000) throw new Error('Vista de cliente no válida.');
      for (const key of Object.keys(fields)) {
        if (['title', 'value_proposition', 'scope', 'timeline'].includes(key) ? !validString(value[key], 1000) :
            !Array.isArray(value[key]) || value[key].length > 5 || !value[key].every(text => validString(text))) throw new Error('Vista de cliente no válida.');
      }
      const fragment = document.createDocumentFragment();
      for (const [key, label] of Object.entries(fields)) {
        const title = document.createElement('strong'); title.textContent = label; fragment.append(title);
        for (const text of Array.isArray(value[key]) ? value[key] : [value[key]]) {
          const row = document.createElement('p'); row.textContent = text; fragment.append(row);
        }
      }
      el('client-view-result').replaceChildren(fragment);
    }
    el('client-view').addEventListener('click', async () => {
      if (!authenticated || authBusy || ideaController || analysisController || proposalController || clientViewController || !savedIdeaId || !savedProposal ||
          el('panel').hidden || !el('options').open || !el('context').open) return;
      const ideaId = savedIdeaId, proposal = savedProposal, request = new AbortController(); clientViewController = request;
      el('client-view-result').replaceChildren(); clientViewState('loading', 'Preparando vista de cliente…');
      try {
        const data = await (await api('prepare_client_view', { idea_id: ideaId, proposal }, request.signal)).json();
        if (clientViewController !== request || request.signal.aborted || savedIdeaId !== ideaId || savedProposal !== proposal) return;
        renderClientView(data, ideaId); clientViewState('success', 'Vista de cliente preparada; pendiente de revisión. No se guarda ni se envía.');
      } catch (error) {
        if (clientViewController !== request || request.signal.aborted) return;
        if (error.name === 'AbortError') cancelClientView();
        else {
          const safeError = new Error('Vista de cliente no disponible.'); safeError.status = error.status;
          showError(safeError); clientViewState('error', safeError.message);
        }
      } finally { if (clientViewController === request) clientViewController = null; }
    });
    function ideaState(value, text) {
      el('idea-status').dataset.state = value;
      el('idea-status').textContent = text;
      el('idea').disabled = value === 'loading';
      el('idea-result').setAttribute('aria-busy', String(value === 'loading'));
    }
    function cancelIdea() {
      if (!ideaController) return;
      ideaController.abort(); ideaController = null;
      ideaState('idle', 'Solicitud detenida; el borrador podría haberse guardado en esta sesión.');
    }
    el('idea').addEventListener('click', async () => {
      if (!authenticated || authBusy || ideaController || el('panel').hidden ||
          !el('options').open || !el('context').open) return;
      const text = el('input').value || lastUserText;
      el('idea-result').replaceChildren(); resetAnalysis();
      if (!text.trim()) { ideaState('error', 'Escribe una idea antes de guardarla.'); return; }
      const source = el('input').value ? 'texto actual' : 'último mensaje enviado';
      const request = new AbortController(); ideaController = request;
      ideaState('loading', 'Guardando borrador privado desde el ' + source + '…');
      try {
        const data = await (await api('idea', { text }, request.signal)).json();
        if (ideaController !== request || request.signal.aborted) return;
        const idea = data?.idea;
        if (data?.ok !== true || idea?.state !== 'BORRADOR' || typeof idea.text !== 'string' ||
            typeof idea.id !== 'string' || !/^[a-f0-9]{16}$/.test(idea.id) || typeof idea.created_at !== 'string') throw new Error('Respuesta de borrador no válida.');
        const label = document.createElement('p'); label.textContent = idea.state + ' · ' + idea.id + ' · ' + idea.created_at;
        const content = document.createElement('p'); content.textContent = idea.text;
        el('idea-result').append(label, content);
        savedIdeaId = idea.id; analysisState('idle', '');
        ideaState('success', 'Idea guardada como BORRADOR privado de esta sesión.');
      } catch (error) {
        if (ideaController !== request || request.signal.aborted) return;
        if (error.name === 'AbortError') cancelIdea();
        else { showError(error); ideaState('error', error.message.slice(0, 4000)); }
      } finally { if (ideaController === request) ideaController = null; }
    });
    function contextState(value, text) {
      el('context-status').dataset.state = value;
      el('context-status').textContent = text;
      el('context-result').setAttribute('aria-busy', String(value === 'loading'));
      el('dashboard').disabled = el('projects').disabled = value === 'loading';
    }
    function cancelContext() {
      if (!contextController) return;
      contextController.abort(); contextController = null;
      contextState('idle', 'Consulta detenida.');
    }
    function renderContext(data) {
      // Opaque MC values are display-only: no HTML, links, model input or history.
      const result = el('context-result'); result.replaceChildren();
      let remaining = 4000, count = 0;
      function visit(value, path, depth) {
        if (count >= 12 || remaining <= 0) return;
        if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) {
          const text = (path + ': ' + String(value).slice(0, remaining)).slice(0, remaining);
          const row = document.createElement('li'); row.textContent = text; result.append(row);
          remaining -= text.length; count++;
        } else if (typeof value === 'object' && depth < 4) {
          // Bound traversal as well as output, including empty/nested collections.
          let visited = 0;
          for (const key in value) {
            if (!Object.prototype.hasOwnProperty.call(value, key)) continue;
            if (visited++ >= 12 || count >= 12 || remaining <= 0) break;
            visit(value[key], (path ? path + ' · ' : '') + key.slice(0, 120), depth + 1);
          }
        }
      }
      visit(data, '', 0);
      return count;
    }
    async function readContext(tool) {
      if (!['read_dashboard', 'read_projects'].includes(tool) || !authenticated || authBusy || contextController ||
          el('panel').hidden || !el('options').open || !el('context').open) return;
      const request = new AbortController(); contextController = request;
      el('context-result').replaceChildren();
      contextState('loading', 'Consultando Contexto MC…');
      try {
        const data = await (await api('tool', { tool, args: {} }, request.signal)).json();
        if (contextController !== request || request.signal.aborted) return;
        if (data?.ok !== true || data.tool !== tool) throw new Error(typeof data?.error === 'string' ? data.error : 'Respuesta de Contexto MC no válida.');
        const count = renderContext(data.data);
        contextState('success', count ? 'Consulta completada · resumen limitado a 12 elementos / 4000 caracteres.' : 'Consulta completada · sin datos resumibles.');
      } catch (error) {
        if (contextController !== request || request.signal.aborted) return;
        if (error.name === 'AbortError') contextState('idle', 'Consulta detenida.');
        else {
          showError(error);
          contextState('error', error.message.slice(0, 4000));
        }
      } finally { if (contextController === request) contextController = null; }
    }
    el('dashboard').addEventListener('click', () => readContext('read_dashboard'));
    el('projects').addEventListener('click', () => readContext('read_projects'));
    let audio = null, audioURL = null, audioContext = null, source = null, analyser = null, raf = 0, finishAudio = null;
    let mic = null, recorder = null, micContext = null, micSource = null, micAnalyser = null, micRAF = 0, micTimer = 0;
    function releaseMic() {
      clearTimeout(micTimer); micTimer = 0;
      cancelAnimationFrame(micRAF); micRAF = 0;
      if (mic) mic.getTracks().forEach(track => track.stop()); mic = null;
      if (micSource) micSource.disconnect(); if (micAnalyser) micAnalyser.disconnect(); micSource = micAnalyser = null;
      if (micContext) micContext.close().catch(() => {}); micContext = null;
      el('talk').textContent = 'Hablar (manual)';
      if (!continuous?.active && !continuous?.pending) micState('off');
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
        el('mic').dataset.state = 'active'; el('mic').textContent = 'Micrófono activo · grabación manual, máximo 20 s';
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
    function readButton(message) {
      if (!message.content.textContent.trim() || message.row.querySelector('.jarvis-chat-read')) return;
      const button = document.createElement('button'); button.type = 'button'; button.className = 'jarvis-chat-read'; button.textContent = 'Leer';
      button.addEventListener('click', () => speak(message.content.textContent, message)); message.row.append(button);
    }
    let SpeechQueue = null, speech = null, ttsEpoch = 0;
    const speechReady = import('/chat/voice/speech.mjs?v=20260909-audio-integrity1').then(module => { SpeechQueue = module.SpeechQueue; });
    speechReady.catch(() => {}); // A requested read reports load failure explicitly.
    const ttsRequests = [];
    function newSpeech(id, message) {
      return new SpeechQueue({
        play: (part, signal) => playPart(part, signal, id, ttsEpoch),
        stop: cleanupAudio,
        onError: error => { if (id === generation) showError(error); },
        onLimit: () => {
          const notice = 'Voz limitada a 3 bloques por respuesta; el resto permanece en texto.';
          if (message && !message.row.querySelector('.jarvis-speech-limit')) {
            const p = document.createElement('p'); p.className = 'jarvis-speech-limit'; p.textContent = notice; message.row.append(p);
          }
          status(notice);
        },
        onIdle: () => { if (id === generation && !busy) { state('idle'); status(speech?.limited ? 'Lectura completada hasta el límite de voz; el resto está en texto.' : 'Lectura completada.'); } }
      });
    }
    async function playPart(part, signal, id, voiceId) {
      const valid = () => id === generation && voiceId === ttsEpoch && !signal.aborted;
      if (!valid()) return;
      const now = Date.now(); while (ttsRequests.length && now - ttsRequests[0] >= 60000) ttsRequests.shift();
      if (ttsRequests.length >= 20) throw Object.assign(new Error('Límite local 20 voces/min. Sin reintento automático.'), { status: 429 });
      const Context = window.AudioContext || window.webkitAudioContext;
      if (Context && !audioContext) audioContext = new Context();
      await audioContext?.resume(); if (!valid()) return;
      if (audioContext && audioContext.state !== 'running') throw new Error('Pulsa Leer para permitir audio.');
      ttsRequests.push(now);
      // Separate signal/deadline from model SSE and microphone capture.
      const deadline = new AbortController();
      const abort = () => { clearTimeout(timer); deadline.abort(); }; signal.addEventListener('abort', abort, { once: true });
      let timeoutError = false;
      const timer = setTimeout(() => { if (!valid()) return; timeoutError = true; deadline.abort(); cleanupAudio(); }, 65000);
      try {
        status('Preparando voz local…');
        const response = await api('tts', { text: part }, deadline.signal);
        if (!valid()) { await response.body?.cancel(); return; }
        if (!/audio\/(?:wav|wave|x-wav)/i.test(response.headers.get('content-type') || '')) throw new Error('El servidor no devolvió audio WAV.');
        const blob = await response.blob(); if (!valid()) return;
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
            if (!valid() || !audio || audio.paused) { raf = 0; return; }
            let level = 0;
            if (analyser && samples) { analyser.getFloatTimeDomainData(samples); for (const x of samples) level += x * x; level = Math.sqrt(level / samples.length); }
            state('speaking', level); raf = requestAnimationFrame(tick);
          };
          audio.play().then(() => { if (valid()) { status('MIA habla · puedes interrumpir en llamada.'); tick(); } })
            .catch(() => reject(new Error('Audio bloqueado. Pulsa Leer para reintentar.')));
        });
        if (timeoutError) throw new Error('Tiempo de voz agotado. Sin reintento automático.');
      } catch (error) {
        if (timeoutError) throw new Error('Tiempo de voz agotado. Sin reintento automático.');
        if (valid()) throw error;
      } finally {
        clearTimeout(timer); signal.removeEventListener('abort', abort);
        if (valid()) cleanupAudio();
      }
    }
    async function speak(text, message) {
      if (!authenticated || authBusy) return;
      cancelResponse(); cleanupMic(); const id = generation;
      try { await speechReady; if (id !== generation) return; speech = newSpeech(id, message); speech.push(text, true); }
      catch (error) { if (id === generation) showError(error); }
    }
    function state(value, level = 0) {
      if (value === 'idle' && continuous?.active) { value = 'listening'; level = micLevel; }
      const labels={idle:'Sin petición activa',listening:'Entrada de micrófono',transcribing:'STT · petición pendiente',thinking:'Modelo · petición / stream pendiente',speaking:'Audio · reproducción local'};
      const label=labels[value]||'Sin instrumentación';
      if(el('stage') && el('stage').textContent!==label) el('stage').textContent=label;
      window.dispatchEvent(new CustomEvent('jarvis-chat-state', { detail: { state: value, micActive: continuous?.active === true, level: Math.max(0, Math.min(1, Number(level) || 0)) } }));
    }
    let continuous = null, responseTimer = 0, micLevel = 0, callOn = false, callMuted = false;
    let sttEpoch = 0, sttController = null;
    function micState(value, settings) {
      if (callOn && callMuted) value = 'muted';
      el('mute').disabled = !callOn || continuous?.pending === true;
      el('mute').textContent = callMuted ? 'Activar micrófono' : 'Silenciar micrófono';
      el('mute').setAttribute('aria-pressed', String(callMuted));
      el('talk').disabled = callOn;
      el('mic').dataset.state = value;
      if (value === 'active') status('Llamada activa · escuchando. Colgar cierra el micrófono.');
      else if (value === 'pending') status('Esperando permiso de micrófono…');
      else if (value === 'loading') status('Cargando VAD local…');
      el('mic').textContent = value === 'off' ? 'Micrófono cerrado' : value === 'pending' ? 'Esperando permiso · Colgar cancela' : value === 'loading' ? 'Micrófono activo · cargando VAD local…' : 'Micrófono activo · escucha también mientras MIA habla · AEC: ' + (settings?.echoCancellation === true ? 'solicitado/activo, no garantizado' : 'no confirmado');
      if (value === 'muted') el('mic').textContent = 'Llamada activa · micrófono silenciado y cerrado. No se graba; MIA puede seguir hablando.';
      else if (value !== 'off') el('mic').textContent = 'Llamada activa · ' + el('mic').textContent;
      el('continuous').textContent = callOn ? 'Colgar' : 'Llamar a MIA';
      // Keep the existing call buttons reachable even when Options is closed.
      const controls = el(callOn ? 'active-controls' : 'call-controls');
      if (el('continuous').parentElement !== controls) controls.append(el('continuous'), el('mute'));
      el('active-controls').hidden = !callOn;
    }
    import('/chat/voice/session.mjs').then(({ ContinuousVoice }) => {
      continuous = new ContinuousVoice({
        onMic: micState,
        onStart: () => { if (!callOn || callMuted) return; cancelResponse(); state('listening'); status('Nueva voz · respuesta interrumpida, escuchando…'); },
        onLevel: level => { micLevel = level; window.dispatchEvent(new CustomEvent('mia-audio-level', {detail:{channel:'input',level}})); if (!sttController && !controller && !busy && !audio) state('listening', level); },
        onEnd: async event => {
          if (!callOn || callMuted) return;
          cancelResponse(); const id = generation, sttId = ++sttEpoch; const current = new AbortController(); sttController = current;
          armResponseDeadline(id); state('transcribing'); status(event.reason === 'limit' ? 'Límite 20 s alcanzado · espera silencio para otra frase.' : 'Transcribiendo audio local…');
          const form = new FormData(); form.append('audio', new Blob([event.wav], { type: 'audio/wav' }), 'voice.wav');
          try {
            const data = await (await api('transcribe', form, current.signal)).json();
            if (sttId !== sttEpoch || id !== generation || callMuted || !callOn) return;
            if (typeof data.text !== 'string' || data.text.length > 4000) throw new Error('Transcripción inválida.');
            if (!data.text.trim()) { status('No se detectó texto. Escuchando…'); return; }
            void sendText(data.text.trim(), true);
          } catch (error) { if (sttId === sttEpoch && id === generation && error.name !== 'AbortError') showError(error); }
          finally { if (sttId === sttEpoch && id === generation) { clearTimeout(responseTimer); sttController = null; state('idle'); } }
        },
        onError: error => { stop(); status('Voz continua cerrada: ' + error.message + ' Puedes usar Hablar o texto.'); }
      });
      el('continuous').disabled = false;
    }).catch(() => { status('VAD local no disponible. Usa Hablar o texto.'); });
    el('continuous').addEventListener('click', () => {
      if (!authenticated || authBusy || !continuous) return;
      if (callOn) { stop(); status('Llamada finalizada · micrófono cerrado.'); return; }
      stop();
      // Both audio unlock and permission begin in this explicit user click.
      const Context = window.AudioContext || window.webkitAudioContext;
      if (Context && !audioContext) audioContext = new Context();
      audioContext?.resume().catch(() => {});
      callOn = true; callMuted = false; void continuous.start();
    });
    el('mute').addEventListener('click', () => {
      if (!callOn || !continuous || continuous.pending) return;
      callMuted = !callMuted;
      if (callMuted) {
        // Close capture entirely: no retained preroll or pending STT is sent on unmute.
        sttEpoch++; sttController?.abort(); sttController = null;
        if (!controller) clearTimeout(responseTimer);
        continuous.shutdown(); micLevel = 0; micState('muted');
      } else { void continuous.start(); } // Explicit click reacquires microphone.
    });
    function armResponseDeadline(id) {
      clearTimeout(responseTimer);
      responseTimer = setTimeout(() => { if (id === generation) { stop(); status('Tiempo de respuesta agotado. Micrófono cerrado; sin reintento automático.'); } }, 65000);
    }
    function cancelResponse() {
      cancelContext();
      cancelIdea(); cancelAnalysis(); cancelProposal(); cancelClientView();
      generation++; ttsEpoch++; speech?.cancel(); speech = null; cleanupAudio();
      sttEpoch++; sttController?.abort(); sttController = null;
      if (controller) controller.abort(); controller = null; busy = false;
      clearTimeout(responseTimer);
      el('compose').querySelector('button').disabled = false;
      state('idle');
    }
    function shutdownVoice() { callOn = false; callMuted = false; continuous?.shutdown(); cleanupMic(); micLevel = 0; micState('off'); }
    function stop() {
      shutdownVoice(); cancelResponse();
      if (audioContext) audioContext.close().catch(() => {}); audioContext = null;
    }
    el('stop').addEventListener('click', () => { if (callOn) cancelResponse(); else stop(); status('Respuesta detenida.'); });
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
      cancelResponse(); cleanupMic(); const id = generation; controller = new AbortController(); busy = true; armResponseDeadline(id);
      el('compose').querySelector('button').disabled = true;
      lastUserText = text; el('input').value = ''; addMessage('user', text);
      const message = addMessage('assistant', ''); let answer = '';
      const voiceWanted = callOn || (fromVoice && el('autoread').checked);
      let spokenInput = '';
      state('thinking'); status('Qwen está respondiendo…');
      try {
        if (voiceWanted) { await speechReady; if (id !== generation) return; speech = newSpeech(id, message); }
        const response = await api('message', { text }, controller.signal);
        if (id !== generation) { await response.body?.cancel(); return; }
        await consume(response, id, (type, part) => {
          if (id !== generation) return;
          if (el('stage')) el('stage').textContent=type==='delta'?'Modelo · texto recibido por stream':'Modelo · texto final recibido';
          answer = type === 'done' ? part : answer + part;
          if (answer.length > 32000) throw new Error('Respuesta demasiado larga.');
          message.content.textContent = answer;
          if (voiceWanted) {
            if (type === 'delta') { speech?.push(part); spokenInput += part; }
            else if (part.startsWith(spokenInput)) speech?.push(part.slice(spokenInput.length), true);
            else { speech?.cancel(); status('El texto final cambió; lectura detenida. Consulta el texto final.'); }
          }
          el('history').scrollTop = el('history').scrollHeight;
        });
        if (id === generation) { status('Respuesta completada.'); readButton(message); }
      } catch (error) {
        if (id === generation && error.name !== 'AbortError') showError(error);
      } finally {
        if (id === generation) { clearTimeout(responseTimer); busy = false; controller = null; el('compose').querySelector('button').disabled = false; if (!speech?.running) state('idle'); }
      }
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
    function expand(value, focus = true) {
      if (!value) stop();
      el('panel').hidden = !value;
      el('toggle').hidden = value;
      el('toggle').setAttribute('aria-expanded', String(value));
      if (focus) (value ? el('input') : el('toggle')).focus();
    }
    el('toggle').addEventListener('click', () => expand(true));
    el('minimize').addEventListener('click', () => expand(false));
    window.addEventListener('mia-view-change', event => {
      if (event.detail?.view !== 'dashboard') expand(false, false);
    });
    root.addEventListener('keydown', e => {
      if (e.key !== 'Escape' || e.isComposing) return;
      const details = e.target.closest('details[open]') || el('options').closest('details[open]');
      if (details) { details.open = false; details.querySelector('summary').focus(); }
      else expand(false);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
