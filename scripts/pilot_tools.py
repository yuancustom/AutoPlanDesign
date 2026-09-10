"""Source-to-layout checks and deterministic evidence views for the L-shape pilot."""
from __future__ import annotations
import base64
import hashlib
import html
import json
from pathlib import Path
from xml.sax.saxutils import escape
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import box
from shapely.ops import unary_union
from plan_tools import poly, polygon_mask, render_floor, frame, write_json, load_font
from l_shape_case import normalized_outline, sha256


def audit_source(job: dict, extraction: dict, source: Path, mask_path: Path) -> dict:
    """Measures deterministic data fidelity; never describes these as model-image metrics."""
    reference = normalized_outline(extraction)
    if job['source']['sha256'] != sha256(source): raise ValueError('Source image hash mismatch')
    if extraction['source_sha256'] != sha256(source): raise ValueError('Extraction source hash mismatch')
    mask = np.asarray(Image.open(mask_path).convert('L')) > 0
    restored = np.asarray(polygon_mask(poly(extraction['outline']), tuple(extraction['canvas']),
                                       lambda p: (round(p[0]), round(p[1])))) > 0
    union = np.logical_or(mask, restored).sum()
    iou = float(np.logical_and(mask, restored).sum()/union)
    rows = []
    notch = box(*reference.bounds).difference(reference)
    for floor in job['floors']:
        current = poly(floor['outline'])
        delta = reference.symmetric_difference(current).area
        if delta > reference.area*1e-9: raise ValueError(f"{floor['level']}F source outline was changed")
        rooms = unary_union([poly(r['polygon']) for r in floor['rooms']])
        intrusion = rooms.intersection(notch).area
        coverage = rooms.intersection(reference).area/reference.area
        if intrusion > reference.area*1e-9: raise ValueError('A room fills the L-shaped notch')
        if coverage < .995: raise ValueError('Pilot leaves more than 0.5% unallocated')
        rows.append({'level':floor['level'], 'room_count':len(floor['rooms']),
                     'door_count':len(floor['doors']), 'allocated_fraction':round(coverage,10),
                     'outline_symmetric_difference_area':delta, 'notch_intrusion_area':intrusion,
                     'stairs':[r['core_id'] for r in floor['rooms'] if r['category']=='stairs']})
    return {'passed':iou >= .995, 'source_sha256':sha256(source),
            'metric_scope':'source raster -> extracted polygon -> layout data, NOT generated-image quality',
            'raster_to_polygon_iou':iou, 'floors':rows,
            'user_outline_approval':'pending', 'generated_image_outline_iou':None}


def floor_svg(job: dict, floor: dict, size: tuple[int,int]) -> str:
    transform, _ = frame(job,*size)
    def path(p):
        chunks=[]
        for ring in [p.exterior,*p.interiors]:
            chunks.append('M '+' L '.join(f'{x},{y}' for x,y in map(transform, ring.coords))+' Z')
        return ' '.join(chunks)
    text=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" height="{size[1]}" viewBox="0 0 {size[0]} {size[1]}">',
          '<title>Geometry-only concept layout; not an AI-generated image</title>',
          '<rect width="100%" height="100%" fill="white"/>']
    for r in floor['rooms']:
        color='#ffffff' if r['category']=='corridor' else '#edf3f6'
        text.append(f'<path d="{path(poly(r["polygon"]))}" fill="{color}" stroke="#233c50" stroke-width="2"/>')
    text.append(f'<path d="{path(poly(floor["outline"]))}" fill="none" stroke="#142b3e" stroke-width="4" fill-rule="evenodd"/>')
    for d in floor['doors']:
        (xa,ya),(xb,yb)=map(transform,d['segment'])
        text.append(f'<path d="M {xa},{ya} L {xb},{yb}" stroke="white" stroke-width="6"/>')
    for r in floor['rooms']:
        x,y=transform(r['label_at'])
        bounds=poly(r['polygon']).bounds
        available=transform((bounds[2],0))[0]-transform((bounds[0],0))[0]-8
        fontsize=min(13,max(8,available/max(1,len(r['label']))))
        text.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="PingFang SC,Noto Sans CJK SC,sans-serif" font-size="13" fill="#152d40">{escape(r["label"])}</text>')
    return '\n'.join(text+['</svg>'])


def write_preview(job: dict, out: Path, size: tuple[int,int], audit: dict, font=None) -> None:
    """Offline HTML, no external fonts/scripts, explicitly geometry only."""
    def data_uri(path): return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
    def png(path, label): return f'<figure><img src="{data_uri(path)}" alt="{html.escape(label)}"><figcaption>{html.escape(label)}</figcaption></figure>'
    panels=[]
    for f in job['floors']:
        level=f['level']; image=render_floor(job,f,size,labels=True,font_path=font)
        name=out/f'floor_{level}_geometry.png'; image.save(name)
        svg=floor_svg(job,f,size); (out/f'floor_{level}_geometry.svg').write_text(svg,encoding='utf-8')
        panels.append(f'<article><h2>{level}F · {html.escape(f["title"])}</h2>'+png(name,'程序几何预览，不是模型输出')+
                      '<p>'+'；'.join(map(html.escape,f['description']))+'</p></article>')
    doc='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AutoPlanDesign · L形三层验证</title><style>
*{box-sizing:border-box}body{font-family:system-ui,"PingFang SC",sans-serif;background:#f3f6f8;color:#193449;margin:0;padding:32px;line-height:1.65}
main{max-width:1250px;margin:auto}h1{font-size:30px;margin-bottom:4px}.notice{background:#fff4df;border-left:4px solid #bd7f20;padding:15px 20px}
.source{display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:720px}figure{margin:0;background:white;padding:14px;border-radius:12px}img{width:100%;object-fit:contain}figcaption{font-size:13px;color:#576c7a}
.plans{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:20px}article{background:white;padding:16px;border-radius:14px}article h2{font-size:18px}code{overflow-wrap:anywhere}p{font-size:15px}footer{font-size:13px;margin-top:25px}@media(max-width:850px){.plans{grid-template-columns:1fr}.source{grid-template-columns:1fr}body{padding:16px}}
</style><main><h1>AutoPlanDesign / 02 L形</h1><p>一个轮廓 · 三层不同功能 · 统一坐标与竖向核心</p>
<div class="notice"><strong>当前仅为程序几何验证。</strong>尚未完成本地模型推理、人工概念审查或工程规范审查。图中不提供真实比例尺。</div><h2>来源与轮廓提取</h2><section class="source">'''
    doc+=png(out/'outline/source_crop.png','用户总览图中的第 02 个形状')+png(out/'outline/outline.png','像素轮廓提取；不是原始 SVG 精确恢复')
    doc+='</section><section class="plans">'+''.join(panels)+'</section>'
    doc+=f'<footer>源图片 SHA-256：<code>{audit["source_sha256"]}</code><br>轮廓栅格→多边形 IoU：{audit["raster_to_polygon_iou"]:.6f}（不是生图一致性分数）。<br>楼梯 A/B 与男女卫位置跨层锁定。房间划分为明确编写的样例提案，不是自动优化排房。</footer></main></html>'
    (out/'preview.html').write_text(doc,encoding='utf-8')
    overview_board(job,out,font)


def overview_board(job: dict, out: Path, font=None):
    """Compact three-column geometry evidence, independent of model resolution."""
    board=Image.new('RGB',(1600,770),'white'); d=ImageDraw.Draw(board)
    title=load_font(32,font); subtitle=load_font(18,font); section=load_font(24,font); small=load_font(16,font)
    d.text((36,25),'AutoPlanDesign / 02 L形三层结构验证',font=title,fill='#142b3e')
    d.text((38,78),'程序几何预览 · 尚未调用生图模型 · 非施工图',font=subtitle,fill='#93632b')
    source=Image.open(out/'outline/source_crop.png').convert('RGB'); source.thumbnail((170,112))
    board.paste(source,(1400,8));d.line((36,132,1564,132),fill='#b8c9d5',width=2)
    for idx,floor in enumerate(job['floors']):
        x=36+idx*520
        d.text((x,159),f"{floor['level']}F · {floor['title']}",font=section,fill='#142b3e')
        image=render_floor(job,floor,(512,512),labels=True,font_path=font)
        board.paste(image.crop((16,64,496,448)),(x,213))
        for n,line in enumerate(floor['description']):d.text((x,620+n*26),line,font=small,fill='#526a7c')
    d.line((36,714,1564,714),fill='#b8c9d5',width=1)
    d.text((36,731),'原轮廓凹口保留｜上下层楼梯与卫生间对齐｜房间功能来自明确布局提案，不是自动排房或模型验收结果',font=small,fill='#526a7c')
    board.save(out/'overview_geometry.png')
