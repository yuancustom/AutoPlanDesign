"""Publication regression for the deterministic UI. Requires Playwright/Chromium, no model."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

def check(page, mode: str) -> dict:
    errors = page._qa_errors
    external = page._qa_external
    page.wait_for_function("document.body.dataset.ready === 'true'")
    summary = lambda: page.evaluate('P2Demo.summary()')
    assert summary()['head'] == 'r0'
    assert summary()['mask']['allowed'] == 0
    for name in ['compare','history','audit','guide','editor']:
        page.locator('#nav-' + name).click()
        assert summary()['page'] == name
    page.locator('[data-preset="racks"]').click()
    assert summary()['mask']['allowed'] > 0
    page.locator('#undoStroke').click()
    assert summary()['mask']['allowed'] == 0
    page.locator('#redoStroke').click()
    assert summary()['mask']['allowed'] > 0
    page.locator('#previewScope').click()
    assert page.locator('#confirmGenerate').is_disabled()
    page.locator('#scopeAgree').check()
    page.locator('#confirmGenerate').click()
    page.wait_for_function("!P2Demo.summary().jobBusy && P2Demo.summary().attempts.length === 1")
    a = summary()['attempts'][0]
    assert a['status'] == 'ready' and not a['modelExecuted']
    assert a['metrics']['changedOutside'] == a['metrics']['protectedChanged'] == 0
    assert summary()['head'] == 'r0'
    page.locator('#acceptCandidate').click()
    page.wait_for_function("P2Demo.summary().head === 'r1'")
    page.locator('#nav-history').click()
    page.locator('[data-revision="r0"]').click()
    page.locator('#restoreVersion').click()
    page.locator('#confirmRestore').click()
    page.wait_for_function("P2Demo.summary().head === 'r2'")
    data = page.evaluate('P2Demo.exportState()')
    assert len(data['revisions']) == 3
    assert data['revisions'][-1]['parent'] == 'r1'
    assert data['revisions'][-1]['restoreFrom'] == 'r0'
    assert data['revisions'][-1]['image'] == data['revisions'][0]['image']
    assert not errors and not external, (errors, external)
    return {'mode':mode,'status':'PASS','scope':['five_pages','mask_undo_redo','permission_confirmation',
             'candidate_before_accept','outside_and_protected_pixels','accept_revision','append_restore','no_external_requests'],
            'model_execution':'NOT_RUN','page_errors':errors,'external_requests':external}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser')
    parser.add_argument('--standalone', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--inline', action='store_true', help='Test assembled HTML via set_content; does not claim file navigation was tested')
    args = parser.parse_args()
    results = []
    with sync_playwright() as p:
        options = {'headless':True}
        if args.browser: options['executable_path'] = args.browser
        browser = p.chromium.launch(**options)
        if args.inline:
            if not args.standalone: parser.error('--inline needs --standalone')
            targets = [('inline-assembled',args.standalone.resolve())]
        else:
            targets = [('file-directory',ROOT/'index.html')]
            if args.standalone: targets.append(('file-standalone',args.standalone.resolve()))
        for name,path in targets:
            context = browser.new_context(viewport={'width':1440,'height':1000})
            page = context.new_page()
            page._qa_errors = []
            page._qa_external = []
            page.on('pageerror', lambda e: page._qa_errors.append(str(e)))
            page.on('request', lambda r: page._qa_external.append(r.url) if r.url.startswith(('http://','https://')) else None)
            if args.inline: page.set_content(path.read_text(encoding='utf-8'))
            else: page.goto(path.as_uri())
            results.append(check(page,name))
            context.close()
        browser.close()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps({'status':'PASS','results':results},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(results,ensure_ascii=False))
