"""Isolated UI regression test. API responses below are test fixtures, not live data."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
posts=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':900})
    def route(r):
        if r.request.method=='POST': posts.append(r.request.url)
        if r.request.url.endswith('/integration.js'):
            r.fulfill(body=(ROOT/'integration.js').read_bytes(),content_type='text/javascript')
        elif '/api/commands' in r.request.url:
            r.fulfill(body='{"success":true,"commands":[]}',content_type='application/json')
        else:
            r.fulfill(body='<html><body><script>window.THREE={};</script><script src="/integration.js"></script></body></html>',content_type='text/html')
    page.route('**/*',route)
    page.add_init_script('window.initialStorageCount=localStorage.length')
    page.goto('http://executor-component.test/')
    assert page.evaluate('initialStorageCount')==0,'fresh isolated desktop storage'
    field=page.locator('#executor-input')
    expect(field).to_be_visible()
    field.fill('Borrador de prueba: NO EJECUTAR')
    toggle=page.get_by_role('button',name='Minimizar Task Executor',exact=True)
    expect(toggle).to_have_count(1,timeout=1500)
    toggle.click()
    expect(field).to_be_hidden()
    restore=page.get_by_role('button',name='Restaurar Task Executor',exact=True)
    expect(restore).to_have_attribute('aria-expanded','false')
    restore.focus(); page.keyboard.press('Enter')
    expect(field).to_be_visible()
    expect(field).to_have_value('Borrador de prueba: NO EJECUTAR')
    page.get_by_role('button',name='Minimizar Task Executor',exact=True).click()
    page.reload()
    expect(page.locator('#executor-input')).to_be_hidden()
    # Restore desktop, then verify the separately stored tablet/mobile default.
    page.get_by_role('button',name='Restaurar Task Executor',exact=True).focus();page.keyboard.press('Enter')
    expect(field).to_be_visible()
    desktop_pref=page.evaluate('localStorage.getItem("jarvis.executor.minimized")')
    page.set_viewport_size({'width':900,'height':700})
    expect(field).to_be_hidden()
    restore=page.get_by_role('button',name='Restaurar Task Executor',exact=True)
    restore.focus();page.keyboard.press('Enter');expect(field).to_be_visible()
    field.fill('Borrador tablet: NO EJECUTAR')
    page.get_by_role('button',name='Minimizar Task Executor',exact=True).click();expect(field).to_be_hidden()
    page.get_by_role('button',name='Restaurar Task Executor',exact=True).click();expect(field).to_be_visible()
    expect(field).to_have_value('Borrador tablet: NO EJECUTAR')
    page.get_by_role('button',name='Minimizar Task Executor',exact=True).click()
    page.set_viewport_size({'width':390,'height':844});expect(field).to_be_hidden()
    assert page.evaluate('localStorage.getItem("jarvis.executor.minimized")')==desktop_pref
    page.set_viewport_size({'width':1280,'height':900});expect(field).to_be_visible()
    expect(field).to_have_value('Borrador tablet: NO EJECUTAR')
    page.evaluate('loadTaskExecutor()')
    expect(page.locator('#task-executor-panel')).to_have_count(1)
    assert not posts,posts
    print('PASS: minimize, restore via keyboard, draft preservation, persistence, idempotent init, no command execution')
    browser.close()
