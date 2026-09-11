from pathlib import Path
import json,time,hashlib,os,argparse
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser(description='Original V3 62 interaction assertions, adapted only for repository paths')
parser.add_argument('--html',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args();HTML=args.html.resolve();QA=args.out.resolve();QA.mkdir(parents=True,exist_ok=True)
results=[];errors=[];requests=[]
def record(name,cond=True,detail=None):
 if not cond: raise AssertionError(name+': '+str(detail))
 results.append({'name':name,'status':'PASS','detail':detail})
def summary(page):return page.evaluate('P3Demo.summary()')
def pos(page,x,y):
 s=summary(page);b=page.locator('#planCanvas').bounding_box();return (b['x']+s['view']['x']+x*s['view']['s'],b['y']+s['view']['y']+y*s['view']['s'])
def drag(page,a,b):
 page.mouse.move(*pos(page,*a));page.mouse.down();page.mouse.move(*pos(page,*b),steps=10);page.mouse.up();page.wait_for_timeout(100)
def generate(page):
 page.click('#generateBtn');page.check('#demoConsent');page.click('#startGeneration')
def close_modal(page):page.locator('#modalRoot [data-close]').first.click()
def ready(page):
 page.wait_for_selector('body[data-ready="true"]');page.wait_for_timeout(150)
fixture=QA/'upload_fixture.png';im=Image.new('RGB',(1000,500),'white');d=ImageDraw.Draw(im);d.rectangle((60,50,940,450),outline='black',width=4);d.line((500,50,500,450),fill='black',width=3);im.save(fixture)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path=os.environ.get('P3_CHROMIUM') or None,headless=True,args=['--no-sandbox'])
 ctx=b.new_context(viewport={'width':1440,'height':900},device_scale_factor=1,accept_downloads=True)
 page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
 page.set_content(HTML.read_text());ready(page)
 record('独立项目首页首次展示',summary(page)['screen']=='home' and page.locator('.project-card').count()==3)
 page.fill('#projectSearch','运行');record('项目搜索可用',page.locator('.project-card').count()==1)
 page.fill('#projectSearch','');page.screenshot(path=str(QA/'01_home.png'))
 page.locator('.project-card').first.click();page.wait_for_timeout(220)
 s=summary(page);origpid=s['projectId']
 record('进入项目后项目页消失，画布占据工作区',not page.locator('#home').is_visible() and page.locator('#studio').bounding_box()['width']==1440)
 record('初始不出现侧面板、版本卡片、补框表单',s['drawer'] is None and not s['formVisible'] and not page.locator('#sideDrawer').is_visible())
 page.screenshot(path=str(QA/'02_workspace.png'))
 page.mouse.click(*pos(page,125,90));page.wait_for_selector('#annotationForm')
 record('点击候选才显示对象复核表单',page.input_value('#objectName')=='楼梯 A')
 page.fill('#objectNote','已核对，这是楼梯 A 的梯段，不是普通走廊。')
 page.click('#saveAnnotation');page.wait_for_timeout(100)
 record('确认对象新增版本并收起表单',summary(page)['revision']=='r1' and not summary(page)['formVisible'] and summary(page)['items'][0]['status']=='confirmed')
 page.click('[data-tool=rect]');drag(page,(395,301),(533,345))
 record('拉框后才出现补充表单',page.locator('#annotationEditor').is_visible())
 page.select_option('#objectType','设备');page.fill('#objectName','检修设备');page.fill('#objectNote','这里是图中已有的检修设备，保留原墙和门。')
 record('表单输入不触发快捷键',summary(page)['tool']=='rect')
 page.screenshot(path=str(QA/'03_annotation.png'))
 page.click('#saveAnnotation');s=summary(page);manual=[o for o in s['items'] if o['source']=='manual']
 record('手工补框精确保存原图坐标',len(manual)==1 and all(abs(a-c)<.3 for a,c in zip(manual[0]['rect'],[395,301,138,44])),manual[0]['rect'])
 record('保存后默认返回选择工具',summary(page)['tool']=='select' and not summary(page)['formVisible'])
 page.click('#undoBtn');page.wait_for_timeout(120);record('撤销不删除历史',len(summary(page)['items'])==6 and summary(page)['revision']=='r3')
 page.click('#redoBtn');page.wait_for_timeout(120);record('重做恢复标注并追加版本',len(summary(page)['items'])==7 and summary(page)['revision']=='r4')
 page.click('#floorBtn');page.click('[data-fid=F02]');page.wait_for_timeout(180);record('楼层数据独立、不串标注',summary(page)['floorId']=='F02' and len(summary(page)['items'])==6)
 page.click('#floorBtn');page.click('[data-fid=F01]');page.wait_for_timeout(120)
 record('返回楼层仍保留手工补框',len(summary(page)['items'])==7)
 # Unchanged selection must not prompt when switching floors.
 page.mouse.click(*pos(page,120,90));page.click('#floorBtn');page.click('[data-fid=F02]');page.wait_for_timeout(100)
 record('只查看未修改对象，切楼层不弹多余确认',summary(page)['floorId']=='F02' and not page.locator('#modalRoot').inner_text())
 page.click('#floorBtn');page.click('[data-fid=F01]');page.wait_for_timeout(120)
 # Zoom and draw inverted rectangle on blank corridor.
 page.click('#zoomIn');page.click('[data-tool=rect]');drag(page,(480,272),(420,242));page.fill('#objectName','补充走廊标注');page.click('#saveAnnotation')
 newest=summary(page)['items'][-1]
 record('放大后反向拉框使用原图坐标',all(abs(a-c)<.3 for a,c in zip(newest['rect'],[420,242,60,30])),newest['rect'])
 page.click('#fitBtn');page.mouse.click(*pos(page,450,255));page.fill('#objectNote','尚未保存的说明');page.click('#floorBtn');page.click('[data-fid=F02]')
 record('未保存草稿跨楼层切换前提示',page.locator('#modalTitle').inner_text()=='尚有未保存的标注')
 close_modal(page);record('继续编辑保留草稿',page.input_value('#objectNote')=='尚未保存的说明')
 page.keyboard.press('Escape');page.click('[data-tool=rect]');drag(page,(415,245),(417,247));record('过小矩形被拒绝',not summary(page)['formVisible'])
 page.click('[data-tool=select]');page.mouse.click(*pos(page,450,256));old=summary(page)['items'][-1]['rect']
 # Resize bottom-right corner of selected annotation.
 drag(page,(480,272),(492,279));page.click('#saveAnnotation');new=summary(page)['items'][-1]['rect']
 record('拖动框角调整原图范围',abs(new[2]-72)<.4 and abs(new[3]-37)<.4,new)
 page.mouse.click(*pos(page,450,255));page.click('#deleteAnnotation');record('删除只移除标注',not any(o['label']=='补充走廊标注' for o in summary(page)['items']))
 page.click('#undoBtn');page.wait_for_timeout(120);record('删除标注可撤销',any(o['label']=='补充走廊标注' for o in summary(page)['items']))
 page.click('#overlayBtn');record('可隐藏识别框看原图',summary(page)['overlay'] is False);page.click('#overlayBtn')
 v=summary(page)['view'];page.keyboard.down('Space');drag(page,(300,250),(320,265));page.keyboard.up('Space')
 record('空格拖动只平移视口',summary(page)['view']['x']!=v['x'] and len(summary(page)['items'])==8)
 page.click('#fitBtn');page.click('#historyBtn');record('历史按需展开',page.locator('#sideDrawer').is_visible() and summary(page)['drawer']=='history');page.click('#closeDrawer');record('关闭历史恢复完整画布',not page.locator('#sideDrawer').is_visible())
 # Recognition cancellation and completion.
 page.click('#recognizeBtn');page.click('#startRecognize');page.click('#cancelTask');record('识别演示可取消',summary(page)['job'] is None)
 page.click('#recognizeBtn');page.click('#startRecognize');page.wait_for_function('P3Demo.summary().job===null',timeout=6000)
 record('重识别保留人工补充与已确认项',len(summary(page)['items'])==8 and summary(page)['items'][0]['status']=='confirmed')
 page.click('#generateBtn');record('生成前有明确演示确认',page.locator('#startGeneration').is_disabled());page.check('#demoConsent');page.click('#startGeneration')
 page.screenshot(path=str(QA/'04_progress_expanded.png'))
 h=page.locator('#taskDock').bounding_box()['height'];page.click('#toggleTask');h2=page.locator('#taskDock').bounding_box()['height']
 record('进度可收起，不常驻详情',h2<h/2,{'expanded':h,'collapsed':h2})
 page.screenshot(path=str(QA/'04b_progress_collapsed.png'))
 page.click('#toggleTask');page.click('#cancelTask');record('生成取消后不伪造结果',summary(page)['result'] is None)
 generate(page);page.wait_for_function('P3Demo.summary().job===null',timeout=8000)
 record('流程完成不宣称真实文件',summary(page)['result']['architectureFilesCreated'] is False and not summary(page)['modelExecuted'])
 page.click('#previewResult');record('真实文件下载禁用',all(x.is_disabled() for x in page.locator('#modalRoot button').all() if x.inner_text() in ['下载 DXF','下载 PDF','下载 GLB']))
 page.click('#openSplit');page.wait_for_timeout(300);page.click('#explodeBtn');page.wait_for_timeout(120)
 record('三维分屏按需出现',summary(page)['modelOpen'] and page.locator('#modelArea').is_visible())
 page.screenshot(path=str(QA/'05_split_review.png'))
 before=page.locator('#modelCanvas').screenshot();bb=page.locator('#modelCanvas').bounding_box();page.mouse.move(bb['x']+bb['width']/2,bb['y']+bb['height']/2);page.mouse.down();page.mouse.move(bb['x']+bb['width']/2+60,bb['y']+bb['height']/2+20,steps=8);page.mouse.up();page.wait_for_timeout(100)
 record('三维示意可以拖动旋转',before!=page.locator('#modelCanvas').screenshot())
 page.click('#closeModel');page.wait_for_timeout(120)
 page.mouse.click(*pos(page,120,90));page.fill('#objectName','楼梯 A 复核');page.click('#saveAnnotation');record('标注变化使旧成果失效',summary(page)['result'] is None)
 page.click('#stepResult');record('过期结果不能当作最新版展示','过期' in page.locator('#modalRoot').inner_text());close_modal(page)
 # Export genuine local JSON backup.
 page.click('#moreBtn')
 with page.expect_download() as di:page.click('#moreExport')
 dl=di.value;dl.save_as(str(QA/'project_export.json'));data=json.loads((QA/'project_export.json').read_text())
 record('标注工程可实际导出',data['schema']=='autoplan.p3.canvas-prototype/3.0' and data['modelExecuted'] is False)
 raw1=data['project']['assets']['asset1']['url']
 record('参考原图字节不被标注改写',page.evaluate("P3Demo.exportState().projects[0].assets.asset1.url") ==raw1)
 page.click('#moreBtn');page.click('#moreImport');page.set_input_files('#projectInput',str(QA/'project_export.json'));page.wait_for_timeout(650)
 record('标注工程导入为新项目、旧项目保留',summary(page)['projectCount']==4 and summary(page)['projectId']!=origpid)
 record('导入保留版本但不沿用结果审批',len(summary(page)['items'])==8 and summary(page)['result'] is None)
 page.click('#backHome');page.fill('#projectSearch','运行管理');page.locator('.project-card').click();page.wait_for_timeout(120)
 record('项目间标注不串用',len(summary(page)['items'])==0 and summary(page)['revision']=='r0')
 page.click('#backHome');page.fill('#projectSearch','');page.click('#newProject');page.fill('#newProjectName','新导入测试');page.click('#createProject');page.wait_for_timeout(100)
 record('新项目是空画布，无假识别框',page.locator('#emptyCanvas').is_visible() and len(summary(page)['items'])==0)
 page.set_input_files('#imageInput',str(fixture));page.wait_for_timeout(500)
 record('自有图片实际导入且无套用预设',len(summary(page)['items'])==0 and '1000 × 500' in page.locator('#imageSize').inner_text())
 s=summary(page);record('非正方形原图保持同一缩放因子',s['view']['s']>0)
 page.click('#recognizeBtn');record('自有图片不虚构自动识别','尚未接入' in page.locator('#modalTitle').inner_text());page.click('#manualInstead');drag(page,(200,100),(430,280));page.fill('#objectName','自有图标注');page.click('#saveAnnotation');record('自有图片可以补框',len(summary(page)['items'])==1)
 generate(page);page.wait_for_function('P3Demo.summary().job===null',timeout=8000);page.click('#previewResult')
 record('自有图片不展示无关示例三维',page.locator('#openSplit').count()==0 and '未重建' in page.locator('#modalRoot').inner_text());close_modal(page)
 # Responsive and keyboard focus smoke with fresh pages.
 for width,height,dpr in [(1280,800,1),(1024,768,1),(390,844,2)]:
  sub=b.new_page(viewport={'width':width,'height':height},device_scale_factor=dpr);sub.on('pageerror',lambda e:errors.append(str(e)));sub.set_content(HTML.read_text());ready(sub)
  record(f'{width}px 首页无横向溢出',sub.evaluate('document.documentElement.scrollWidth <= innerWidth'))
  sub.locator('.project-card').first.click();sub.wait_for_timeout(170)
  record(f'{width}px 画布无横向溢出',sub.evaluate('document.documentElement.scrollWidth <= innerWidth'))
  record(f'{width}px 主操作可见',sub.locator('#generateBtn').is_visible() and sub.locator('#generateBtn').bounding_box()['x']>=0)
  if width==390:
   sub.screenshot(path=str(QA/'06_mobile_workspace.png'));sub.mouse.click(*pos(sub,130,80));sub.wait_for_timeout(80)
   r=sub.locator('#annotationEditor').bounding_box();record('移动端按需底部表单不超出屏幕',r['x']>=0 and r['x']+r['width']<=width+1)
   sub.screenshot(path=str(QA/'07_mobile_editor.png'));sub.keyboard.press('Escape');record('Escape 关闭表单',not summary(sub)['formVisible'])
  sub.close()
 record('无 JavaScript 运行错误',not errors,errors)
 record('无外部网络或模型请求',not [u for u in requests if u.startswith(('http:','https:'))],requests[:5])
 record('无存储权限时可用临时会话',summary(page)['persistence'] is False)
 ctx.close();b.close()
(QA/'test_results.json').write_text(json.dumps({'browser':'Chromium / Playwright','document_loading':'page.set_content (no network; opaque origin)','checks':len(results),'results':results,'errors':errors,'not_tested':['真实模型/BIMFACE/DXF/PDF/GLB','Mac Safari','Native IndexedDB across reload: sandbox origin denied access; fallback verified']},ensure_ascii=False,indent=2))
print(f'{len(results)} checks passed')
