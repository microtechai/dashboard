# JARVIS Phase 2 — electric-blue fire repair

Status: deployed to production; technical verification PASS. Full authenticated visual acceptance by the owner remains pending. Chat/TTS/voice-to-voice are NOT implemented by this phase.

Tracking: https://github.com/microtechai/dashboard/issues/1

## Approved scope

Direct production intervention, no staging deployment and no full-site/server/database backup. Preserve only prior versions of the four affected core files. No voice, API, login, CSS/layout, Nginx, or model/service changes.

## Root causes and repair

- `fire/shaders.js` introduced global lexical names that collided with the inline dashboard script, preventing the scene from starting.
- Two fire implementations overlapped; the new `updateFire` was not wired into the render loop, and the loader created another group.
- Replace with a scoped `JarvisFire` namespace and explicit `createFire({THREE, coreGroup})` controller. One existing scene and one existing RAF own updates.
- Four crossed shader planes, coherent advected noise, tapered flame silhouettes extending beyond the core, electric-blue/cyan highlights. This is shader-based fire in a 3D scene, not a volumetric raymarcher.
- Reduce opacity/depth writing of the existing central mesh so it does not hide the flames. Preserve camera, layout and navigation.
- Clamp time steps and state, dispose shared geometry/materials exactly once, respect reduced-motion preference by slowing fire without hiding it.
- Version changed script URLs to avoid mixing cached old/new assets. Voice URL unchanged.
- Keep the old `fire/integration.js` path as a no-op compatibility file, without a second initializer.

## Qwen contribution and review

An actual request to the existing DGX `qwen3-coder-next` endpoint returned HTTP 200, request id `chatcmpl-a98dc9093fbf7779`, 3399 prompt tokens / 3780 completion tokens, finish reason `stop`.

Qwen proposed the scoped controller, crossed planes and coherent noise. Hermes reviewed and corrected its draft before use: the raw draft incorrectly derived height from Z while its planes remained at Z=0, which would make the fire invisible; it also rotated around the wrong axis and had shared-resource disposal/registry issues. No tests are attributed to Qwen's text response. Hermes ran the tests and reviewed images.

## Executed verification

1. RED: baseline shared classic declarations reproduced `Identifier 'fireVertexShader' has already been declared`; initial controller/wiring regression tests failed.
2. GREEN: `node --test tests/fire.test.cjs` — 5 passing, 0 failing.
3. Shared classic script syntax and scope check — PASS; login/UI/styles/API block unchanged.
4. `python3 tests/fire_webgl.py` — real Chromium WebGL using ANGLE SwiftShader, not mocked GLSL. Program linking PASS, `glError=0`, visible changed pixels outside the core and different rendered checksums over time. Images inspected at camera distances 100 and 30 and another orbit angle.
5. Isolated full-page candidate boot — PASS, untouched login, canvas 1200x800, four fire planes, advancing fire time, no page errors.
6. ACTUAL `https://dashboard.microtechai.es/`, without request interception — PASS in WebGL-capable Chromium: public HTML and changed JS match reviewed bytes, four fire planes, advancing time, linked programs, no page errors and `glError=0`.
7. Origin HTTPS bodies match on-disk versions. `voice/speech.js` hash unchanged. Nginx and dashboard-api remain active; no restarts performed.
8. Post-deployment server snapshot: load average 0.02 / 0.03 / 0.00; memory available 2.8 GiB. This is a snapshot, not a before/after performance benchmark.

The primary browser automation session cannot create any WebGL context (`getContext('webgl')` returns null; Three.js logs `Error creating WebGL context`). This environment limitation was independently confirmed, not blamed on user cache. A separate Chromium with functioning software WebGL passed the actual production URL. Its login overlay was not bypassed. Authenticated end-to-end visual acceptance and physical-device FPS remain pending; no 30 FPS claim is made.

## Evidence

- `tests/fire-red.tap`, `tests/fire-green.tap`: actual test transcripts.
- `docs/evidence/core-close.png`, `docs/evidence/core-normal.png`: isolated component renders of the deployed fire code; not authenticated production dashboard screenshots.
- `docs/evidence/webgl-results.json`: real component pixel/program checks.

## Deployed SHA256

| File | SHA256 |
|---|---|
| index.html | 37a9ccee7d25988b747609799531579da0dc0d2f39a49be4c05f93820ba88871 |
| fire/shaders.js | 38951e11d2f4accb384a33b84c33b5eb35ecb51e7b95e20b7da3b0a59c780e39 |
| fire/integration.js | 1c858e843492d893db3afcf48838a357cf43a9301bc90658ed6cd23f63a3d1ef |
| integration.js | 7073bf237503f2a94b81dabf231d65718d3862e28461ffa87d1dee158e39f4fe |

## Reproduction

Node.js and Python with Playwright plus `/usr/bin/chromium` are required. The matching Three.js r128 UMD library is vendored for tests with its MIT license.

```sh
node --test tests/fire.test.cjs
python3 tests/fire_webgl.py
```

The WebGL test intercepts only its isolated component files in memory; it does not deploy a staging server or access dashboard authentication.

## Follow-up / GO-NO-GO

- GO: core patch technically deployed and verified.
- Pending: owner visual acceptance in an authenticated WebGL-capable browser and device performance measurement.
- NO-GO: expanding into chat/voice/API without the next phase's authorization and security review.
- GitHub issue comment/edit API attempts returned 403 with the current token. Code/report are preserved through Git; do not imply the issue was updated.
