# Microtech AI / MIA — Handoff 2026-09-09

## LEER PRIMERO EN LA PRÓXIMA SESIÓN
Última petición: guardar contexto, cambios, plan y worklog. El nuevo plan de prosodia/herramientas es SOLO PLAN; no ejecutar nuevas fases sin GO. Prioridad del propietario: la voz no respeta pausas/puntos/comas y parece comerse letras; la transcripción humana y naturalidad siguen sin aceptar.

## Estado verificado al cierre
- Producción https://dashboard.microtechai.es en OPERATOR PREVIEW autorizado por el propietario; no GO global de hardware/acústica.
- Repo /home/ddr/jarvis-phase2-20260908, rama feat/mia-reactor-integration. Último commit de código al redactar: 8d4d6b0ff7f052e8ac46968b4bc420183de5c481. PR8 draft https://github.com/microtechai/dashboard/pull/8; apilada sobre PR7, PR2–PR8 siguen abiertas. No merge autorizado; checks CI no publicados no equivalen a PASS.
- Microtech AI marca, MIA asistente. Reactor oscuro, electricidad y conversación central. 24 entradas y 17 nodos conservados.
- Voz femenina Piper es_ES-sharvard-medium speaker1/F; Whisper base int8 CPU. Llamada continua opt-in, auto-TTS, cancelación por voz, ruido reforzado, mute/colgar cierran captura. Máximo 3 peticiones TTS/respuesta, 1000 caracteres/bloque, avisos de exceso.
- Login MC server-side, recursos privados; Cloudflare bypass de hostname aplicado. Executor separado solo 127.0.0.1:5000, sin debug. No habilitar ejecución libre desde el chat.
- MC tiene módulos reales de proyectos/subvenciones/auditoría/PDF, separados de pantallas 3D previamente estáticas. No afirmar integración de herramientas que no existe. No perder módulos al rediseñar.

## Último arreglo de audio publicado
Fusión por eliminar emojis sin separador: Buenos👩🏽‍💻días → Buenosdías; corregida frontend/PHP. Frase larga antes descartada ahora segmentada por palabras conservando remanente dentro del presupuesto. Dos bugs reproducidos; NO solución certificada de prosodia/acento/STT humana.
Hashes comprobados padre remoto/local:
- api/chat.php 759dd6a527f3ae83e61ee637f8f40e714f9c56ba598810a8fe9034a1b3615cb3
- chat/voice/speech.mjs a0008bd89cdd2c76ce4b60044df9b866044756ba64d099ba475cf947ebfc3506
Qwen DGX real revisó: chatcmpl-a9992b29b2514b8f; propuestas erróneas rechazadas. 98 PASS/1 SKIP/0 FAIL reportados para este parche, síntesis real probada. No equiparar round-trip sintético con audición humana.

## Próximo paso, después de GO
Leer docs/plans/mia-voz-herramientas-autonomia.md. Fase1: auditar puntuación, finales y reproducción; comparar párrafo completo vs chunking y muestras femeninas con audición. Fase2: STT con muestra humana voluntaria. Luego herramientas tipadas (web/análisis), reutilización MC, Calendar read-first OAuth individual y escrituras confirmadas. Nada de esto está implementado por redactar el plan.
Revisión Qwen del plan: chatcmpl-959697039b291bc6, finish stop. No aceptar SSML Piper no demostrado, regex como defensa prompt injection ni supuestas métricas de naturalidad.

## Entorno y rutas
- SSH autorizado root@178.104.253.211, clave /home/ddr/.ssh/hetzner-admin (solo ruta, nunca contenido).
- /var/www/dashboard; gate /opt/jarvis-access/gate.php; sesión /opt/jarvis-access/session.php; configuración privada /etc/jarvis-chat/config.php. No imprimir credenciales.
- /opt/jarvis-tts y /opt/jarvis-stt. No reiniciar para cambios estáticos.
- MC /opt/microtech/dashboard/mc-dashboard.py sirve /home/ddr/mc-dashboard-dev.html en el servidor. No es el mismo documento que index del 3D.
- Qwen existente DGX 192.168.1.137:8010, qwen3-coder-next; comprobar modelos y métricas exactas antes de inferir. No cargar nuevos modelos, reiniciar ni aumentar memoria sin inspección y GO.
- voice/speech.js y api/stats.php existen solo en producción en algunas bases: jamás sincronizar carpeta con borrado.
- Máquina de QA QEMU/QXL sin GPU3D; SwiftShader no hardware. /home/ddr/mia-hardware-qa/README.md.

## Evidencias y reversión
- docs/call-report.md, docs/mia-integration-report.md, docs/mia-redesign-report.md y documentos de audio identificados en el índice Git.
- /home/ddr/mia-audio-dgx-diagnosis/: trazas y WAV antes/después, revisión DGX y despliegue del arreglo de integridad.
- /home/ddr/mia-integration-audit/: inventario y matriz de regresiones.
- /home/ddr/mia-female-voice-evaluation/: muestras, licencia y atribución Sharvard.
- /home/ddr/mia-redesign-release/deployment-manifest.json.
- Rollbacks remotos selectivos: /root/mia-audio-integrity-20260908T234827Z (más reciente audio), /root/mia-redesign-rollback-20260908T232629Z, /root/mia-integration-rollback-20260908T223615Z. Leer manifiesto vivo antes de usar; no revertir indiscriminadamente ni reabrir login.
- Evidencia no versionada preservada localmente; índice SHA256 en /home/ddr/mia-session-close-20260909/local-evidence-index.json. No git add .

## Criterios y cuidados de la siguiente sesión
Conservar módulos, diseño aprobado y funcionalidades. TDD dirigido por fallo, una regresión final; no repetir pruebas pesadas sin cambios. Preservar fallos históricos y diferenciar revalidación dirigida de suite completa. No aceptar guard de rendimiento inflado por baseline lento. No declarar solución vocal hasta audición del propietario.
No grabar micrófono real ni eludir autenticación. Secretos compartidos anteriormente NO incluidos en estos documentos; rotación coordinada pendiente si no consta evidencia posterior. No recuperar/publicar valores de conversaciones previas.
Cada despliegue: GO/NO-GO o excepción OPERATOR PREVIEW explícita, backup selectivo fuera del webroot, hash contra deriva, pruebas, lectura remota y GitHub/Obsidian.
