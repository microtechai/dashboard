"""Real Chromium/WebGL isolated fire test; no dashboard or authentication accessed."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path('/home/ddr/jarvis-fire-artifacts')
ARTIFACTS.mkdir(exist_ok=True)
ALLOWED = {
    '/': (ROOT / 'tests/fire-webgl.html', 'text/html'),
    '/three.js': (ROOT / 'tests/vendor/three-r128.cjs', 'text/javascript'),
    '/fire/shaders.js': (ROOT / 'fire/shaders.js', 'text/javascript'),
}
results = []
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
        args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1200, 'height': 800})
    def route(request):
        from urllib.parse import urlparse
        key = urlparse(request.request.url).path
        if key in ALLOWED:
            file, mime = ALLOWED[key]
            request.fulfill(body=file.read_bytes(), content_type=mime)
        else:
            request.abort()
    page.route('**/*', route)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
    page.goto('http://fire-component.test/')
    for distance, angle in [(100, 0), (30, 0), (30, 1.57)]:
        before = page.evaluate('([d,a])=>sample(d,a,0)', [distance, angle])
        after = page.evaluate('([d,a])=>sample(d,a,90)', [distance, angle])
        assert after['time'] > before['time'], after
        assert after['checksum'] != before['checksum'], 'Rendered pixels must animate'
        assert after['outsideCore'] > 50, after
        assert after['blue'] > after['changed'] * 0.95, after
        assert after['glError'] == 0, after
        assert after['programs'] and all(p['runnable'] for p in after['programs']), after
        name = f'fire-{distance}-angle-{angle}.png'
        page.screenshot(path=str(ARTIFACTS / name))
        results.append({'distance': distance, 'angle': angle, 'before': before, 'after': after, 'screenshot': name})
    assert not errors, errors
    browser.close()
report = {'result': 'PASS', 'backend': 'real WebGL via Chromium ANGLE SwiftShader (software GPU)', 'errors': errors, 'samples': results}
(ARTIFACTS / 'webgl-results.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
