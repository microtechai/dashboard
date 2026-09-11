# Fase 5 — acceso único server-side (2026-09-08)

> **Actualización posterior verificada:** el parent resolvió Cloudflare con bypass/purge del hostname; Fase6 repitió las cuatro URLs antiguas y obtuvo401 DYNAMIC, HTML303. También se contuvo la exposición del executor a127.0.0.1:5000, debug/reloaderFalse, health local200 y conexión externa rechazada, según `/home/ddr/jarvis-port5000-containment/REPORT.md`. No certifica executor UI operativo. Login/logout positivo del propietario sigue pendiente. Fase6 tiene candidato WebGL real pero **NO-GO de rendimiento y no se desplegó**; ver [informe Fase6](phase6-fire-report.md). Las secciones siguientes son el registro histórico de Fase5 y sus bloqueos originales, no el estado actual de Cloudflare/puerto.

## Resultado: origen protegido; **NO-GO global / aceptación pendiente**

Se desplegó directamente en producción, sin staging ni backup completo. No se implementaron fases 6/7. Se mantuvo la estética del núcleo, voz y Task Executor. El único escritor de esta fase trabajó sobre `feat/jarvis-single-login`, apilada sobre `feat/jarvis-chat-tts` (PR3 abierta verificada antes de publicar).

### Bloqueos que impiden declarar seguro el sistema completo
1. **Cloudflare todavía entrega cuatro recursos previos anónimamente (`HIT 200`)**:
   - `https://dashboard.microtechai.es/chat/chat.js?v=20260908-chat4`
   - `https://dashboard.microtechai.es/chat/chat.css?v=20260908-chat4`
   - `https://dashboard.microtechai.es/chat/core-state.js?v=20260908-chat4`
   - `https://dashboard.microtechai.es/voice/speech.js`
   El origen devuelve 401 a todos. El token local comprobado está activo, pero la consulta autorizada de zonas para `microtechai.es` devuelve una lista vacía: **no hay permiso utilizable para purgar/configurar esa zona**. No se modificaron DNS ni reglas de otros sitios. Hace falta acceso Cloudflare a esta zona y una regla de bypass de caché limitada a `dashboard.microtechai.es`, además de purgar los objetos anteriores (preferentemente todas las claves de ese hostname si el plan lo permite). No basta con cambiar `?v=`: las URLs antiguas siguen siendo accesibles.
2. **Executor independiente expuesto en `178.104.253.211:5000`**. GET `/api/health` devuelve 200 desde Internet; el archivo real `/var/www/dashboard/api/exec_handler.py` no tiene guardia de autenticación y publica `/api/exec`, `/api/commands`, `/api/history`, `/api/validate` con Flask debug activado. No se hicieron POST ni se ejecutaron comandos. Es una superficie previa, independiente del vhost; no se cambió su servicio/firewall de forma silenciosa. Requiere contención/auditoría separada antes de GO global. MC `:9090/api/me` devuelve 302 anónimo y valida sesiones; también está ligado a todas las interfaces, no se modificó.
3. **Login/logout positivo del propietario pendiente** en https://dashboard.microtechai.es/login.html. No se introdujeron cuentas/contraseñas reales ni se inyectó estado de autenticación para QA. La prueba positiva automatizada usa exclusivamente MC FIXTURE y PHP real. No implica aceptación productiva del propietario.

**El origen queda cerrado**, no se revirtió a la configuración pública anterior. No declarar GO ni avanzar automáticamente a fase 6 con estas limitaciones.

## Arquitectura y archivos exactos

- `/opt/jarvis-access/session.php` (nuevo, privado root:www-data, 0640; directorio 0750): módulo extraído del chat sin cambiar el contrato. Cookie `__Host-jarvis-chat`, Secure, HttpOnly, SameSite=Strict, Path=/; almacenamiento privado `/var/lib/jarvis-chat`; validación MC `/api/me` en cada petición privada. MC conserva su expiración de 86400 s; caídas/JSON inesperado fallan cerrados. Configuración existente `/etc/jarvis-chat/config.php` sin modificaciones.
- `/opt/jarvis-access/gate.php` (nuevo privado): entrada PHP para **todas** las rutas salvo excepciones públicas exactas. Allowlist de archivos, nunca concatena el URI a una ruta de disco. `/` y `/index.html` anónimos → 303 a `/login.html`; otros privados → 401. Tras autenticación, copias/aliases desconocidos → 404, no fallback HTML. Estadísticas solo se ejecutan tras validar MC.
- `/var/www/dashboard/login.html` (nuevo): una página pública autocontenida, sin librerías ni datos del dashboard; usa el endpoint MC existente del chat con Origin/CSRF. Un formulario, sin pistas de credenciales.
- `/var/www/dashboard/api/chat.php`: importa el módulo privado; mantiene guards, workers privados, streaming, TTS y STT. Las constantes de configuración de fixtures solo pueden definirse desde un router PHP de prueba, no desde parámetros/headers del cliente.
- `/var/www/dashboard/index.html`: elimina overlay, `mc_authed`, login local y pistas; arranca únicamente después de entrega autenticada. Conserva núcleo/RAF/estilos/executor. Referencia `chat/chat.js?v=20260908-access5`.
- `/var/www/dashboard/chat/chat.js`: elimina segundo formulario; reutiliza sesión de acceso; cierre de sesión común desde chat/sidebar, limpieza de audio y redirección al login. Revalidación de página restaurada por bfcache.
- `/etc/nginx/sites-enabled/microtechai` resuelve a `/etc/nginx/sites-available/microtechai`. Solo se sustituye el bloque TLS de dashboard. El resto del mismo archivo (WordPress y redirecciones HTTP) y las demás secciones de `nginx -T` resultaron idénticos. No se cambió ningún otro vhost.

La plantilla versionada `server/nginx-dashboard.conf` fuerza gate para cualquier ruta no pública, desactiva FastCGI cache/ETag/condicionales y fija `private, no-store` más cabeceras CDN no-store, incluso cuando stats intenta sobrescribir Cache-Control. Se oculta CORS `*` heredado de stats. Solo `/login.html` y `/api/chat.php` son excepciones exactas; las acciones privadas del segundo siguen requiriendo MC/CSRF/Origin. Host incoherente en el vhost devuelve 421. No hay regex PHP ni `try_files ... /index.html` que eludan el gate.

## Evidencia ejecutada

`docs/evidence/phase5/`:
- `tests.json`, `test-0.txt`…`test-5.txt`: comandos y resultados reales PASS.
- `http-anonymous.json`: 23 rutas × origen/edge, con códigos, tamaños, SHA256 y estado CF; sin cuerpos ni cookies.
- `direct-host.json`: IP HTTPS `/index.html` 404 (otro vhost, no JARVIS), IP HTTP `/dashboard/index.html` 404, Host IP con SNI dashboard 421; MC 302; executor health 200.
- `public-browser.json` y `anonymous-login.png`: Chromium real navegó `/` → 303 → login 200; bootstrap sesión 200, exactamente un formulario, cero canvas/dashboard y cero errores JS. No intentó login real.
- `production-checks.txt`: PHP lint productivo y `nginx -t` PASS; vhosts ajenos byte-identical.
- `deployment-manifest.json`: rutas, SHA256 antes/después y metadatos originales; verificable por SSH sin login de aplicación.

RED observado: el test anónimo recibió 200 sin gate (nueve aserciones fallidas); después PASS. Siguiente RED: login público inexistente; después PASS. Siguiente RED: routing Nginx inexistente; después PASS. Los tests de contrato de sesión reutilizada validan el comportamiento ya existente además de la nueva integración.

GREEN ejecutado:
- `python3 tests/access_gate_test.py Access`: 4 tests (anonimato, sesión compartida/revocada/MC caído/logout/cookie inválida, contrato Nginx, un solo login).
- `python3 tests/access_browser_test.py BrowserAccess`: 1 test Chromium + PHP real + MC FIXTURE: acceso inicial, login mediante formulario, chat sin otro login, sidebar logout y sesión revocada. Documento protegido mínimo **fixture**, no prueba visual del dashboard.
- `python3 tests/chat_backend_test.py`: 11 tests de sesión, CSRF/Origin, límites, SSE/history, TTS, locks, limpieza/timeout y carreras.
- `node --test tests/fire.test.cjs`: 5 tests; `node tests/core_activity.cjs`: 1; `node tests/stt_core.cjs`: PASS.
- PHP CLI local 8.3 y producción 8.4 lint; sintaxis de scripts inline de index/login y chat `node --check`; `git diff --check`.

No se afirma que toda la suite legacy siga pasando: ver revisión obligatoria abajo. Tampoco se afirma CI de GitHub, rendimiento WebGL, audio físico ni login productivo positivo.

## Revisión independiente corta

Qwen real `qwen3-coder-next` en DGX devolvió la revisión guardada en `qwen-review.txt`. Sus acusaciones de traversal/race por `session_write_close()` **no se aceptaron**: la allowlist mapea únicamente claves exactas a rutas constantes; cerrar el lock no modifica esa allowlist. No hay variable de entorno/request que defina constantes PHP. `fail()` termina (`never` → `reply()` → exit). Se mantuvo el cierre temprano para no serializar todos los assets. Los riesgos hipotéticos por futuras ampliaciones no se presentan como vulnerabilidades actuales. No se reiniciaron modelos, MC, TTS, STT ni executor.

## Despliegue y reversión selectiva

Script reproducible con guards: `server/deploy_access5.py`. Verifica hashes de los cuatro archivos previos y ausencia de rutas nuevas antes de escribir. Conserva únicamente afectados fuera del webroot; valida candidato Nginx con configuración real antes de modificar archivos activos; PHP lint previo al rename; reemplazo atómico por archivo y `nginx -t` final; **solo `systemctl reload nginx`**, nunca restart. El primer intento falló por límite argv antes de SSH; el segundo candidato falló por includes relativos antes de tocar live. Corregido enviando script por stdin y resolviendo includes para el test; despliegue final correcto.

Preservación válida utilizada: `/root/jarvis-access5-rollback-20260908T134249Z/manifest.json`, con originales en ese directorio conservando la ruta absoluta relativa. La carpeta de ensayo fallido `...T134224Z` no es el manifiesto de la publicación.

Para reversión selectiva: comparar primero cada hash vivo con `after`; verificar copia original con `before`; restaurar por rename con uid/gid/modo originales solo archivos listados. Los tres archivos nuevos tienen `before=null`. **Restaurar Nginx antiguo vuelve a abrir el dashboard anónimamente y no está recomendado/autorizado como solución de seguridad.** Ante regresión de login, mantener el gate o servir 503, no quitarlo. Una reversión completa exige restaurar chat+Nginx de forma coherente, `nginx -t` y reload graceful; requiere una decisión explícita que acepte la reapertura. No eliminar módulos privados mientras el chat/gate vivo los referencia.

## Antes de fase 6: tests legacy que deben revisarse

- `tests/chat_frontend_test.py`: helper `login()` y aserciones dependen del eliminado `#jarvis-chat-login`, usuario/password y segundo formulario. Migrar al formulario público real y al gate PHP fixture, no simular `mc_authed` ni inyectar una sesión autenticada en producción. Expiración/401/logout ahora redirigen; fallos 503 de sesión se muestran en la página pública o bloquean la API.
- `tests/stt_frontend_test.py` hereda ese helper: actualizar arranque antes de interpretar fallos como regresión de voz. Conservar casos de permisos denegados/tardíos, stop/logout y tracks.
- `tests/fire_webgl.py` y `tests/executor_minimize.py`: siguen siendo pruebas aisladas de componentes, no evidencia de acceso productivo. Para aceptación visual productiva debe iniciar sesión el propietario; no ocultar overlay ni inyectar auth. SwiftShader no demuestra FPS de dispositivo físico.
- Mantener y ampliar `access_browser_test.py` como contrato de login único; añadir prueba de caducidad temporal MC y logout en varias pestañas si se amplían políticas de sesión. La revocación/outage ya están cubiertas con fixtures.

## Checklist del propietario / operación

1. Resolver Cloudflare hostname bypass + purge y repetir **las URLs antiguas**, no solo un cache-buster; esperar 401 en todos los assets privados en edge. HTML `/` y `/index.html` ya son DYNAMIC 303, no se vio HTML previo después del despliegue.
2. Contener/auditar executor separado y acceso externo MC sin alterar cuentas.
3. Iniciar sesión personalmente en `/login.html`; comprobar dashboard+chat sin segundo formulario; salir desde sidebar/chat; recargar `/index.html` y stats sin sesión; no entregar la contraseña al agente.
4. Solo entonces resolver GO/NO-GO para fase 6.
