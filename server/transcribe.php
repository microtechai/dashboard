<?php
// Installed outside document root; included only after MC + Origin + CSRF + upload validation.
$lock = workerLock('transcribe');
session_write_close();
ignore_user_abort(true);
set_time_limit(50);
$process = null; $pipes = []; $tmp = false; $output = ''; $result = null;
try {
    $tmp = tempnam($config['state_dir'], 'stt-');
    if ($tmp === false || dirname($tmp) !== realpath($config['state_dir'])) throw new RuntimeException('temp');
    if (!move_uploaded_file($upload['tmp_name'], $tmp)) throw new RuntimeException('upload');
    chmod($tmp, 0600);
    $process = proc_open(['/usr/bin/taskset', '-c', '1', '/opt/jarvis-stt/venv/bin/python', '/opt/jarvis-stt/stt_worker.py', $tmp],
        [0 => ['file', '/dev/null', 'r'], 1 => ['pipe', 'w'], 2 => ['file', '/dev/null', 'w']], $pipes,
        null, ['OMP_NUM_THREADS' => '1', 'OPENBLAS_NUM_THREADS' => '1', 'PATH' => '/usr/bin:/bin', 'LANG' => 'C.UTF-8', 'HOME' => $config['state_dir'], 'HF_HUB_OFFLINE' => '1']);
    if (!is_resource($process)) throw new RuntimeException('process');
    stream_set_blocking($pipes[1], false);
    $deadline = microtime(true) + 40;
    do {
        $output .= stream_get_contents($pipes[1]);
        if (strlen($output) > 32768 || microtime(true) >= $deadline || connection_aborted()) throw new RuntimeException('limit');
        $status = proc_get_status($process);
        if (!$status['running']) break;
        usleep(20000);
    } while (true);
    $output .= stream_get_contents($pipes[1]);
    $exit = $status['exitcode'];
    $closed = proc_close($process); $process = null;
    if (($exit === -1 ? $closed : $exit) !== 0 || strlen($output) > 32768) throw new RuntimeException('exit');
    $data = json_decode($output, true);
    if (!is_string($data['text'] ?? null) || !mb_check_encoding($data['text'], 'UTF-8') || mb_strlen($data['text']) > 4000) throw new RuntimeException('result');
    $result = ['text' => $data['text']];
} catch (Throwable $e) {
    $result = null;
} finally {
    foreach ($pipes as $pipe) if (is_resource($pipe)) fclose($pipe);
    if (is_resource($process)) {
        $status = proc_get_status($process);
        if ($status['running']) { proc_terminate($process, 9); }
        proc_close($process);
    }
    if ($tmp !== false && is_file($tmp)) unlink($tmp);
    flock($lock, LOCK_UN); fclose($lock);
}
if ($result === null) fail(502, 'No se pudo transcribir. Máximo 20 segundos.');
reply($result);
