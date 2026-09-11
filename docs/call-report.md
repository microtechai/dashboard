# Llamada MIA — endurecimiento y voz femenina desplegados

## Resultado vigente

GO autorizado aplicado en `feat/jarvis-call-streaming`, apilada sobre `feat/jarvis-continuous-voice` / PR6, baseline `445ca76f4d25291ebc7efeb6d22582eaf275c398`. **No se modificaron index, reactor/shader, Nginx, Cloudflare, servicios, GPU, MC ni executor.** Se preservó el trabajo previo, sin reset; [informe anterior archivado](call-initial-report.md).

En esta continuación se publicaron solo **3 archivos**: `chat/chat.js`, `chat/voice/core.mjs`, `api/chat.php`. Backup selectivo `/root/jarvis-call-rollback-20260908T205803Z`; [manifiesto y hashes](evidence/call/deployment-manifest.json). La entrega previa de seis archivos sigue reflejada en [manifiesto inicial](evidence/call/deployment-initial.json). El gate sigue idéntico a ese despliegue y no se reescribió en el endurecimiento.

Además se activó **es_ES-sharvard-medium, speaker 1 (F)** en configuración privada. No se cambió proveedor, no se descargó otra vez el modelo ni se reinició nada. Modelo estable `/opt/jarvis-tts/models/mia-sharvard/es_ES-sharvard-medium.onnx`; directorio root:www-data0750, pesos/JSON0640. `/etc/jarvis-chat/config.php` conserva root:www-data0640, backup selectivo `/root/mia-voice-rollback-20260908T205804Z`. No modelos, secretos ni muestras nuevas en webroot. [Prueba viva](evidence/call/female-live.json), [atribución Sharvard/Piper y CC BY 3.0](mia-voice-attribution.md).

## Causas y RED → GREEN

- **Interrupciones por falsas probabilidades:** el segmentador previo solo requería probabilidad≥0.65 durante96ms; no contrastaba nivel relativo. `node --test tests/voice_noise.test.mjs` falló con `1 !== 0`: confianza neural falsa a nivel del suelo de ruido iniciaba una respuesta. Se añadió estimación de suelo solo en no-voz neural, suavizada0.95/0.05 y acotada0.0005–0.01; inicio requiere probabilidad≥0.65 **y** RMS≥max(0.002,2.5×suelo),4frames/128ms. No es detector RMS-only, ni filtro que elimine todo ruido del WAV. El navegador ya solicitaba AEC/noiseSuppression/autoGainControl; los tres siguen solicitados y comprobados. Su cumplimiento físico no está demostrado.
- Histéresis de salida probabilidad<0.35,704ms de silencio; pre-roll512ms incluyendo confirmación; cap20s/320000muestras y cola16frames con ACK permanecen. La confirmación aumenta solo32ms, no un bloqueo largo. El test de seam demuestra rechazo de golpes de96ms y dos inicios de voz dentro de128ms de evidencia, preservando onset débil en pre-roll. El fixture heredado de20s pasó de PCM cero con probabilidad0.99 a PCM audible: silencio con confianza errónea ya no debe iniciar frase.
- **Auto-TTS:** la voz reconocida en llamada ya se leía sin checkbox, pero un mensaje escrito durante llamada no. El test de SSE real/HTMLAudio falló por ausencia de audio antes del final. Ahora `callOn || (fromVoice && checkbox)` hace que toda respuesta en llamada se hable, incluso durante mute. Checkbox solo rige `Hablar (manual)`, alternativa secundaria explícita, deshabilitada durante llamada. No hay fallback automático.
- **Identidad:** prueba backend falló porque sistema decía `Eres Jarvis`. Ahora dice **MIA, la asistente de MicrotechAI**, y reconoce reproducción local de texto; mantiene no herramientas/no comandos/no acceso a sistemas. No se renombran IDs/cookies/modelos ni se reescribe contenido histórico.
- **Speaker femenino:** prueba PHP real/CLI-fixture falló por ausencia de `--speaker`. Backend usa un argumento fijo derivado exclusivamente de configuración privada, entero0–255; `--speaker 1` real comprobado. Strings, shell payload, negativos, flotantes, bool y fuera de rango no lanzan proceso. Los parámetros del usuario no configuran modelo/speaker. Config inválida503; sin cambios de presupuesto backend.

## Contrato y límites que se mantienen

- Clic explícito para captura, nunca por login/render/Leer. Permiso tardío termina tracks si la llamada ya cerró.
- Barge-in cancela audio/SSE/TTS y generaciones obsoletas sin apagar el micrófono. Mute cierra tracks/worklet/worker/contexto, descarta pre-roll/STT; la respuesta sigue hablando. Unmute requiere clic y nueva captura. Colgar, logout/sidebar,401, pagehide, minimizar, error y timeout cierran captura.
- **Máximo3 solicitudes TTS por respuesta,1000caracteres cada una**, una en vuelo, hasta2 bloques pendientes. Texto completo visible, aviso persistente cuando el resto no se sintetiza; sin truncación silenciosa ni reintentos429. Backend **6STT/min,6mensajes/min,20TTS/min** intacto. Abort del navegador no certifica cancelación inmediata de cómputo servidor.
- Voz derivada del contenido, no autor/Leer/HTML. Normalización conservadora de Markdown/badges, preservación de números, decimales y código. No parser completo CommonMark.

## Verificación ejecutada

`python3 tests/run_call.py`: **16 comandos PASS,122 invocaciones de tests**, incluyendo herencia/duplicación legacy, NO122 casos nuevos independientes. [Comandos, timestamps, logs y hashes exactos](evidence/call/tests.json). Incluye Node17, frontend18, STT frontend33, gate/backend16, login1, STT backend24, navegador nativo1, backend/speaker12, PHP/JS syntax.

Ensayo reautorizado `JARVIS_HEADFUL=1 xvfb-run -a python3 tests/call_barge_in_test.py VoiceBargeIn`: PHP/login/gate reales contra MC fixture; ONNX Silero/Worker/AudioWorklet/HTMLAudio/WebAudio reales en Chromium/SwiftShader. **Audio sintético, HTMLAudio muted, APIs modelo/STT/TTS fixtures; ningún permiso de micro físico ni credencial real.** Snapshot legacy vivo incluido, sin botón legacy ni inicio WebSpeech por Ctrl+M. No se atribuye al legacy un conflicto real no observado.

Casos comprobados: ruido blanco determinista + golpes + tono antes y durante reproducción **no interrumpen**; residuo de habla sintético de ganancia0.0005 no activa; voz normal sí interrumpe dos respuestas;3WAV uploads; autoTTS con checkbox apagado; mute/unmute, permiso tardío/denegado, staleSTT, worker404, timeout,429sinloop,401PHP/logout y controles móviles. **El residuo atenuado no es prueba de AEC ni equivale a eco a volumen de altavoz**: habla sintética fuerte se reconoce como voz y puede interrumpir. [JSON navegador](evidence/call/browser.json).

Inspección visual de PNG: controles desktop/móvil dentro del panel; reactor anterior conservado. [MIA activa](evidence/call/continuous-active.png), [silenciada](evidence/call/call-muted.png), [móvil](evidence/call/continuous-mobile.png). No se afirma aceptación visual del propietario.

### Mediciones observadas, sin mezclar ámbitos

| Ámbito | Resultado |
|---|---:|
| SSE controlado local, primer HTMLAudio observado desde primer delta |64.10ms|
| Mismo fixture, final SSE observado |151.40ms|
| ONNX/Worklet1115frames, roundtrip p95 / máximo |3.90 /72.80ms|
| Máximo PCM pendiente observado |3 de16|
| Inyección sintética → pausa observada, dos interrupciones |**766.10 /216.10ms**|
| Whisper real CPU1 sobre WAV sintético conocido |1.4266s|
| Qwen real revisión: primer contenido / final |3.6004 /3.7825s|
| Piper anterior Davefx, primera salida de revisión, CPU0 |0.9732s|
| Piper femenino vivo como www-data, texto MIA, CLI / WAV |1.3098s /5.9675s|
| Piper femenino vivo como www-data, números, CLI / WAV |1.2182s /4.4931s|

[Streaming](evidence/call/stream-timing.json) prueba concurrencia con SSE aún abierto, **no ahorro end-to-end de producción**; tiempos observados por harness incluyen planificación y acciones de prueba. Las pausas son variables: no se oculta la de766ms ni se promete latencia universal. Pre-roll/primeras sílabas se comprueban en fixtures, no oído humano.

[Etapas reales baseline](evidence/call/real-measure.json): una revisión Qwen después de métricas running/waiting0, `SIN HALLAZGOS.`; primer punto+espacio ausente, `first_sentence_seconds:null`. Es revisión pesada, **no benchmark conversacional/TTFA**, ni certificación. Se ejecutó antes del pequeño cambio speaker posterior; no se hizo otra petición Qwen para voz. Transcripción real contiene error “Jardis”, no corregido en prueba. No reinicio GPU/modelo.

[Female-live](evidence/call/female-live.json): dos procesos CPU0, un hilo, **como www-data**, leyendo modelo/speaker de configuración viva; mismos textos que evaluación previa. WAV mono22050Hz reales y argv/hash registrados; temporales eliminados. Tiempo CLI incluye carga de modelo, no primer audio. `voice-default.wav`/`voice-pace-090.wav` de la evaluación baseline son **Davefx masculino**, no muestras de la nueva voz. Las muestras femeninas de audición están fuera del repo en `/home/ddr/mia-female-voice-evaluation/`.

## Acceso, secretos, rollback

- `python3 tests/call_public_check.py`: **44 probes edge/origen PASS**: HTML303→login200, assets privados actuales/anteriores401; **10hashes remotos coinciden** incluyendo gate y index/fire preservados. [Anónimo](evidence/call/anonymous.json), [hashes](evidence/call/live-hashes.json).
- `python3 tests/call_public_browser.py`: login público,1form,0chat,0canvas,0errores, sin intento de login/permiso. [Prueba](evidence/call/public-browser.json).
- `python3 tests/call_secret_scan.py`: firmas de tokens/llaves/URLs credenciales en candidatos UTF8, sin hallazgos. No es garantía exhaustiva; WAV/PNG fixtures no se escanean como texto. Ninguna configuración privada copiada al repo.
- `python3 server/rollback_call.py --check` y `python3 server/rollback_mia_voice.py --check`: PASS sin restaurar. Para revertir con autorización: **primero voz privada**, luego3archivos de esta continuación. Modelos quedan privados, no se borran datos previos. El rollback inicial anterior sigue archivado y no debe aplicarse sobre hashes posteriores sin coordinarlo. No backup completo ni restart.

**GO técnico acotado, experimental con auriculares; NO GO acústico/global.** Pendientes: login positivo/micrófono del propietario, altavoces y double-talk real, móviles físicos, aceptación de sílabas/prosodia/naturalidad. Integración visual del reactor/barra por separado, no realizada en este alcance.
