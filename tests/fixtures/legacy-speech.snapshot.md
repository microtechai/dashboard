# Legacy speech snapshot

`legacy-speech.js` is a byte-exact QA snapshot of `/var/www/dashboard/voice/speech.js`, fetched before this continuation and compared again over authorized SSH on 2026-09-08.

SHA256: `9d6ce800df3d0ba354e4f68f83d5140caa30a3cb16592f620ff0d747a5c3e6d9` for both.

Retained trailing whitespace is deliberate source fidelity. `git diff --cached --check` reports it; the quality check excludes this one unmodified snapshot, not production code. Signature scan found no secret tokens/keys. Tests route the snapshot only inside an isolated local fixture; they forbid physical SpeechRecognition.start and assert that legacy setupUI/button/shortcut do not activate. This snapshot is never deployed or used to execute commands.
