# MIA: voz natural y herramientas — Implementation Plan

> **For Hermes:** Implementar por tareas con revisión de especificación, código y pruebas. Este documento es SOLO PLAN: requiere GO antes de ejecutar cada fase productiva.

**Goal:** MIA conversacional en español, con pausas naturales, transcripción verificable y herramientas útiles con autonomía acotada.

**Architecture:** Mantener la autenticación MC y el dashboard existente. Separar captura/STT, generación de texto, preparación de habla y reproducción; añadir un ejecutor de herramientas tipadas privado, autorizado por el servidor, no por texto del modelo. Usar Qwen existente en DGX para planificación/selección de herramientas y Hermes para orquestación y verificación.

**Tech Stack:** Frontend JS/WebAudio/Silero; gateway PHP; backend MC Python existente; Whisper/Piper actuales como baseline; Qwen DGX existente. Proveedores nuevos y modelos grandes son decisiones pendientes, no instalaciones autorizadas.

## Estado y alcance
- El propietario reporta falta de pausas en espacios, puntos y comas, omisión de letras y mala transcripción. No está resuelto por haber generado WAV válidos.
- Se corrigieron previamente fusión de palabras al eliminar emojis y descarte de frases largas. No prueban naturalidad, prosodia ni precisión con voz humana.
- Voz actual: Piper es_ES-sharvard-medium speaker 1/F. STT: Whisper base int8 CPU. Captura con confirmación VAD 128 ms, pre-roll 512 ms y fin por silencio 704 ms; revalidar configuración viva antes de cambiarla.
- El chat no dispone automáticamente de las herramientas de Hermes. MC tiene funcionalidades reales de proyectos/subvenciones/auditorías separadas de algunas pantallas estáticas del 3D.
- Conservar diseño, módulos, roles, login, controles de llamada, voz femenina y privacidad. No habilitar shell/SSH arbitrarios ni reabrir el executor público.
- Planificación únicamente: no OAuth, búsqueda de datos personales, escaneo de sitios ni cambios de producción en esta fase.

## Revisión DGX realizada para este plan
Qwen real en 192.168.1.137:8010, qwen3-coder-next, petición chatcmpl-959697039b291bc6; 1365 tokens de entrada, 2319 de salida, finish_reason stop. Cola running/waiting cero antes de consultar. Recibió código actual speech.mjs y contexto acotado sin credenciales.

Se conservan sus ideas de separar prosodia, STT, permisos y Calendar. Se RECHAZAN como no verificadas o incorrectas: insertar etiquetas SSML en Piper sin demostrar soporte; usar round-trip TTS→Whisper como aceptación de voz humana; considerar una regex defensa contra prompt injection; asumir cookie PHPSESSID/tabla de roles; inferir que todo funciona en DGX sin instalaciones; asumir zona Europe/Madrid; métricas de latencia/precisión inventadas. No se usará la afirmación no comprobada de soporte SSML desde determinada versión. No basta con cambiar el prompt.

## Fase 0 — Baseline reproducible y decisiones
**Archivos a leer:** `/home/ddr/jarvis-phase2-20260908/chat/voice/speech.mjs`, `chat/chat.js`, `chat/voice/capture.js`, `chat/voice/worker.js`, `api/chat.php`, `server/stt_worker.py`, `docs/call-report.md`, `docs/mia-redesign-report.md`; `/home/ddr/mia-integration-audit/README.md` y `regression-matrix.json`.
1. Capturar hashes y parámetros no secretos de idioma, locutora, velocidades, silencios y presupuesto TTS desde servidor.
2. Pedir una grabación humana breve voluntaria y una frase donde MIA pronuncie mal. No activar/grabar micrófono sin acción consciente ni guardar conversaciones por defecto.
3. Preparar corpus corto de puntuación, interrogaciones, abreviaturas, números, nombres propios y finales de palabra. Mismas frases en todas las comparaciones.
4. Medir por separado fin de voz, respuesta STT, primer texto, primera unidad hablable, primer audio y fin; registrar distribución y condiciones, no sumas inferidas de pruebas independientes.
**GO:** problemas y baseline documentados. La falta de muestra humana limita conclusiones, no bloquea pruebas de integridad del texto.

## Fase 1 — Hablar con pausas y sin perder letras (prioridad)
**Modificar si procede:** `chat/voice/speech.mjs`, `chat/chat.js`, `api/chat.php`. **Crear pruebas:** `tests/speech_prosody.test.mjs`, `tests/speech_playback_test.py`.
1. RED: demostrar conservación del texto y puntuación a través de normalización y chunking incremental; probar fragmentos SSE partidos dentro de una palabra, abreviaturas, 3.14, URLs, guiones y espacios Unicode.
2. Comparar síntesis de párrafo completo frente a bloques con las mismas palabras para distinguir prosodia del modelo de pérdida al reproducir.
3. Agrupar unidades hablables completas: no convertir cada trozo SSE en audio, no quitar puntuación ni cortar sílabas. Preservar remanentes y los avisos del límite de voz.
4. Verificar que el siguiente bloque no cancela/solapa el anterior, que termina de reproducirse y que barge-in solo cancela por voz válida. No recortar colas del WAV ni duplicar silencios.
5. Si falta pausa, estudiar primero parámetros soportados del motor; después silencios PCM o pausas entre unidades con cancelación inmediata. Rangos iniciales orientativos para audición: comas 100–200 ms, puntos 250–450 ms; no insertar en decimales/abreviaturas y no tratarlos como resultados garantizados.
6. Comparar voz femenina actual y como máximo dos alternativas españolas con las mismas frases. Mantener selección actual hasta audición/decisión del usuario si se cambia el motor o timbre. No acelerar artificialmente antes de resolver inteligibilidad.
7. GREEN: pruebas unitarias y de reproducción; evaluación auditiva del propietario de pausas y finales de palabras. Round-trip sintético solo diagnóstico auxiliar.
**Validar:** `node --test tests/speech_prosody.test.mjs`; `python3 tests/speech_playback_test.py`; regresión final `python3 tests/run_call.py`. Comandos nuevos son objetivos a implementar, no pruebas ya ejecutadas.
**GO:** ninguna palabra desaparece en transformaciones; secuencia de audio completa; el propietario acepta pronunciación y pausas. No declarar naturalidad con hashes o HTTP200.

## Fase 2 — Transcripción fiable
**Archivos:** `chat/voice/capture.js`, `chat/voice/worker.js`, `server/stt_worker.py`; crear `tests/stt_quality_eval.py` y corpus con consentimiento/licencia.
1. RED: frases con inicio suave, pausas interiores y última sílaba; comparar audio capturado con referencia antes de culpar Whisper.
2. Verificar resampling 16k, número de muestras, clipping, idioma español, pre-roll, silencio final y doble filtrado VAD.
3. Si captura está íntegra pero STT falla, comparar opciones de decodificación y un modelo español/multilingüe más preciso en entorno aislado.
4. Si requiere GPU: inspeccionar DGX real, MemAvailable y procesos; no detener Qwen ni cargar un modelo adicional sin presupuesto/GO. Comparar alternativa CPU con latencia real.
5. Medir WER/CER por frase humana y nombres/números críticos; reportar errores concretos. No prometer WER universal ni usar solo audio Piper como benchmark.
**GO:** mejora repetible sobre baseline sin empeorar cortes, privacidad o latencia más allá de lo aceptado. Prueba de auriculares/altavoces real separada.

## Fase 3 — Herramientas con autonomía controlada
**Archivos propuestos:** `server/mia-tools/registry.json`, `server/mia-tools/runner.py`, `server/mia-tools/policy.py`, `server/mia-tools/web.py`; integración en `api/chat.php`; pruebas `tests/mia_tools_test.py`.
Las rutas son propuestas: confirmar layout backend y modelo de servicio antes de crearlas. Publicar workers fuera del webroot; gateway autenticado como entrada única.
1. RED: herramientas inexistentes, argumentos inválidos, sesión vencida, usuario ajeno y confirmaciones caducadas deben rechazarse.
2. Registro con JSON Schema, política read/write, timeout, límite de salida y permisos. Identidad/rol vienen de sesión validada, nunca del modelo.
3. Probar tool calling real del modelo vivo; el soporte del proveedor no garantiza integración. Bucle inicial acotado (p. ej. 4 pasos/60 s como propuesta ajustable), cancelación y presupuesto por usuario.
4. Web: búsqueda + extracción + enlaces y fecha de consulta. Elegir proveedor y coste antes de contratar; no asumir que herramientas Hermes están instaladas en el dashboard.
5. Fetch seguro: validar DNS/IP inicial y tras redirecciones, bloquear loopback/redes privadas/link-local/metadatos y esquemas no HTTP(S), limitar tamaño/tiempo/MIME. Auditorías internas solo mediante conectores explícitos para activos autorizados.
6. Tratar páginas/PDF/resultados como datos no confiables: instrucciones externas no pueden elevar permisos ni autorizar escrituras. No enviar secretos al modelo o a buscadores.
7. Progreso visible con eventos reales de herramienta, fuente y resultado; respuesta hablada breve y detalles/citas en pantalla.
**GO:** consultas reales citadas y pruebas negativas de autorización, SSRF y prompt injection. No asegurar protección perfecta por pasar un corpus de pruebas.

## Fase 4 — Conectar proyectos, subvenciones y auditorías existentes
**Leer antes:** `/opt/microtech/dashboard/mc-dashboard.py` y su frontend servido; no sustituir MC ni copiar placeholders como datos reales.
**Proponer:** adaptador `server/mia-tools/mc.py`, pruebas `tests/mia_mc_tools_test.py`.
1. Mapear endpoints y permisos reales; permitir lectura de proyectos/subvenciones/resultados existentes de la cuenta autorizada.
2. Análisis y comparación con fuentes: distinguir datos vacíos de servicio desconectado y capacidades aún no conectadas.
3. Auditorías públicas no invasivas con objetivo validado, límites y control de coste; para activos propios, reutilizar flujo MC existente y autorización correspondiente.
4. Trabajos largos con ID y estado persistente, cancelación, resultados y PDF reales; no simular porcentajes.
5. Crear/editar proyectos o ejecutar auditorías costosas requiere resumen y confirmación vinculada a parámetros exactos.
**GO:** resultado consultable con ID/URL, aislamiento entre usuarios, módulo original intacto y navegación regresada.

## Fase 5 — Google Calendar y conectores posteriores
**Propuesto:** `server/mia-tools/google_calendar.py`, OAuth web backend privado y `tests/mia_calendar_test.py`. No reutilizar ciegamente OAuth Desktop de Hermes como arquitectura del dashboard multiusuario.
1. Elegir cuenta/calendario y comprobar si existe autorización adecuada sin imprimir tokens. Definir servicio OAuth con redirect seguro, state/PKCE según flujo, tokens cifrados fuera del webroot, separación por usuario y revocación.
2. Primero permisos mínimos de lectura: agenda y huecos. No pedir Gmail/Drive por anticipado.
3. Zona IANA confirmada por el usuario/calendario, sin asumir Madrid; probar Canarias si corresponde, horario de verano, días completos y horas ambiguas.
4. Luego crear/mover/cancelar: mostrar calendario, fecha, zona, duración e invitados; confirmar antes de la escritura. Invitaciones son mensajes externos.
5. Idempotencia persistente con identificador único de operación confirmado; gestionar respuesta incierta/reintentos sin duplicar eventos. No basarla solo en resumen+hora.
6. Leer de vuelta ID/URL del evento antes de anunciar éxito.
7. Posteriores: Drive solo carpetas seleccionadas, Docs/Sheets para informes, correo primero borradores; cada conector requiere scopes y autorización propios.
**GO:** lectura real de calendario autorizado; escritura solo tras consentimiento, ID comprobado, pruebas DST/duplicados/revocación. Este plan no inicia OAuth.

## Niveles de libertad propuestos
- Autónomo dentro de la solicitud: buscar web pública, leer fuentes autorizadas, comparar, resumir y preparar borradores; límites de recursos y trazabilidad.
- Confirmación contextual: escribir/borrar datos, crear/modificar eventos, enviar invitaciones/correos, compartir documentos y ejecutar trabajos costosos. Vincular aprobación a acción, parámetros y usuario, con caducidad.
- GO operativo separado: cambios de servidores, instalaciones/modelos, pagos, escaneos intrusivos y operaciones destructivas. No habilitar intérprete de comandos general desde el chat.
- Las instrucciones contenidas en una página, email o documento nunca equivalen a consentimiento del propietario.

## Entrega y ritmo
Cada fase: baseline selectivo → pruebas RED → cambio mínimo → pruebas dirigidas GREEN → revisión Qwen/Hermes → una regresión completa al estabilizar → GO → publicación selectiva → verificar hashes y comportamiento → GitHub/Obsidian. No repetir suites gráficas pesadas por cada cambio de audio. No modificar diseño en estas fases.
Mantener módulos y rollback selectivo fuera del webroot. Preservar historiales; logs de herramientas redactados, sin grabaciones ni tokens por defecto. Las métricas de calidad humana y GPU quedan separadas de fixtures.

## Decisiones pendientes antes de implementación
1. GO Fase 1 (voz); frase/grabación voluntaria para identificar el fallo exacto y valorar muestras femeninas.
2. Aceptación de coste/latencia para motor alternativo si Piper no cumple.
3. Proveedor de búsqueda y activos autorizados para auditoría.
4. Cuenta/calendario, zona horaria y alcance OAuth cuando llegue Fase 5.
5. Confirmar niveles de autonomía; no interpretar «más libertad» como permiso indefinido para publicar, gastar o modificar sistemas.

No se implementó código ni se modificó producción al redactar este plan.
