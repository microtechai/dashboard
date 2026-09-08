// Compatibility path only. The canonical classic-script module is shaders.js.
// index.html creates JarvisFire.createFire({THREE, coreGroup}) synchronously
// and calls update(delta) from its existing render loop. No auto-init here:
// loading this legacy file must not create another fire, group, or RAF.
