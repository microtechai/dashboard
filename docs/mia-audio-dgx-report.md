# MIA: audio integrity diagnosis with actual DGX Qwen

## Evidence and scope
- Repository branch `feat/mia-reactor-integration`, PR #8, baseline `fb40369aea13a2a04a05dc3f65ef3b08cd382314`. Existing untracked evidence left untouched.
- Live origin source hashes matched local baseline for index, API and capture/core/worker/speech. No private conversation or credential logs collected.
- Actual DGX request: `qwen3-coder-next`, HTTP 200, handle `chatcmpl-a9992b29b2514b8f`, 6861 input / 2324 output tokens, 60.031 s. Exact running/waiting metrics both zero before single request. Input 23634 characters (slightly above approximate 20k target), max output 6000 tokens. Raw review and usage stored outside Git in `/home/ddr/mia-audio-dgx-diagnosis/`.

## Confirmed bugs, not claims about the owner's recordings
1. Emoji deletion fused adjacent words and numbers at BOTH frontend normalization and final PHP TTS stdin boundary. Controlled original `Buenos👩🏽‍💻días. Revisa🇪🇸mañana. 10❤️25.` became `Buenosdías. Revisamañana. 1025.`. Separate JS and actual PHP/fixture-stdin tests failed before fixes. Replacement with spaces now produces `Buenos días. Revisa mañana. 10 25.`. Emoji stay silent; regular decimal/currency/minus/math text stays unchanged; history stays original.
2. A single 1213-character sentence containing normal words was entirely rejected even though it fits two requests. Before: no TTS chunks, limit notice. After: 998 + 214 characters, rejoined text exactly equals original, final word retained. Splitting only at existing spaces retains the remainder. Existing max 3 requests / 1000 characters each stays in force. An indivisible oversized token or overall budget overflow gives one existing explicit notice; never a half-word or silent truncation.

## Capture/STT/TTS trace and limits
- Controlled 1-second tones at 44100 and 48000 input samples both yielded 16000 output samples: 15872 posted + 128 buffered. Injected-probability VAD fixture emitted 27648 samples / 55340 WAV bytes with start/end markers retained. This tests sample accounting, NOT physical speech onset, acoustic cancellation or human STT accuracy.
- Live STT stays CPU1, int8, one thread, Spanish, beam1, VAD filter on, 20s decoded cap; no tuning or model install.
- Live female Piper stays sharvard medium speaker1, map M0/F1, 22050Hz, es_ES language, espeak voice `es`, default length_scale1/noise_scale0.667/noise_w0.8. No foreign phonemizer configuration was found.
- Actual CPU0 Piper synthesized six controlled chunks before and six after as www-data using live voice configuration. WAV samples/bytes/hashes/times and three synthetic round-trip STT transcripts per phase are in `synthesis-baseline.json` and `synthesis-after.json`. Baseline STT misrecognized `quedan` as `queden` on one synthetic sample. Round trips do not establish natural STT quality or prove the voice sounds natural.
- Audition files: baseline `2-0.wav`, `2-1.wav`; corrected `after-2-0.wav`, `after-2-1.wav`, all under `/home/ddr/mia-audio-dgx-diagnosis/`. Raw controlled text / sanitized / exact chunk lists: `baseline-chain.json`, `after-chain.json`. No user microphone was accessed; no public-human corpus used.

## Independent review of Qwen proposals
Accepted: inspect boundaries separately, controlled reproducible tests, distinguish budgets and quality limits.
Rejected as unsupported/harmful: lower pre-roll or 4-frame confirmation, normalize all numbers with num2words, discard sentence remainder using slice, speak emoji descriptions, retune female voice/noise/speed without audition. Qwen incorrectly claimed pre-roll adds 512ms waiting, loses retained onset, and blocked state requires session restart: actual source retains the ring and clears blocked after silence. It also overclaimed phonemizer/naturalness root causes without hearing audio. Its assessment is advisory, not approval.

## Verified release outcome
- Deployed four files with baseline SHA guards and fresh independent remote SHA verification. Backup: `/root/mia-audio-integrity-20260908T234827Z`; manifest outside Git: `deployment-manifest.json`. No service restart or voice/STT config change.
- Final regression: 99 executed test cases across suites (including inherited backend cases), 98 passed / 1 skipped / 0 failed; PHP lint and JS syntax checks passed. `stt_backend_test.py` reported one skip; do not count it as passed.
- Edge and origin anonymous checks: `/` 303 to login, login200, exact new versioned audio module/controller URLs401 and private no-store, session API200. Private authenticated served-body/runtime acceptance was not bypassed: independent SSH verifies deployed bytes, anonymous HTTP verifies the gate.
- Application: https://dashboard.microtechai.es/ . Audio module version: `/chat/voice/speech.mjs?v=20260909-audio-integrity1`; controller `/chat/chat.js?v=20260909-audio-integrity1`.
- Selective rollback: for each of the four manifest files, first verify current SHA equals `after`, then atomically restore only that file from the backup and verify `before`. Refuse rollback on drift; do not reset whole repository or config.

## Remaining acceptance
The user's real STT loss, premature end VAD, false acoustic barge-in and perceived foreign accent remain unresolved without an owner-supplied short manual audio upload and listening comparison. Do not advertise human transcription or voice naturalness fixed. No architecture change, paid provider, male fallback, physical microphone permission or DGX service restart.

Targeted tests and one final audio/call/security regression run are recorded in `/home/ddr/mia-audio-dgx-diagnosis/final-tests.json`. Deployment status and rollback hashes are recorded separately in that directory's deployment manifest. Index/chat controller changes, if present, only advance audio-import cache versions, no visual edits.
