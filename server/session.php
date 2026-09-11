<?php
declare(strict_types=1);
// Trusted server-only override permits isolated local HTTP tests; no request/env override.
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
ini_set('display_errors', '0');
function reply(array $data, int $status = 200): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}
function fail(int $status, string $message): never {
    global $action, $toolName, $toolSource;
    if (($action ?? ($_GET['action'] ?? null)) === 'tool') reply(['ok' => false, 'tool' => $toolName ?? null,
        'source' => $toolSource ?? null, 'status' => null, 'data' => null, 'error' => $message], $status);
    reply(['error' => $message], $status);
}
$configFile = defined('JARVIS_CHAT_CONFIG') ? JARVIS_CHAT_CONFIG : '/etc/jarvis-chat/config.php';
if (function_exists('opcache_invalidate')) @opcache_invalidate($configFile, true);
if (!is_readable($configFile)) fail(503, 'Servicio no disponible.');
$config = require $configFile;
if (!is_array($config)) fail(503, 'Servicio no disponible.');
$config += ['state_dir' => '/var/lib/jarvis-chat', 'origin' => 'https://dashboard.microtechai.es',
    'auth_base' => 'http://127.0.0.1:9090', 'model_url' => 'http://127.0.0.1:18010/v1/chat/completions',
    'piper_python' => '/opt/jarvis-tts/venv/bin/python', 'piper_model' => '/opt/jarvis-tts/models/es_ES-davefx-medium.onnx'];
if (!is_dir($config['state_dir']) || !is_writable($config['state_dir'])) fail(503, 'Servicio no disponible.');
umask(0077);
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
ini_set('session.gc_maxlifetime', '86400');
// Debian's default session-clean cron does not cover this private save path.
ini_set('session.gc_probability', '1');
ini_set('session.gc_divisor', '100');
session_cache_limiter('');
session_save_path($config['state_dir']);
session_name('__Host-jarvis-chat');
session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'secure' => true, 'httponly' => true, 'samesite' => 'Strict']);
if (!session_start()) fail(503, 'Servicio no disponible.');
$_SESSION['csrf'] ??= bin2hex(random_bytes(32));
$_SESSION['history'] ??= [];
function sessionView(?string $username = null): array {
    return ['authenticated' => $username !== null, 'username' => $username, 'csrf' => $_SESSION['csrf'], 'history' => $username !== null ? $_SESSION['history'] : []];
}
function rate(string $bucket, int $limit): void {
    $now = time();
    $times = array_values(array_filter($_SESSION['rate'][$bucket] ?? [], fn($t) => $t > $now - 60));
    if (count($times) >= $limit) { header('Retry-After: 60'); fail(429, 'Demasiadas solicitudes.'); }
    $times[] = $now;
    $_SESSION['rate'][$bucket] = $times;
}
function authCall(string $path, ?array $body = null, bool $readTool = false): array {
    global $config;
    if ($readTool && ($body !== null || !in_array($path, ['/api/me', '/api/dashboard', '/api/projects',
        '/api/audits', '/api/dgx/status', '/api/clients'], true))) return [0, null, null, 'tool_not_allowed'];
    $ch = null;
    try {
        $ch = curl_init(rtrim($config['auth_base'], '/') . $path);
        $cookie = null; $response = ''; $oversized = false;
        $headers = ['Accept: application/json'];
        if (isset($_SESSION['mc_token'])) $headers[] = 'Cookie: session=' . $_SESSION['mc_token'];
        if ($body !== null) $headers[] = 'Content-Type: application/json';
        curl_setopt_array($ch, [CURLOPT_CONNECTTIMEOUT => 3, CURLOPT_TIMEOUT => $readTool ? 5 : 8,
            CURLOPT_FOLLOWLOCATION => false, CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_HEADERFUNCTION => function($ch, $line) use (&$cookie) {
                if (preg_match('/^Set-Cookie:\s*session=([a-f0-9]{64})(?:;|\s|$)/i', $line, $m)) $cookie = $m[1];
                return strlen($line);
            },
            CURLOPT_WRITEFUNCTION => function($ch, $chunk) use (&$response, &$oversized, $readTool) {
                if (strlen($response) + strlen($chunk) > ($readTool ? 65536 : 262144)) { $oversized = true; return 0; }
                $response .= $chunk; return strlen($chunk);
            }]);
        if ($readTool) curl_setopt($ch, CURLOPT_HTTPGET, true);
        if ($body !== null) curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($body)]);
        $ok = curl_exec($ch); $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE); $errno = curl_errno($ch);
        if ($readTool) {
            $error = $oversized ? 'output_limit' : ($errno === CURLE_OPERATION_TIMEDOUT ? 'timeout' :
                ($ok === false ? 'transport_error' : ($status >= 300 && $status < 400 ? 'redirect_not_allowed' :
                ($status < 200 || $status >= 300 ? 'http_error' : null))));
            $data = null;
            if ($error === null) {
                $data = json_decode($response);
                if (json_last_error() !== JSON_ERROR_NONE) $error = 'invalid_response';
                // Also block a credential reflected in JSON (including escaped strings/keys).
                elseif (isset($_SESSION['mc_token']) && str_contains(json_encode($data, JSON_UNESCAPED_UNICODE), $_SESSION['mc_token'])) $error = 'invalid_response';
            }
            return [$status, $error === null ? $data : null, null, $error];
        }
        if ($ok === false || $status >= 500 || $status === 0) fail(503, 'Autenticación no disponible.');
        return [$status, json_decode($response, true), $cookie];
    } catch (Throwable $e) {
        if ($readTool) return [0, null, null, 'transport_error'];
        throw $e;
    } finally {
        if ($ch !== null && $ch !== false) curl_close($ch);
    }
}
function authenticated(): ?string {
    if (!isset($_SESSION['mc_token'])) return null;
    [$status, $data] = authCall('/api/me');
    if (in_array($status, [401, 403, 302, 303], true)) {
        unset($_SESSION['mc_token'], $_SESSION['private_idea_drafts']); $_SESSION['history'] = []; return null;
    }
    if ($status !== 200 || !is_string($data['user']['username'] ?? null)) fail(503, 'Autenticación no disponible.');
    return $data['user']['username'];
}
