<?php
declare(strict_types=1);
// Nginx sends EVERY non-public route here. Never serve a request-derived path.
require __DIR__ . '/session.php';
$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
$username = authenticated();
if ($username === null) {
    if (in_array($path, ['/', '/index.html'], true)) {
        header('Location: /login.html', true, 303); exit;
    }
    fail(401, 'Inicia sesión para continuar.');
}
session_write_close();
if (!in_array($_SERVER['REQUEST_METHOD'] ?? 'GET', ['GET', 'HEAD'], true)) {
    header('Allow: GET, HEAD'); fail(405, 'Método no permitido.');
}
$root = defined('JARVIS_DOCUMENT_ROOT') ? JARVIS_DOCUMENT_ROOT : '/var/www/dashboard';
$files = [
    '/reactor/reactor.js' => ['reactor/reactor.js', 'application/javascript'],
    '/' => ['index.html', 'text/html; charset=utf-8'],
    '/index.html' => ['index.html', 'text/html; charset=utf-8'],
    '/integration.js' => ['integration.js', 'application/javascript; charset=utf-8'],
    '/fire/shaders.js' => ['fire/shaders.js', 'application/javascript; charset=utf-8'],
    '/fire/integration.js' => ['fire/integration.js', 'application/javascript; charset=utf-8'],
    '/chat/chat.js' => ['chat/chat.js', 'application/javascript; charset=utf-8'],
    '/chat/core-state.js' => ['chat/core-state.js', 'application/javascript; charset=utf-8'],
    '/chat/chat.css' => ['chat/chat.css', 'text/css; charset=utf-8'],
    '/chat/voice/assets-manifest.json' => ['chat/voice/assets-manifest.json', 'application/json'],
    '/chat/voice/onnxruntime-license.txt' => ['chat/voice/onnxruntime-license.txt', 'text/plain'],
    '/chat/voice/onnxruntime-ThirdPartyNotices.txt' => ['chat/voice/onnxruntime-ThirdPartyNotices.txt', 'text/plain'],
    '/chat/voice/silero-license.txt' => ['chat/voice/silero-license.txt', 'text/plain'],
    '/chat/voice/vad-license.txt' => ['chat/voice/vad-license.txt', 'text/plain'],
    '/chat/voice/speech.mjs' => ['chat/voice/speech.mjs', 'application/javascript'],
    '/chat/voice/session.mjs' => ['chat/voice/session.mjs', 'application/javascript'],
    '/chat/voice/core.mjs' => ['chat/voice/core.mjs', 'application/javascript'],
    '/chat/voice/capture.js' => ['chat/voice/capture.js', 'application/javascript'],
    '/chat/voice/worker.js' => ['chat/voice/worker.js', 'application/javascript'],
    '/chat/voice/assets/ort.wasm.min.js' => ['chat/voice/assets/ort.wasm.min.js', 'application/javascript'],
    '/chat/voice/assets/ort-wasm-simd-threaded.mjs' => ['chat/voice/assets/ort-wasm-simd-threaded.mjs', 'application/javascript'],
    '/chat/voice/assets/ort-wasm-simd-threaded.wasm' => ['chat/voice/assets/ort-wasm-simd-threaded.wasm', 'application/wasm'],
    '/chat/voice/assets/silero_vad_v5.onnx' => ['chat/voice/assets/silero_vad_v5.onnx', 'application/octet-stream'],
    '/voice/speech.js' => ['voice/speech.js', 'application/javascript; charset=utf-8'],
    '/task-exec/commands.json' => ['task-exec/commands.json', 'application/json'],
];
if ($path === '/api/stats.php') { require $root . '/api/stats.php'; exit; }
if (!is_string($path) || !isset($files[$path])) fail(404, 'Recurso no disponible.');
[$file, $mime] = $files[$path];
$file = $root . '/' . $file;
if (!is_readable($file)) fail(503, 'Recurso no disponible.');
header('Content-Type: ' . $mime);
header('Content-Length: ' . filesize($file));
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'HEAD') readfile($file);
