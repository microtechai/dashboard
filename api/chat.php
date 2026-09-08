<?php
declare(strict_types=1);
// Overrides are PHP constants defined only by the isolated fixture router.
require defined('JARVIS_CHAT_CONFIG') ? __DIR__ . '/../server/session.php' : '/opt/jarvis-access/session.php';
$action = $_GET['action'] ?? 'session';
if (!is_string($action) || !in_array($action, ['session','login','logout','message','tts','clear','transcribe'], true)) fail(404, 'Acción no disponible.');
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method !== ($action === 'session' ? 'GET' : 'POST')) { header('Allow: ' . ($action === 'session' ? 'GET' : 'POST')); fail(405, 'Método no permitido.'); }
if ($action === 'session') reply(sessionView(authenticated()));
if (($_SERVER['HTTP_ORIGIN'] ?? '') !== $config['origin'] || !hash_equals($_SESSION['csrf'], $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '')) fail(403, 'Solicitud no autorizada.');
if ($action === 'transcribe') {
    if (authenticated() === null) fail(401, 'Inicia sesión para continuar.');
    if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 2097152 + 8192) fail(413, 'Audio demasiado grande.');
    if (strtolower(trim(explode(';', $_SERVER['CONTENT_TYPE'] ?? '')[0])) !== 'multipart/form-data') fail(415, 'Se requiere audio.');
    if ($_POST || array_keys($_FILES) !== ['audio']) fail(400, 'Campos no permitidos.');
    $upload = $_FILES['audio'];
    if (!is_int($upload['error']) || $upload['error'] !== UPLOAD_ERR_OK) fail(in_array($upload['error'], [UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE], true) ? 413 : 400, 'Audio inválido.');
    if ($upload['size'] > 2097152 || $upload['size'] < 1) fail(413, 'Audio demasiado grande o vacío.');
    if (!is_uploaded_file($upload['tmp_name'])) fail(400, 'Audio inválido.');
    $mime = (new finfo(FILEINFO_MIME_TYPE))->file($upload['tmp_name']);
    if (!in_array($mime, ['audio/webm','video/webm','audio/ogg','application/ogg','audio/mp4','video/mp4','audio/x-m4a','audio/wav','audio/x-wav'], true)) fail(415, 'Formato de audio no admitido.');
    rate('transcribe', 6);
    require '/opt/jarvis-stt/transcribe.php';
    exit;
}
if (strtolower(trim(explode(';', $_SERVER['CONTENT_TYPE'] ?? '')[0])) !== 'application/json') fail(415, 'Se requiere JSON.');
if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 24576) fail(413, 'Solicitud demasiado grande.');
$raw = file_get_contents('php://input', false, null, 0, 24577);
if ($raw === false || strlen($raw) > 24576) fail(413, 'Solicitud demasiado grande.');
$object = json_decode($raw);
if (!is_object($object)) fail(400, 'JSON inválido.');
$body = (array)$object;
$allowed = $action === 'login' ? ['username','password'] : (in_array($action, ['message','tts'], true) ? ['text'] : []);
if (array_diff(array_keys($body), $allowed)) fail(400, 'Campos no permitidos.');
if ($action === 'logout') {
    $limits = $_SESSION['rate'] ?? [];
    $_SESSION = ['csrf' => bin2hex(random_bytes(32)), 'history' => [], 'rate' => $limits];
    session_regenerate_id(true); reply(sessionView());
}
if ($action === 'login') {
    foreach (['username','password'] as $field) if (!is_string($body[$field] ?? null) || strlen($body[$field]) < 1 || strlen($body[$field]) > 512) fail(400, 'Credenciales inválidas.');
    rate('login', 6);
    [$status, $data, $token] = authCall('/api/login', $body);
    unset($body, $raw, $object);
    if ($status === 429) fail(429, 'Demasiados intentos.');
    if ($status === 401 || $status === 403) fail(401, 'Credenciales no válidas.');
    if ($status !== 200 || ($data['success'] ?? false) !== true || !$token || !is_string($data['username'] ?? null)) fail(503, 'Autenticación no disponible.');
    session_regenerate_id(true);
    $_SESSION['mc_token'] = $token; $_SESSION['csrf'] = bin2hex(random_bytes(32)); $_SESSION['history'] = [];
    reply(sessionView($data['username']));
}
$username = authenticated();
if ($username === null) fail(401, 'Inicia sesión para continuar.');
if ($action === 'clear') { $_SESSION['history'] = []; $_SESSION['epoch'] = bin2hex(random_bytes(16)); reply(sessionView($username)); }
function textInput(array $body, int $max): string {
    $text = $body['text'] ?? null;
    if (!is_string($text) || !mb_check_encoding($text, 'UTF-8') || mb_strlen($text, 'UTF-8') > $max || trim($text) === '' || preg_match('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/', $text)) fail(400, 'Texto inválido.');
    return $text;
}
function workerLock(string $name) {
    global $config;
    $lock = fopen($config['state_dir'] . '/' . $name . '.lock', 'c');
    if (!$lock) fail(503, 'Servicio no disponible.');
    if (!flock($lock, LOCK_EX | LOCK_NB)) { fclose($lock); header('Retry-After: 2'); fail(429, 'Servicio ocupado.'); }
    return $lock;
}
function sse(string $event, array $data): void {
    echo 'event: ' . $event . "\ndata: " . json_encode($data, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE) . "\n\n";
    flush();
}
function boundHistory(array $history): array {
    $history = array_slice($history, -12);
    while ($history && array_sum(array_map(fn($m) => mb_strlen($m['content'], 'UTF-8'), $history)) > 18000) array_shift($history);
    // Never begin the next prompt with an orphaned assistant turn.
    while ($history && $history[0]['role'] !== 'user') array_shift($history);
    return array_values($history);
}
$text = textInput($body, $action === 'message' ? 4000 : 1000);
if ($action === 'tts') {
    // Last trusted speech boundary: never mutate conversation/history or parse HTML.
    // Keycaps first; ordinary digits, currency and mathematical operators survive.
    $text = preg_replace('/[0-9#*]\x{FE0F}?\x{20E3}/u', ' ', $text);
    $text = preg_replace('/[\p{Extended_Pictographic}\p{Regional_Indicator}\p{Emoji_Modifier}]/u', ' ', $text);
    $text = preg_replace('/[\x{200D}\x{FE0E}\x{FE0F}\x{20E3}\x{E0020}-\x{E007F}]/u', '', $text);
    $text = trim(preg_replace('/\s+/u', ' ', $text));
    if ($text === '') fail(400, 'El texto no contiene palabras para leer.');
}
rate($action, $action === 'message' ? 6 : 20);
$lock = workerLock($action);
$_SESSION['epoch'] ??= bin2hex(random_bytes(16));
$epoch = $_SESSION['epoch']; $authToken = $_SESSION['mc_token']; $history = $_SESSION['history'];
session_write_close();
// Reopening the same session after SSE must not attempt headers or emit cookies.
ini_set('session.use_cookies', '0');
ignore_user_abort(true);
set_time_limit(90);
if ($action === 'message') {
    $ch = null;
    try {
        while (ob_get_level() > 0) ob_end_clean();
        header('Content-Type: text/event-stream; charset=utf-8');
        header('X-Accel-Buffering: no');
        echo ": connected\n\n"; flush();
        $messages = array_merge([['role' => 'system', 'content' => 'Eres MIA, la asistente de MicrotechAI. Responde en español con claridad y honestidad. Tus respuestas de texto pueden reproducirse con voz local. No tienes herramientas, no ejecutas comandos ni acciones, no accedes a sistemas ni afirmas haberlo hecho.']], $history, [['role' => 'user', 'content' => $text]]);
        $buffer = ''; $full = ''; $done = false; $invalid = false; $lastBeat = microtime(true);
        $ch = curl_init($config['model_url']);
        curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Accept: text/event-stream'],
            CURLOPT_POSTFIELDS => json_encode(['model' => 'qwen3-coder-next', 'messages' => $messages, 'max_tokens' => 1024, 'stream' => true], JSON_UNESCAPED_UNICODE),
            CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 60, CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS, CURLOPT_NOPROGRESS => false,
            CURLOPT_XFERINFOFUNCTION => function($ch, ...$unused) use (&$lastBeat) {
                if (microtime(true) - $lastBeat >= 1) { echo ": ping\n\n"; flush(); $lastBeat = microtime(true); }
                return connection_aborted() ? 1 : 0;
            },
            CURLOPT_WRITEFUNCTION => function($ch, $chunk) use (&$buffer, &$full, &$done, &$invalid) {
                if (connection_aborted() || curl_getinfo($ch, CURLINFO_RESPONSE_CODE) !== 200) return 0;
                $buffer .= $chunk;
                if (strlen($buffer) > 131072) { $invalid = true; return 0; }
                while (($pos = strpos($buffer, "\n")) !== false) {
                    $line = rtrim(substr($buffer, 0, $pos), "\r"); $buffer = substr($buffer, $pos + 1);
                    if (!str_starts_with($line, 'data:')) continue;
                    $json = ltrim(substr($line, 5), ' ');
                    if ($json === '[DONE]') { $done = true; continue; }
                    if ($done) { $invalid = true; return 0; }
                    $data = json_decode($json, true);
                    if (!is_array($data) || isset($data['error'])) { $invalid = true; return 0; }
                    $delta = $data['choices'][0]['delta']['content'] ?? '';
                    if (!is_string($delta) || !mb_check_encoding($delta, 'UTF-8') || mb_strlen($full . $delta, 'UTF-8') > 14000) { $invalid = true; return 0; }
                    if ($delta !== '') { $full .= $delta; sse('delta', ['text' => $delta]); }
                    if (connection_aborted()) return 0;
                }
                return strlen($chunk);
            }]);
        $ok = curl_exec($ch); $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        if (!connection_aborted()) {
            if ($ok === false || $status !== 200 || !$done || $invalid || $full === '') {
                sse('error', ['error' => 'No se pudo completar la respuesta.']);
            } else {
                if (!session_start()) throw new RuntimeException('session');
                // Clear/logout/login while streaming must never resurrect discarded state.
                if (($_SESSION['mc_token'] ?? null) === $authToken && ($_SESSION['epoch'] ?? null) === $epoch) {
                    $_SESSION['history'] = boundHistory(array_merge($history, [['role' => 'user', 'content' => $text], ['role' => 'assistant', 'content' => $full]]));
                }
                session_write_close();
                sse('done', ['text' => $full]);
            }
        }
    } catch (Throwable $e) {
        if (!connection_aborted()) sse('error', ['error' => 'No se pudo completar la respuesta.']);
    } finally {
        if ($ch !== null) curl_close($ch);
        if (session_status() === PHP_SESSION_ACTIVE) session_write_close();
        flock($lock, LOCK_UN); fclose($lock);
    }
    exit;
}
$process = null; $pipes = []; $tmp = false; $wav = null;
try {
    $tempDir = $config['tts_temp_dir'] ?? $config['state_dir'];
    if (!is_dir($tempDir) || !is_writable($tempDir)) throw new RuntimeException('temp');
    $tmp = tempnam($tempDir, 'tts-');
    if ($tmp === false || dirname($tmp) !== realpath($tempDir)) throw new RuntimeException('temp');
    $speaker = $config['piper_speaker'] ?? 0;
    if (!is_int($speaker) || $speaker < 0 || $speaker > 255) { unlink($tmp); $tmp = false; fail(503, 'Configuración de voz no válida.'); }
    $process = proc_open(['/usr/bin/taskset', '-c', '0', $config['piper_python'], '-m', 'piper', '--model', $config['piper_model'], '--speaker', (string)$speaker, '--output_file', $tmp],
        [0 => ['pipe', 'r'], 1 => ['file', '/dev/null', 'w'], 2 => ['file', '/dev/null', 'w']], $pipes,
        null, ['OMP_NUM_THREADS' => '1', 'PATH' => '/usr/bin:/bin', 'LANG' => 'C.UTF-8', 'HOME' => $config['state_dir']]);
    if (!is_resource($process)) throw new RuntimeException('process');
    stream_set_blocking($pipes[0], false);
    // Piper's line-oriented CLI can overwrite output_file per input line.
    $input = preg_replace('/\s+/u', ' ', $text) . "\n"; $offset = 0; $deadline = microtime(true) + 20;
    do {
        if (microtime(true) >= $deadline || connection_aborted()) throw new RuntimeException('timeout');
        if (isset($pipes[0])) {
            $written = @fwrite($pipes[0], substr($input, $offset));
            if ($written === false) throw new RuntimeException('stdin');
            $offset += $written;
            if ($offset === strlen($input)) { fclose($pipes[0]); unset($pipes[0]); }
        }
        clearstatcache(true, $tmp);
        if (filesize($tmp) > 20971520) throw new RuntimeException('size');
        $status = proc_get_status($process);
        if (!$status['running']) break;
        usleep(20000);
    } while (true);
    $exit = $status['exitcode'];
    $closed = proc_close($process); $process = null;
    if (($exit === -1 ? $closed : $exit) !== 0 || $offset !== strlen($input)) throw new RuntimeException('exit');
    clearstatcache(true, $tmp);
    $size = filesize($tmp);
    if ($size < 44 || $size > 20971520) throw new RuntimeException('audio');
    $wav = file_get_contents($tmp);
    if ($wav === false || substr($wav, 0, 4) !== 'RIFF' || substr($wav, 8, 4) !== 'WAVE') throw new RuntimeException('audio');
} catch (Throwable $e) {
    $wav = null;
} finally {
    foreach ($pipes as $pipe) if (is_resource($pipe)) fclose($pipe);
    if (is_resource($process)) {
        $status = proc_get_status($process);
        if ($status['running']) {
            proc_terminate($process);
            $until = microtime(true) + 0.25;
            do { usleep(10000); $status = proc_get_status($process); } while ($status['running'] && microtime(true) < $until);
            if ($status['running']) proc_terminate($process, 9);
        }
        proc_close($process);
    }
    if ($tmp !== false && is_file($tmp)) unlink($tmp);
    flock($lock, LOCK_UN); fclose($lock);
}
if ($wav === null) fail(502, 'No se pudo generar el audio.');
header('Content-Type: audio/wav');
header('Content-Length: ' . strlen($wav));
echo $wav;

