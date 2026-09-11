"""Repository loading smoke test: directory HTTP and generated standalone file."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse
import argparse
import json
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run(standalone: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    report = {'purpose': 'INTERACTION_PROTOTYPE_ONLY', 'modelExecuted': False,
              'bimfaceConnected': False, 'results': [], 'errors': []}
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        report['results'].append({'name': name, 'status': 'PASS'})

    def state(page):
        return page.evaluate('P3Demo.summary()')

    def point(page, x, y):
        s = state(page)
        bounds = page.locator('#planCanvas').bounding_box()
        return (bounds['x'] + s['view']['x'] + x * s['view']['s'],
                bounds['y'] + s['view']['y'] + y * s['view']['s'])

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ.get('P3_CHROMIUM') or None,
                                         headless=True, args=['--no-sandbox'])
            for mode, url in [('directory', origin + '/index.html'), ('standalone', standalone.resolve().as_uri())]:
                context = browser.new_context(viewport={'width': 1440, 'height': 900})
                external = []
                failures = []
                context.on('request', lambda r: external.append(r.url)
                           if urlparse(r.url).scheme in ('http', 'https') and urlparse(r.url).netloc != urlparse(origin).netloc else None)
                page = context.new_page()
                page.on('pageerror', lambda error: failures.append(str(error)))
                page.goto(url)
                page.wait_for_selector('body[data-ready="true"]')
                check(mode + ': project home', page.locator('.project-card').count() == 3)
                page.locator('.project-card').first.click()
                page.wait_for_timeout(200)
                check(mode + ': canvas-first', not page.locator('#home').is_visible() and
                      not page.locator('#sideDrawer').is_visible() and not state(page)['formVisible'])
                page.click('[data-tool=rect]')
                page.mouse.move(*point(page, 400, 300)); page.mouse.down()
                page.mouse.move(*point(page, 520, 342), steps=8); page.mouse.up()
                page.wait_for_selector('#objectName')
                page.fill('#objectName', '同步验证标注')
                page.click('#saveAnnotation')
                s = state(page)
                check(mode + ': manual box and revision', s['revision'] == 'r1' and len(s['items']) == 7)
                check(mode + ': source-space coordinates', all(abs(a-b) < .4 for a,b in zip(s['items'][-1]['rect'], [400,300,120,42])))
                check(mode + ': editor dismissed', not s['formVisible'])
                page.click('#floorBtn'); page.click('[data-fid=F02]'); page.wait_for_timeout(120)
                check(mode + ': floors isolated', state(page)['floorId'] == 'F02' and len(state(page)['items']) == 6)
                page.click('#floorBtn'); page.click('[data-fid=F01]'); page.wait_for_timeout(120)
                page.click('#generateBtn')
                check(mode + ': confirmation required', page.locator('#startGeneration').is_disabled())
                page.check('#demoConsent'); page.click('#startGeneration')
                page.click('#toggleTask')
                check(mode + ': progress collapses', page.locator('.task-details').count() == 0)
                page.click('#toggleTask'); page.click('#cancelTask')
                check(mode + ': cancel preserves version', state(page)['job'] is None and state(page)['revision'] == 'r1')
                page.click('#generateBtn'); page.check('#demoConsent'); page.click('#startGeneration')
                page.wait_for_function('P3Demo.summary().job===null', timeout=10000)
                check(mode + ': no fake files', state(page)['result']['architectureFilesCreated'] is False)
                page.click('#previewResult')
                check(mode + ': downloads disabled', all(page.get_by_role('button', name='下载 ' + ext, exact=True).is_disabled() for ext in ['DXF', 'PDF', 'GLB']))
                page.click('#openSplit'); page.wait_for_timeout(100)
                check(mode + ': optional split', state(page)['modelOpen'] and page.locator('#modelArea').is_visible())
                page.screenshot(path=str(out / (mode + '-split.png')))
                page.click('#closeModel')
                if mode == 'directory':
                    check('directory: IndexedDB available', state(page)['persistence'])
                    page.wait_for_timeout(500)
                    page.reload(); page.wait_for_selector('body[data-ready="true"]')
                    page.locator('.project-card').first.click(); page.wait_for_timeout(150)
                    check('directory: reload restores saved annotation', state(page)['revision'] == 'r1' and len(state(page)['items']) == 7)
                check(mode + ': no external service requests', not external)
                check(mode + ': no JS errors', not failures)
                check(mode + ': model remains unexecuted', state(page)['modelExecuted'] is False)
                context.close()
            browser.close()
        report['status'] = 'PASS'
    except Exception as exc:
        report['status'] = 'FAIL'
        report['errors'].append(str(exc))
        raise
    finally:
        server.shutdown(); server.server_close()
        report['checks'] = len(report['results'])
        (out / 'smoke-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"{report['checks']} repository loading checks passed")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--standalone', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.standalone, args.out)
