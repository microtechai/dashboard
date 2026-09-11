# Registro histórico anterior al endurecimiento y voz femenina

No describe el estado final; ver [informe vigente](call-report.md).

# Llamada MIA — pipeline incremental, entrega acotada

## Resultado y alcance

GO del usuario aplicado. Publicados **6 archivos**, con preservación selectiva `/root/jarvis-call-rollback-20260908T200351Z` y guardas de hashes. Rama apilada `feat/jarvis-call-streaming` sobre Fase7 `feat/jarvis-continuous-voice`, baseline `445ca76f4d25291ebc7efeb6d22582eaf275c398`. **No cambia el diseño/reactor**: índice y shader Fase6 intactos. Sin cambios a Nginx, Cloudflare, proveedores, modelos, API, límites backend, servicios, GPU ni executor.

La última dirección del usuario se aplica a los controles propios: **MIA**, `Llamar a MIA`, `Colgar`, `Silenciar micrófono` / `Activar micrófono`; autor de mensajes y encabezado MIA. IDs, cookies, archivos y mensajes históricos no se renombran. **Pendiente del parent en la integración de identidad:** `api/chat.php:95` aún contiene `Eres Jarvis`; no se amplió este despliegue al backend. El branding global/reactor central aprobado queda fuera de esta entrega y no se ha tocado su maqueta.

## Diagnóstico, sin atribuir una causa física no observada

1. Fuente viva `chat/chat.js` Fase7 coincidía con SHA256 `16fb9438052638fcd37c8db0da421051bf0d5313f8f6e3ea2cfe24807f5fb74f`. `Hablar` era un MediaRecorder manual por clic; coexistía como acción ordinaria con `Iniciar conversación`. La prueba de UI falló contra el contrato nuevo: estos controles no expresaban la llamada como acción primaria. Esto demuestra la diferencia de UX, **no cuál pulsó el propietario**.
2. El fixture SSE controlado mantuvo abierta la respuesta tras una primera frase completa: no se creaba audio. Fuente confirmada: `await consume(...)` antes de `speak(answer)`. El mismo ensayo ahora reproduce audio mientras SSE sigue abierto y su AbortSignal permanece vivo.
3. El navegador completo con ONNX/Worklet reales reprodujo fallos intermitentes `VAD sobrecargado` con el margen anterior de cuatro frames, tanto en baseline como durante integración. También llegó a completar tres frases y doble barge-in: no es ausencia absoluta de escucha continua. No se ha probado que fuera la causa del caso del propietario.
4. Se amplió **solo el transporte PCM acotado** de4 a16 frames pendientes, manteniendo ACK tras inferencia secuencial y cierre fail-closed al frame17. Pruebas RED→GREEN verifican el nuevo límite y rechazo del excedente. En la ejecución final hubo máximo5 pendientes: una ráfaga que ya excede el margen anterior. Esto aporta tolerancia a planificación/carga, no una garantía bajo cualquier saturación. Watchdog2s, pre-roll512ms, confirmación96ms, silencio704ms y máximo20s de frase permanecen.

## Contrato de llamada y privacidad

- Solo clic explícito inicia permiso/captura. Sin arranque por login, render, Leer o recuperación de error.
- Micrófono continuo entre frases, durante STT/modelo/TTS y al interrumpir dos respuestas. `cancelResponse` pausa HTMLAudio, revoca URL, invalida generaciones y aborta solicitudes sin parar captura.
- Silenciar **cierra tracks, Worklet, Worker y contexto de captura**, borra frase/pre-roll e invalida STT pendiente; la respuesta ya en curso puede continuar. No se captura ni se conserva audio para envío posterior mientras está silenciado. `Activar micrófono` es otro clic explícito que adquiere una captura nueva; no usa una reactivación silenciosa.
- Colgar, Salir/sidebar, pagehide,401, error y deadline cierran la llamada. Permiso tardío tras cierre se termina. Minimizar/Escape sigue colgando, así no queda una llamada oculta.
- Indicador de llamada/micrófono independiente de pensando/transcribiendo/hablando. `Hablar (manual)` es alternativa explícita secundaria y está deshabilitada durante la llamada; hay que colgar primero. No fallback automático.
- STT continuo tiene controller/epoch separados del modelo; TTS tiene queue/controller/epoch y deadline propios. El final STT no espera ni limpia el pipeline de modelo/TTS. La prueba de STT pendiente verifica que un frame de nivel no falsea su estado y que mute no manda transcripción obsoleta.

## Texto frente a voz, streaming y presupuesto

`chat/voice/speech.mjs` nunca procesa HTML ni consulta etiquetas de UI. Deriva voz exclusivamente del contenido del mensaje. Normaliza títulos/listas, Markdown de énfasis, enlaces, backticks y una lista conservadora de badges decorativos iniciales; preserva números, decimales, porcentajes, operadores de código, palabras como `icono` y emoji con significado. El contenido visible original permanece mediante `textContent`; no se reinterpretan mensajes HTML/SVG ni se importan bibliotecas de iconos. No es un parser completo de CommonMark ni pretende resolver todas las abreviaturas humanas.

La primera frase completa puede comenzar antes de `done`; se espera lookahead para no cortar `3.14`, `Sr.`, `Dr.` o `P. ej.`. Las frases posteriores se agrupan en bloques de hasta1000caracteres. **Máximo3 solicitudes TTS por respuesta, una en vuelo y hasta2 bloques pendientes**; se descarta inmediatamente lo pendiente al barge-in. Si una frase sola supera1000caracteres o se agota el presupuesto, se detiene la producción de voz y se muestra aviso persistente en el mensaje: el resto permanece íntegro en texto. No se fracciona código/número arbitrariamente para forzar audio. Esto es una limitación explícita, no voz ilimitada.

No se cambian los límites backend20TTS/min,6mensajes/min,6STT/min. El cliente añade también ventana20TTS/min para Leer repetido.429/red/error no generan reintentos ni bucles de autoenvío. Abort del navegador **no demuestra cancelación inmediata del cómputo** Qwen/Piper servidor. Los resultados `done` incompatibles con los deltas cancelan la voz para no duplicar un texto final diferente.

## Pruebas ejecutadas y evidencias

`python3 tests/run_call.py`: **15 comandos PASS**,109 invocaciones de tests (incluyen herencia/duplicación legacy; no109 casos nuevos independientes), más validaciones sintácticas en esos comandos. [Manifiesto completo](evidence/call/tests.json), logs `test-0.txt` a `test-14.txt` con comandos, timestamps, duración y hash exacto de cada fuente desplegada.

- Node16: normalización, decimal/abreviatura, cola larga acotada, doble cancelación,429/red sin retry, Worklet/Worker bounded fail-closed, segmentación/lifecycle/core/fire.
- Frontend18: UI MIA, SSE aún abierto mientras HTMLAudio reproduce, mute sin cancelar modelo, pendingSTT inválido, salida larga visible/aviso, no lectura de autor/Leer, XSS/render seguro, respuestas obsoletas, bloqueo de audio, logout y errores. Son APIs/captura dobles **declarados**, no producción autenticada.
- STT frontend33, gate/backend16, login navegador1, backendSTT24, navegador nativo1. Las suites heredadas conservan sus coberturas; la prueba de lectura completa ahora usa1400caracteres dentro del presupuesto y se añade otra de respuesta extensa con límite explícito.
- `JARVIS_HEADFUL=1 xvfb-run -a python3 tests/call_barge_in_test.py VoiceBargeIn`: PHP/login/gate reales contra MC fixture, Chromium/SwiftShader completo, ONNX/Worklet/HTMLAudio nativos, WAV sintético previamente generado con Piper. **HTMLAudio muted; no permiso de micrófono físico, no AEC acústico validado.** Tres uploads WAV comprobados; doble barge-in; silencio/tono no autoenvían; mute termina tracks, audio inyectado mientras muted no genera upload, unmute por clic adquiere una vez; staleSTT, timeout, denegación, permiso tardío, worker404,429 sin loop,401PHP y sidebar logout.
- [Navegador JSON](evidence/call/browser.json), [MIA activa](evidence/call/continuous-active.png), [micrófono silenciado](evidence/call/call-muted.png), [móvil](evidence/call/continuous-mobile.png). Inspección visual real sin nuevos cambios al diseño.

Medición final del **fixture local/SwiftShader**, no oído humano:949frames, roundtrip Worklet→Worker→main p95 **7.30ms**, máximo **75.10ms**, máximo5pendientes. Inyección sintética→pausa observada **263ms y428ms**. No son garantía, benchmark móvil ni máximo universal de latencia de llamada.

## STT, Qwen y Piper reales; voces

`python3 tests/call_real_measure.py`: llamada directa privada por SSH al worker existente CPU1, endpoint Qwen loopback existente y Piper CPU0. **No autentica una sesión pública del propietario ni sustituye un circuito físico mic→HTTPSTT→Qwen→Piper.** Inputs/outputs, todos los deltas Qwen y timestamps ISO están en [real-measure.json](evidence/call/real-measure.json).

| Etapa real observada | Tiempo |
|---|---:|
| Whisper CPU1, WAV sintético conocido |1.4831s|
| Qwen revisión de fuentes, primer contenido |3.2598s|
| Qwen revisión completa |3.9463s|
| Piper CPU0, primera salida textual de esa revisión |1.0855s|

Whisper devolvió realmente “Hola, soy **Jardis**…”; error conservado, no corregido en la evidencia. Qwen revisó código real y respondió `SIN HALLAZGOS`; eso **no es certificación** y no reemplaza pruebas/revisión independiente. Métricas running/waiting0 comprobadas inmediatamente antes de la única solicitud. No hubo solapamiento observado, cambio/reinicio de modelo ni petición a proveedor de pago. Una corrección posterior pequeña de estado STT y labels MIA está respaldada por regresiones, no por una segunda revisión Qwen.

La revisión no produjo un punto+espacio antes de terminar: `first_sentence_seconds:null` es honesto; no se inventa tiempo. El benchmark es serial por etapas y de revisión pesada, **no un ahorro end-to-end medido de streaming**. La concurrencia real del frontend se demuestra con SSE/Audio del fixture separado.

Solo hay **una voz española instalada**: `es_ES-davefx-medium`,22050Hz,1speaker. Configuración existente: length_scale1, noise_scale0.667, noise_w0.8. Sin instalaciones ni cambios de voz de producción. Comparación local del mismo texto/voz: [actual](evidence/call/voice-default.wav),5.2013s de audio, síntesis1.2666s; [ritmo0.90](evidence/call/voice-pace-090.wav),4.9110s de audio, síntesis1.2126s. Es una comparación de ritmo, **no de identidades vocales ni prueba de naturalidad**. Esas muestras se generaron antes de la última dirección MIA y contienen el nombre anterior; no se alteró un WAV fingiendo que dice MIA. Elegir prosodia requiere escucha del propietario; proveedor/modelo no cambiados.

## Producción, reversión y límites de aceptación

- `python3 tests/call_public_check.py`: **44 probes edge/origen PASS**: HTML303→login, login200, assets nuevos/anteriores401.8/8 hashes SSH coinciden (6publicados+index/fire preservados). [anónimo](evidence/call/anonymous.json), [hashes vivos](evidence/call/live-hashes.json), [manifiesto desplegado](evidence/call/deployment-manifest.json).
- `python3 tests/call_public_browser.py`: pública redirige a login,1formulario/0chat/0canvas/0errores, ningún intento de login ni permiso. [JSON](evidence/call/public-browser.json).
- `python3 server/rollback_call.py --check`: PASS, solo verifica originales/hashes. Con autorización, `--apply` restaura5archivos previos y elimina solo `speech.mjs`; aborta ante drift. **No se ejecutó reversión.** [check](evidence/call/rollback-check.json).
- Runtime exacto: `chat/chat.js`, `chat/chat.css`, `chat/voice/{speech.mjs,capture.js,worker.js}`, `server/gate.php`→`/opt/jarvis-access/gate.php`. Todos los demás destinos son `/var/www/dashboard/` + ruta repo. El gate sigue siendo privado; no hay nueva URL pública para la voz.
- **GO técnico acotado, experimental con auriculares**, no GO acústico/global. Pendientes: sesión positiva y micro del propietario, altavoces/double-talk/AEC, móviles físicos, aceptación de sílabas/prosodia y branding global/reactor por el parent. No se cambió ni reinició infraestructura para ocultar estas limitaciones.
