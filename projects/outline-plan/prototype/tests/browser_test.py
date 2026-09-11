"""Render local HTML as content (no network); test prototype, not model inference.
Requires: Python + playwright + a Chromium executable. No external requests.
Usage: python browser_test.py --chromium /usr/bin/chromium --out /tmp/p1-ux-tests
"""
from pathlib import Path
import argparse, json, hashlib
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser();parser.add_argument('--chromium',required=True);parser.add_argument('--out',type=Path,required=True)
a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=True)
html=Path(__file__).resolve().parents[1]/'index.html'
source=html.read_text(encoding='utf-8');results=[];errors=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox'])
    def fresh():
        p=browser.new_page(viewport={'width':1440,'height':1120},device_scale_factor=1)
        p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_content(source,wait_until='load')
        return p
    def run(name, fn):
        p=fresh()
        try:
            fn(p);results.append({'name':name,'status':'PASS'})
        except Exception as e:
            results.append({'name':name,'status':'FAIL','error':str(e)})
        finally: p.close()
    def confirm(p):p.check('#scaleConfirmed')
    def to_params(p):confirm(p);p.locator('[data-action=next]').click()
    def to_models(p):to_params(p);p.locator('[data-action=next]').click()
    def blocked(p):
        p.locator('[data-action=next]').click()
        assert p.evaluate('P1Prototype.getState().step')==1
    run('unconfirmed scale prevents continuation',blocked)
    def metric(p):
        p.fill('#scaleWidth','60');p.locator('#scaleWidth').press('Tab')
        assert p.locator('#heightText').inner_text()=='48.00 m'
        assert p.locator('#areaText').inner_text()=='1920.0 m²'
        assert not p.is_checked('#scaleConfirmed')
    run('uniform metric calibration',metric)
    def importer(p):
        p.locator('[data-action=openImport]').click()
        p.fill('#svgText',"<svg xmlns='http://www.w3.org/2000/svg'><path d='M0 0H40V10H10V30H0Z'/></svg>")
        p.locator('[data-action=importText]').click()
        assert len(p.evaluate('P1Prototype.getState().points'))==6
        assert not p.is_checked('#scaleConfirmed')
    run('simple SVG import does not grant scale approval',importer)
    def unsafe(p):
        for text in ["<svg><script>alert(1)</script><rect width='4' height='4'/></svg>","<svg><g transform='translate(1)'><rect width='4' height='4'/></g></svg>","<svg><path d='M0 0Q5 5 10 0Z'/></svg>"]:
            assert p.evaluate('(s)=>{try{P1Prototype.parseSVG(s);return false}catch(e){return true}}',text)
    run('script transform and curve input rejected explicitly',unsafe)
    def screenpoint(p,x,y):
        return p.evaluate('([x,y])=>{let s=document.querySelector("#editor"),q=s.createSVGPoint();q.x=x;q.y=y;let r=q.matrixTransform(s.getScreenCTM());return [r.x,r.y]}',[x,y])
    def drag(p):
        before=p.evaluate('P1Prototype.getState().points')
        x,y=screenpoint(p,10,0);xx,yy=screenpoint(p,11,0)
        p.mouse.move(x,y);p.mouse.down();p.mouse.move(xx,yy,steps=3);p.mouse.up()
        assert p.evaluate('P1Prototype.getState().points')!=before
        p.locator('[data-action=undo]').click()
        assert p.evaluate('P1Prototype.getState().points')==before
        p.locator('[data-action=redo]').click()
        assert p.evaluate('P1Prototype.getState().points')!=before
    run('vertex drag undo redo',drag)
    def draw(p):
        p.locator('[data-tool=draw]').click()
        for x,y in [(2,2),(9,2),(9,9),(2,9),(2,2)]:
            sx,sy=screenpoint(p,x,y);p.mouse.click(sx,sy)
        assert len(p.evaluate('P1Prototype.getState().points'))==4
    run('closed polygon drawing',draw)
    def allocation(p):
        to_params(p);p.fill('#param-racks','25');p.locator('#param-racks').press('Tab')
        assert '相差 1' in p.locator('.alert').inner_text()
        p.locator('[data-action=next]').click();assert p.evaluate('P1Prototype.getState().step')==2
        p.locator('[data-action=allocate]').first.click()
        s=p.evaluate('P1Prototype.getState().params')
        assert sum(r['racks'] for r in s['rows'])==25
        assert '9 台' in p.locator('main').inner_text()
    run('25 cabinets no silent rounding or generation',allocation)
    def invalid(p):
        to_params(p);p.fill('[data-row="0"][data-key="rooms"]','1.5');p.locator('[data-row="0"][data-key="rooms"]').press('Tab')
        assert '非负整数' in p.locator('.alert').inner_text()
        p.locator('[data-action=next]').click();assert p.evaluate('P1Prototype.getState().step')==2
    run('invalid fractional counts stay editable without crash',invalid)
    def snapshot(p):
        to_models(p);p.select_option('#seedCount','3');p.locator('[data-action=next]').click()
        assert p.evaluate('P1Prototype.getState().step')==4
        s=p.evaluate('P1Prototype.getState().snapshot');assert len(s['sha256'])==64
        assert s['payload']['model_execution'] is False
        p.locator('[data-step="2"]').click();p.fill('#param-desks','25');p.locator('#param-desks').press('Tab')
        assert p.evaluate('P1Prototype.getState().snapshot') is None
    run('frozen snapshot and invalidation',snapshot)
    def trace(p):
        to_models(p);p.locator('[data-action=next]').click()
        p.locator('[data-action=traceNext]').click()
        assert '流程示例 · 未执行' in p.locator('.timeline').inner_text()
        p.locator('[data-action=next]').click()
        assert '不是当前参数的求解结果' in p.locator('main').inner_text()
        assert p.locator('[data-action=favorite]').is_enabled()
        assert p.get_by_role('button',name='确认并交给 P2（未接入）').is_disabled()
    run('fixed schematic and NOT_RUN labels',trace)
    def svg_export(p):
        confirm(p)
        with p.expect_download(timeout=7000) as d:p.locator('[data-action=exportSVG]').click()
        f=a.out/'exported_outline.svg';d.value.save_as(f)
        t=f.read_text();assert '30.00 m' in t and '24.00 m' in t and '无工程审查' in t
    run('actual SVG download',svg_export)
    def png_export(p):
        confirm(p)
        with p.expect_download(timeout=7000) as d:p.locator('[data-action=exportPNG]').click()
        f=a.out/'exported_outline.png';d.value.save_as(f)
        assert f.read_bytes().startswith(b'\x89PNG')
    run('actual PNG raster export',png_export)
    def responsive(p):
        p.set_viewport_size({'width':390,'height':844})
        assert p.evaluate('document.documentElement.scrollWidth')<=392
    run('mobile initial screen no horizontal overflow',responsive)
    p=fresh();p.screenshot(path=str(a.out/'01-outline.png'),full_page=True)
    to_params(p);p.screenshot(path=str(a.out/'02-parameters.png'),full_page=True)
    p.locator('[data-action=next]').click();p.screenshot(path=str(a.out/'03-models.png'),full_page=True)
    p.locator('[data-action=next]').click()
    for _ in range(3):p.locator('[data-action=traceNext]').click()
    p.screenshot(path=str(a.out/'04-process.png'),full_page=True)
    p.locator('[data-action=next]').click();p.screenshot(path=str(a.out/'05-results.png'),full_page=True)
    p.close();browser.close()
report={'scope':'P1 browser prototype only; HTML loaded as local content, no network navigation','html_sha256':hashlib.sha256(html.read_bytes()).hexdigest(),'cases':results,'page_errors':errors,'model_inference':'NOT_RUN','localStorage_persistence':'NOT_TESTED (opaque renderer origin)','file_http_navigation':'not tested: managed Chromium policy blocks navigation; policy unchanged','production_backend':'NOT_IMPLEMENTED'}
(a.out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results),'page_errors':errors}))
if any(x['status']=='FAIL' for x in results) or errors:raise SystemExit(1)
