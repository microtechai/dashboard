# JARVIS chat frontend

## Parent integration

Deployed once in `index.html` (phases 3+4):

```html
<link rel="stylesheet" href="chat/chat.css?v=20260908-chat4">
<script defer src="chat/chat.js?v=20260908-chat4"></script>
```

The stylesheet belongs in head. The deferred script may be in head or near the existing integration scripts. It self-mounts `#jarvis-chat` after DOM ready; no other HTML container, npm build, external CDN, API key, or global initializer is needed. It does not modify the old dashboard login, executor, scene, camera, or canvas. Chat initially collapses to a bottom-right launcher. Expanded desktop size is 400×460 maximum, mobile width viewport minus 24px and height at most 65dvh. Minimization preserves the current conversation and does not silently stop audio; Detener does. On narrow displays users can minimize the executor/chat independently.

Listen on `window` for:

```js
window.addEventListener('jarvis-chat-state', ({ detail }) => {
  // Validate before passing to the single existing nucleus controller:
  // detail.state: 'idle' | 'thinking' | 'speaking' | 'listening' | 'transcribing'
  // detail.level: finite number clamped to [0, 1]
});
```

Thinking covers response streaming and WAV preparation. Speaking begins only after successful media playback; level is the actual time-domain RMS from an AudioContext analyser, not synthetic random animation. There is one analysis RAF while playing, no new 3D renderer, explicit-click microphone access only, and no speechSynthesis fallback. Without AudioContext, media can still play and level is zero. Media autoplay errors leave a visible Leer retry button and an explicit status message.

## API alignment

Read and aligned with `docs/backend-contract.md`:

- Same-origin `/api/chat.php?action=session|login|logout|message|tts|transcribe`; fetch credentials `same-origin`, no-store. Browser sends Origin naturally; frontend does not forge it.
- GET session supplies `{authenticated,csrf,username,history:[{role,content}]}`. Every POST sends `X-CSRF-Token`; transcribe uses FormData, other actions JSON. Login sends only `{username,password}` and refetches session for rotated CSRF/history. Password input clears immediately; credentials are not stored in local/session storage.
- Logout posts `{}`, consumes rotated CSRF, immediately clears private visible history, and refetches session. Session refresh failures have an explicit retry button. 401 hides/clears chat history; 403/503 expose session refresh without automatically resending a message.
- Message sends only `{text}`; input maxlength 4000 UTF-16 code units (conservative compared with backend Unicode-character limit). Enter sends, Shift+Enter inserts newline, IME composition does not send.
- SSE delta/done carry `{text}`, error carries `{error}`. Uses streaming UTF-8 decoder, arbitrary byte boundaries, LF/CRLF/CR line endings, multiline data and JSON validation. Premature EOF/malformed payload/server errors are visible, never replaced with a fabricated model answer. AbortController plus generation IDs prevent stale response/audio updates.
- Backend owns fixed Qwen model, 1024 output tokens, authentication, rate limits and persistent history. Frontend retains at most 40 visible messages, at most 32000 code units per assistant output and 256KB of SSE wire data. No assistant text executes as HTML or commands.
- TTS sends serial `{text}` chunks no longer than 1000 code units, split preferentially at sentence/word boundaries, preserving surrogate pairs. No arbitrary chunk-count truncation. Backend TTS 20/min rate limit remains authoritative and can stop exceptionally long readings with an explicit error. Auto-read is OFF by default and in Phase4 applies only to replies to microphone input, never typed messages. Completed assistant/history messages have Leer; Detener aborts fetch, pauses/unloads media, disconnects nodes, revokes URLs and cancels RAF. URLs are also revoked on completion/error.

## Local verification (not public authentication)

```sh
cd /home/ddr/jarvis-phase2-20260908
python3 tests/chat_frontend_test.py
JARVIS_TEST_WAV=/home/ddr/jarvis-phase3-artifacts/voice-check.wav python3 tests/chat_frontend_test.py
node --check chat/chat.js
```

Python Playwright with `/usr/bin/chromium`; no local HTTP server or live API required. Every API request is explicitly intercepted at `http://chat-fixture.test`; test username/password are unmistakably dummy values. Browser tests were added in red/green feature slices. Coverage: responsive minimization, login/CSRF rotation, safe XSS rendering, UTF-8 byte-split/multiline SSE, errors/EOF, abort/stale callbacks, logout cancellation/private-history clearing, session recovery, read/auto-read, blocked autoplay, serial chunks, URL cleanup and real WAV decoding/analyser level.

Default WAV test uses a generated sine-wave file only as decoder evidence. Setting JARVIS_TEST_WAV substitutes the parent's actual Piper-generated `voice-check.wav` (mono PCM16 22050Hz, approximately six seconds), locally served through the fixture TTS route. The real browser produced nonzero analyser RMS and successfully stopped/revoked this actual WAV. Queue and autoplay-denial tests additionally use clearly marked media doubles for deterministic lifecycle edges.

Screenshots `tests/chat_frontend_fixture_desktop.png` and `tests/chat_frontend_fixture_mobile.png` are labelled **ISOLATED MOCK API FIXTURE — NOT LIVE** and have been visually inspected. They are not deployed dashboard screenshots.

Pending parent/user verification: real secure-cookie MC login with user-supplied credentials, public authenticated SSE/TTS, integration with the existing nucleus, real speaker audibility and browser/mobile autoplay policies. See `phase3-4-report.md` for consolidated real deployment and Qwen/CPU evidence. These isolated tests are not public authenticated acceptance.
