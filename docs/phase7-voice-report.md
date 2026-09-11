# Fase7 — voz continua y barge-in, entrega experimental desplegada

## Resultado

Desplegados **16 archivos** mediante `server/deploy_voice7.py`, preservación selectiva **`/root/jarvis-voice7-rollback-20260908T184623Z`**. Index y fuego Fase6 intactos; no cambios a Nginx, Cloudflare, API, modelos, servicios, credenciales ni executor. Rama apilada sobre `feat/jarvis-volumetric-fire` / PR5, baseline Git `e8831ee67c0b118785dac066530a4c93fbd45656`.

**GO técnico limitado: modo opt-in experimental con auriculares recomendados, no GO acústico para altavoces ni aceptación global.** Login/logout positivo del propietario y pruebas físicas de micro/auriculares/altavoces continúan pendientes. No se ha solicitado permiso físico ni introducido credenciales reales en QA.

## Comportamiento publicado

- `Iniciar conversación` es el único inicio del modo continuo: permiso explícito con AEC/noiseSuppression/autoGainControl; nada se activa por login, Leer o carga de modelo. El fallback manual `Hablar` conserva su propio clic y MediaRecorder.
- Indicador de micrófono independiente del estado pensando/transcribiendo/hablando; Finalizar, Salir/sidebar, 401, pagehide, minimizar/Escape, errores y deadlines cierran tracks. Una concesión tardía tras cierre también los termina. BFCache no reactiva escucha.
- `cancelResponse()` pausa HTMLAudio, revoca URL, resuelve playback pendiente, invalida generación y aborta fetch antes de esperar STT. No detiene el micrófono continuo ni borra pre-roll. `shutdownVoice()` sí cierra la captura.
- Silero v5 ONNX + ORT1.22 WASM CPU de **un hilo**, locales y tras puerta autenticada. No usa MicVAD stock, `startOnLoad`, RMS como VAD ni colas stock. Worker secuencial; máximo4 frames enviados/no confirmados, error fail-closed ante overflow o watchdog. AudioWorklet transmite PCM, su salida es cero y gain0 (no monitor audible de entrada).
- Segmentador: frames512 a16kHz, confirmación3 frames p≥.65, pre-roll16frames/512ms, cierre22frames p<.35/704ms. Máximo320000 muestras **incluyendo** pre-roll y cola; al límite se emite una frase y espera silencio para rearmar.
- WAV PCM16 mono16k, máximo640044bytes, bajo límite2MiB backend. PCM de frase acotado a1.28MB y ring pequeño; no copia de todos los chunks para aplanarlos. **2MiB es límite de upload, no de RSS total del navegador/ONNX**; runtime, TTS y copias de Blob/fetch tienen memoria adicional. No persistencia de audio en storage/logs de la aplicación.
- Fin automático → `transcribe` autenticado+CSRF → SSE Qwen → TTS automático → escucha; sin reintentos automáticos. 429/busy/error termina la conversación con aviso. Texto y Leer/Detener siguen disponibles; Detener en continuo interrumpe solo la respuesta, Finalizar cierra el micrófono.
- Carga/permisos20s, watchdog de frames2s, deadline de respuesta65s; frontend no cambia deadlines/locks backend. AbortController **no demuestra cancelación inmediata del cómputo Qwen/Piper**. TTS por frases seriales después de completar SSE; streaming TTS temprano no incluido.

## Eco y límites honestos

El aviso visible dice experimental/auriculares y que AEC/VAD no garantizan evitar auto-interrupciones con altavoces. El fixture nativo es sintético y el HTMLAudio real está muted: prueba captura, inferencia y pausa real, **no AEC ni double-talk acústico**. El spike mostró que Piper atenuado/retrasado también dispara Silero: VAD no es antieco. No se promete latencia tipo GPT, rendimiento móvil ni ausencia de pérdida de sílabas físicas.

Assets runtime:13606961bytes, hashes/versiones en [manifest](../chat/voice/assets-manifest.json). MIT ONNX/Silero, ISC procedencia vad-web y ThirdPartyNotices ORT conservados. No descarga a CDNs en runtime de voz; no cambios a COOP/COEP/CSP global.

## Pruebas ejecutadas

- `node --test tests/voice_capture.test.mjs tests/voice_core.test.mjs tests/voice_session.test.mjs tests/voice_worker.test.mjs tests/core_activity.cjs tests/stt_core.cjs tests/fire.test.cjs`: exit 0. [test-0.txt](evidence/phase7/test-0.txt)
- `python3 tests/chat_frontend_test.py`: exit 0 · 14 tests (includes inherited cases). [test-1.txt](evidence/phase7/test-1.txt)
- `python3 tests/stt_frontend_test.py`: exit 0 · 33 tests (includes inherited cases). [test-2.txt](evidence/phase7/test-2.txt)
- `python3 tests/access_gate_test.py`: exit 0 · 16 tests (includes inherited cases). [test-3.txt](evidence/phase7/test-3.txt)
- `python3 tests/access_browser_test.py BrowserAccess`: exit 0 · 1 tests (includes inherited cases). [test-4.txt](evidence/phase7/test-4.txt)
- `python3 tests/stt_backend_test.py`: exit 0 · 24 tests (includes inherited cases). [test-5.txt](evidence/phase7/test-5.txt)
- `xvfb-run -a python3 tests/voice_barge_in_test.py VoiceBargeIn`: exit 0 · 1 tests (includes inherited cases). [test-6.txt](evidence/phase7/test-6.txt)
- `php -l api/chat.php`: exit 0. [test-7.txt](evidence/phase7/test-7.txt)
- `php -l server/gate.php`: exit 0. [test-8.txt](evidence/phase7/test-8.txt)
- `php -l server/session.php`: exit 0. [test-9.txt](evidence/phase7/test-9.txt)
- `php -l server/transcribe.php`: exit 0. [test-10.txt](evidence/phase7/test-10.txt)

Runner: `python3 tests/run_phase7.py` (suites backend secuenciales por directorio fixture compartido). [Registro y hashes de fuentes verificadas](evidence/phase7/tests.json). Se actualizaron helpers/asserts legacy al formulario público, sin eliminar cobertura de SSE/seguridad/TTS/MediaRecorder; esos doubles siguen siendo fixtures, no auth/modelo de producción.

### Navegador real, GUI aislada

`JARVIS_HEADFUL=1 xvfb-run -a python3 tests/voice_barge_in_test.py VoiceBargeIn`: página completa Fase6 con Chromium ANGLE SwiftShader + login PHP real contra MC fixture. Worker/ONNX/Worklet y HTMLAudio nativos. Model/STT/TTS responses de esta prueba están explícitamente etiquetadas fixtures; el audio WAV es Piper generado previamente. Stats es fixture y Three local vendorizado solo en QA.

3 uploads validados WAV, un permiso inicial, doble interrupción conserva tracklive, retorno a escucha tras TTS sin nuevos uploads, tono440Hz/silencio no envían, stale STT ignorado, timeout, denegación/permiso tardío, worker404,429 sin retry,401 real PHP, logout/sidebar y controles móvil. [JSON](evidence/phase7/browser.json), [mic activo](evidence/phase7/continuous-active.png), [móvil](evidence/phase7/continuous-mobile.png).

Medición **solo este host/SwiftShader y fuente sintética**, no latencia humana: 938 frames, round-trip Worker p95 3.70ms, máximo 102.70ms; máximo pendientes 4; inyección→pausa observada [238, 288.09999990463257]. El presupuesto de4 frames puede cerrar voz bajo carga pesada; se prefiere fallo explícito a acumular audio.

### Whisper real y revisión Qwen real

`python3 tests/voice_real_stt_check.py`: **dos WAV reales**, del spike y del navegador de esta integración, transcritos por worker existente Hetzner `taskset -c1 /opt/jarvis-stt/venv/bin/python /opt/jarvis-stt/stt_worker.py`. Ambos devolvieron “Hola, soy Jardis. El núcleo azul está conectado. Puedes escribirme y escuchar mis respuestas en español.” (error real Jardis por Jarvis, no corregido en evidencia). ~2.2–2.3s incluyendo SSH/proceso. [Resultados/hash](evidence/phase7/real-stt.json). Prueba directa del worker **no** login de propietario ni HTTP STT autenticado de producción; su contrato HTTP se prueba con PHP+fixtures.

Una revisión Qwen real de33s está archivada [aquí](evidence/phase7/qwen-review.json). **Se rechazaron sus5 hallazgos por contradicción con la fuente**: pending guard ya precede getStream; cleanup opcional ya existe; límite dequeue ya precede push; shutdown termina Worker y failed bloquea emisiones tardías; Worklet ya publica error y existe watchdog. No se aplicaron “fixes” incorrectos ni se toma Qwen como certificado. Pruebas independientes de esas propiedades pasan.

RED→GREEN observado en tool output: segmentador ausente, Worklet ausente, Worker ausente, sesión ausente, botón continuo ausente; después memoria sin flatten duplicado y estado de error obsoleto al reactivar. La inspección PNG detectó este último, se añadió assert que falló y se corrigió antes de publicar.

## Verificación producción y seguridad

- `python3 tests/voice_public_check.py`: **42 probes** edge/origen; / e index303, login200, todos los assets nuevos/anteriores, stats y shader401. [Evidencia](evidence/phase7/anonymous.json). No cambio/purge de Cloudflare.
- Hashes SSH **18/18** coinciden (16publicados+index/fire preservados). [Hashes](evidence/phase7/live-hashes.json), [deploy manifest](evidence/phase7/deployment-manifest.json).
- `python3 tests/voice_public_browser.py`: navegador público redirige a login;1formulario,0chat/0canvas privado,0errores,0intentos login. [PNG](evidence/phase7/public-login.png).
- Gate prueba13 assets nuevos con MIME real, bytes/hash autenticados y401 antes/después logout mediante PHP y MC fixture. Licencias también privadas. El gate nunca entrega HTML de login para importar .mjs/.wasm/.onnx.
- No bypass de sesión de producción. Prueba positiva del propietario y circuito completo **real** mic→STT HTTP→Qwen→Piper en su sesión siguen pendientes.

## Archivos publicados exactos

| Fuente repo | Destino producción |
|---|---|
| `chat/voice/assets/ort-wasm-simd-threaded.mjs` | `/var/www/dashboard/chat/voice/assets/ort-wasm-simd-threaded.mjs` |
| `chat/voice/assets/ort-wasm-simd-threaded.wasm` | `/var/www/dashboard/chat/voice/assets/ort-wasm-simd-threaded.wasm` |
| `chat/voice/assets/ort.wasm.min.js` | `/var/www/dashboard/chat/voice/assets/ort.wasm.min.js` |
| `chat/voice/assets/silero_vad_v5.onnx` | `/var/www/dashboard/chat/voice/assets/silero_vad_v5.onnx` |
| `chat/voice/assets-manifest.json` | `/var/www/dashboard/chat/voice/assets-manifest.json` |
| `chat/voice/capture.js` | `/var/www/dashboard/chat/voice/capture.js` |
| `chat/voice/core.mjs` | `/var/www/dashboard/chat/voice/core.mjs` |
| `chat/voice/onnxruntime-ThirdPartyNotices.txt` | `/var/www/dashboard/chat/voice/onnxruntime-ThirdPartyNotices.txt` |
| `chat/voice/onnxruntime-license.txt` | `/var/www/dashboard/chat/voice/onnxruntime-license.txt` |
| `chat/voice/session.mjs` | `/var/www/dashboard/chat/voice/session.mjs` |
| `chat/voice/silero-license.txt` | `/var/www/dashboard/chat/voice/silero-license.txt` |
| `chat/voice/vad-license.txt` | `/var/www/dashboard/chat/voice/vad-license.txt` |
| `chat/voice/worker.js` | `/var/www/dashboard/chat/voice/worker.js` |
| `server/gate.php` | `/opt/jarvis-access/gate.php` |
| `chat/chat.css` | `/var/www/dashboard/chat/chat.css` |
| `chat/chat.js` | `/var/www/dashboard/chat/chat.js` |

Fuentes de pruebas añadidas: `.gitattributes` marca assets vendorizados y conserva sus bytes/hash (incluido whitespace upstream); `tests/voice_{core,capture,worker,session}.test.mjs`, `tests/voice_barge_in_test.py`, `tests/run_phase7.py`, `tests/voice_public_{check,browser}.py`, `tests/voice_real_stt_check.py`, `tests/fixtures/voice-check.wav`. Modificados `tests/access_gate_test.py`, `tests/chat_frontend_test.py`. Herramientas nuevas `server/deploy_voice7.py`, `server/rollback_voice7.py`; este informe y `docs/evidence/phase7/*`. Sin modificar `index.html`, `fire/shaders.js`, `chat/core-state.js` ni API de producción.

## Reversión selectiva

`python3 server/rollback_voice7.py --check` se ejecutó y verificó originales y hashes vivos, sin restaurar. [Resultado](evidence/phase7/rollback-check.json). Con autorización de reversión, `python3 server/rollback_voice7.py --apply` restaura chatJS/CSS/gate anteriores y retira solo los13 assets nuevos; aborta ante drift. Conserva index/fire y acceso único Fase5. No reinicia servicios ni toca Nginx/CF. No usar main ni una reversión Fase5 que reabra acceso público.

## Aceptación pendiente

Propietario: entrar normalmente, usar auriculares, Iniciar conversación, interrumpir dos respuestas, comprobar sílabas y cierre del indicador tras Finalizar/Salir. Altavoces: validar TTSsolo (cero auto-STT), double-talk, volumen/distancia/reverberación y navegadores objetivo. Si hay eco, finalizar y usar Hablar; no hay fallback RMS silencioso. Rendimiento físico/móvil y aceptación estética Fase6 pendientes.
