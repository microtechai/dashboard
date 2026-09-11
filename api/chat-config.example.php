<?php
// Install OUTSIDE webroot as /etc/jarvis-chat/config.php, root:www-data 0640.
// No credentials, public upstreams, or client-selected configuration.
return [
    'origin' => 'https://dashboard.microtechai.es',
    'state_dir' => '/var/lib/jarvis-chat', // www-data, mode 0700; PHP sessions and global locks
    'auth_base' => 'http://127.0.0.1:9090',
    'model_url' => 'http://127.0.0.1:18010/v1/chat/completions', // private reverse SSH tunnel
    'piper_python' => '/opt/jarvis-tts/venv/bin/python',
    'piper_model' => '/opt/jarvis-tts/models/es_ES-davefx-medium.onnx',
    'tts_temp_dir' => '/var/lib/jarvis-chat', // private, writable; never webroot or shared /tmp
];
