// Passive bridge: the existing Three.js RAF owns every core update.
(function (root) {
  'use strict';
  let state = 'idle', level = 0, updated = 0;
  root.addEventListener('jarvis-chat-state', function (event) {
    const detail = event.detail;
    if (!detail || !['idle', 'thinking', 'speaking', 'listening', 'transcribing'].includes(detail.state)) return;
    state = detail.state;
    level = Number.isFinite(detail.level) ? Math.max(0, Math.min(1, detail.level)) : 0;
    updated = root.performance.now();
  });
  root.JarvisCoreState = Object.freeze({
    boost(now, time, reducedMotion) {
      // Audio level is supplied by the playing WAV analyser, never invented.
      // A missing stream of audio events must not leave the nucleus "speaking".
      if (['speaking', 'listening'].includes(state) && now - updated > 1000) return 0;
      if (['thinking', 'transcribing'].includes(state) && now - updated > 90000) return 0;
      const amount = ['speaking', 'listening'].includes(state) ? level * 0.8 :
        ['thinking', 'transcribing'].includes(state) ? 0.25 + Math.sin(time * 5) * 0.1 : 0;
      return amount * (reducedMotion ? 0.2 : 1);
    }
  });
})(window);
