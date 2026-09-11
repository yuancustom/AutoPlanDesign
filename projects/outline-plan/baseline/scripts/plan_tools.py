#!/usr/bin/env python3
"""Local concept-plan utilities. Not an automatic architectural design solver."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def poly(value: Any) -> Polygon:
    if isinstance(value, dict):
        result = Polygon(value['outer'], value.get('holes', []))
    else:
        result = Polygon(value)
    if result.is_empty or not result.is_valid or result.area <= 0:
        raise ValueError('Invalid, empty, self-intersecting or zero-area polygon')
    if not all(math.isfinite(x) for x in result.bounds):
        raise ValueError('Polygon coordinates must be finite')
    return result


def frame(job: dict, width: int, height: int, margin: int = 28):
    """One common transform for ALL floors; never auto-fit each floor separately."""
    if width <= 2 * margin or height <= 2 * margin:
        raise ValueError('Canvas too small')
    extent = unary_union([poly(f['outline']) for f in job['floors']]).bounds
    x0, y0, x1, y1 = extent
    scale = min((width-2*margin)/(x1-x0), (height-2*margin)/(y1-y0))
    dx = (width-(x1-x0)*scale)/2-x0*scale
    dy = (height-(y1-y0)*scale)/2-y0*scale
    return lambda p: (round(p[0]*scale+dx), round(p[1]*scale+dy)), scale


def polygon_mask(p: Polygon, size: tuple[int, int], transform) -> Image.Image:
    out = Image.new('L', size, 0); d = ImageDraw.Draw(out)
    d.polygon([transform(v) for v in p.exterior.coords], fill=255)
    for hole in p.interiors:
        d.polygon([transform(v) for v in hole.coords], fill=0)
    return out


def validate(job: dict) -> dict:
    errors, warnings = [], []
    floors = job.get('floors', [])
    if not floors:
        return {'passed': False, 'errors': ['No floors'], 'warnings': []}
    if job.get('units') != 'diagram_units':
        warnings.append('This tool checks relative geometry only, not real-world dimensions or code compliance.')
    levels = [f.get('level') for f in floors]
    if any(type(v) is not int for v in levels) or levels != list(range(1, len(floors)+1)):
        return {'passed': False, 'errors': ['Floor levels must be consecutive integers starting at 1'], 'warnings': []}
    all_cores = []; previous_outline = None
    for floor in floors:
        tag = f"{floor['level']}F"
        try:
            outline = poly(floor['outline'])
            rooms = floor.get('rooms', [])
            ids = [r['id'] for r in rooms]
            if not rooms or len(ids) != len(set(ids)) or 'outside' in ids:
                errors.append(f'{tag}: Missing rooms or duplicate/reserved room IDs'); continue
            shapes = {r['id']: poly(r['polygon']) for r in rooms}
            area_eps = max(1e-7, outline.area * 1e-7)
            length_eps = max(1e-7, math.sqrt(outline.area) * 1e-7)
            if previous_outline is not None:
                if job.get('footprint_policy', 'same') == 'same' and not outline.equals(previous_outline):
                    errors.append(f'{tag}: Outline changed despite same-footprint policy')
                if not job.get('allow_cantilever', False) and outline.difference(previous_outline).area > area_eps:
                    errors.append(f'{tag}: Upper floor extends beyond floor below; no cantilever approval')
            previous_outline = outline
            for room in rooms:
                p = shapes[room['id']]
                if room.get('allow_ai_surface') and (room.get('core_id') or room.get('category') in {'stairs','wc_m','wc_f','corridor','shaft'}):
                    errors.append(f"{tag}/{room['id']}: Protected core/circulation cannot allow AI repaint")
                if p.difference(outline).area > area_eps:
                    errors.append(f"{tag}/{room['id']}: Room outside outline or inside a hole")
                if not room.get('label'):
                    errors.append(f"{tag}/{room['id']}: Missing label")
                if 'label_at' in room:
                    from shapely.geometry import Point
                    if not p.contains(Point(room['label_at'])):
                        errors.append(f"{tag}/{room['id']}: Label anchor outside room")
                for item in room.get('equipment', []):
                    q = poly(item['polygon'])
                    if not p.covers(q):
                        errors.append(f"{tag}/{room['id']}: Equipment outside room")
            for i, a in enumerate(ids):
                for b in ids[i+1:]:
                    if shapes[a].intersection(shapes[b]).area > area_eps:
                        errors.append(f'{tag}: Rooms overlap: {a}, {b}')
            unused = outline.difference(unary_union(list(shapes.values()))).area / outline.area
            if unused > 0.02:
                warnings.append(f'{tag}: {unused:.1%} area unallocated; review walls/reserve/circulation')
            categories = {r.get('category') for r in rooms}
            for needed in floor.get('required_categories', []):
                if needed not in categories:
                    errors.append(f'{tag}: Missing required category {needed}')
            cores = {}
            for r in rooms:
                if r.get('core_id'):
                    if r['core_id'] in cores:
                        errors.append(f'{tag}: Duplicate core_id {r["core_id"]}')
                    cores[r['core_id']] = (shapes[r['id']], r.get('category'))
                elif r.get('category') == 'stairs':
                    errors.append(f'{tag}/{r["id"]}: Stair room requires a core_id')
            all_cores.append((floor['level'], cores))
            stair_ids = {r['id'] for r in rooms if r.get('category') == 'stairs'}
            if not stair_ids:
                errors.append(f'{tag}: No stair room')
            graph = {x: set() for x in ids + ['outside']}
            for door in floor.get('doors', []):
                a, b = door['connects']; seg = LineString(door['segment'])
                if a not in graph or b not in graph or a == b or seg.length <= length_eps:
                    errors.append(f'{tag}: Invalid door endpoints/segment'); continue
                if 'outside' in (a, b):
                    if floor['level'] != 1:
                        errors.append(f'{tag}: Exterior access on upper floor unsupported by this schema'); continue
                    other = b if a == 'outside' else a
                    shared = outline.boundary.intersection(shapes[other].boundary)
                else:
                    shared = shapes[a].boundary.intersection(shapes[b].boundary)
                if not shared.buffer(length_eps).covers(seg):
                    errors.append(f'{tag}: Door not on shared boundary: {a}, {b}'); continue
                graph[a].add(b); graph[b].add(a)
            start = {'outside'} if floor['level'] == 1 else stair_ids
            reachable, pending = set(start), list(start)
            while pending:
                n = pending.pop()
                for neighbor in graph[n] - reachable:
                    reachable.add(neighbor); pending.append(neighbor)
            for rid in ids:
                if rid not in reachable:
                    errors.append(f'{tag}/{rid}: No topological connection to entry/stair')
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f'{tag}: {exc}')
    if all_cores:
        base = all_cores[0][1]
        for core_level, cores in all_cores[1:]:
            if set(base) != set(cores):
                errors.append(f"{core_level}F: Vertical core IDs differ")
            for key in set(base) & set(cores):
                if not base[key][0].equals(cores[key][0]) or base[key][1] != cores[key][1]:
                    errors.append(f"{core_level}F/{key}: Vertical core geometry/category changed")
    return {
        'passed': not errors, 'errors': errors, 'warnings': warnings,
        'scope': 'Polygon containment/overlap, declared requirements, shared-boundary doors, room graph and core footprints only',
        'not_checked': ['Building codes', 'Structural loads', 'Stair flights/landings/headroom',
                        'Real egress travel distances or widths', 'Door swing clearance',
                        'Equipment service clearances', 'MEP design', 'Generated-image semantics'],
    }


def require_valid(job: dict):
    report = validate(job)
    if not report['passed']:
        raise ValueError('Geometry validation failed:\n' + '\n'.join(report['errors']))
    return report


def prepare(path: Path, out: Path, mode: str = 'blue', box=None, size: int = 768) -> dict:
    """Extract a selected, filled shape. Not OCR; not a vector-perfect SVG reconstruction."""
    if not 128 <= size <= 4096:
        raise ValueError('Size must be 128..4096')
    img = Image.open(path).convert('RGB')
    if box:
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= img.width and 0 <= y0 < y1 <= img.height):
            raise ValueError('Crop outside source image')
        img = img.crop(tuple(box))
    rgb = np.asarray(img).astype(np.int16)
    if mode == 'blue':
        select = ((rgb[:,:,2]-rgb[:,:,0]) > 20) & ((rgb[:,:,1]-rgb[:,:,0]) > 10) & (rgb[:,:,0] > 60)
    elif mode == 'black-fill':
        select = rgb.mean(axis=2) < 90
    elif mode == 'white-mask':
        select = rgb.mean(axis=2) > 127
    else:
        raise ValueError('Unsupported extraction mode')
    mask = select.astype(np.uint8)*255
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    areas = sorted([(int(stats[i,cv2.CC_STAT_AREA]), i) for i in range(1,count)], reverse=True)
    if not areas or areas[0][0] < 64:
        raise ValueError('No clear filled shape found. Supply a tight crop or explicit binary mask.')
    if len(areas)>1 and areas[1][0] > areas[0][0]*0.08:
        raise ValueError('Multiple large shapes found. Crop ONE building before extraction.')
    mask = (labels == areas[0][1]).astype(np.uint8)*255
    y, x = np.where(mask > 0); bbox = (int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1))
    tight = Image.fromarray(mask).crop(bbox)
    available = size-64
    factor = min(available/tight.width, available/tight.height)
    resized = tight.resize((round(tight.width*factor),round(tight.height*factor)), Image.Resampling.NEAREST)
    normalized = Image.new('L',(size,size),0)
    offset = ((size-resized.width)//2,(size-resized.height)//2)
    normalized.paste(resized,offset)
    normalized_array = np.asarray(normalized)
    contours,hierarchy = cv2.findContours(normalized_array,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    roots = [i for i,h in enumerate(hierarchy[0]) if h[3] == -1]
    root = max(roots,key=lambda i:cv2.contourArea(contours[i]))
    contour_points = lambda i: contours[i].reshape(-1,2).astype(float).tolist()
    rings = {'outer':contour_points(root), 'holes':[contour_points(i) for i,h in enumerate(hierarchy[0]) if h[3]==root]}
    p = poly(rings)
    out.mkdir(parents=True,exist_ok=True)
    img.save(out/'source_crop.png'); normalized.save(out/'mask.png')
    edge = cv2.Canny(normalized_array,100,200)
    Image.fromarray(edge).save(out/'control_canny.png')
    outline = Image.new('RGB',(size,size),'white')
    outline.paste((12,26,39),(0,0,size,size),Image.fromarray(edge))
    outline.save(out/'outline.png')
    paths = []
    for ring in [p.exterior,*p.interiors]:
        pts = list(ring.coords)
        paths.append('M '+' L '.join(f'{a:g},{b:g}' for a,b in pts)+' Z')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}"><path d="{" ".join(paths)}" fill="white" stroke="black" fill-rule="evenodd"/></svg>'
    (out/'raster_traced_outline.svg').write_text(svg,encoding='utf-8')
    metadata = {'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'source_name':path.name,'source_crop_box':box,'shape_bbox_within_crop':bbox,
                'mode':mode,'canvas':[size,size],'outline':rings,
                'note':'Thresholded raster estimate, not original SVG geometry. Confirm corners/holes against source.',
                'status':'awaiting_outline_review'}
    write_json(out/'outline.json',metadata)
    return metadata


def load_font(size: int, requested: str | None = None):
    candidates = [requested] if requested else []
    candidates += ['/System/Library/Fonts/PingFang.ttc',
                   '/System/Library/Fonts/STHeiti Light.ttc',
                   '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                   '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for value in candidates:
        if value and Path(value).is_file():
            return ImageFont.truetype(value,size)
    raise ValueError('No font found. Supply --font pointing to an installed Chinese font. Fonts are not bundled.')


def draw_symbol(d, room: dict, transform):
    p = poly(room['polygon']); x0,y0,x1,y1 = p.bounds
    if room.get('category') == 'corridor': return
    w,h = x1-x0,y1-y0
    # User-provided equipment takes precedence over generic schematic symbols.
    if room.get('equipment'):
        for item in room['equipment']:
            q = poly(item['polygon'])
            d.polygon([transform(v) for v in q.exterior.coords], outline='#596E7B', fill='#E5ECF1',width=1)
        return
    cat = room.get('category','')
    def rectangle(xa,ya,xb,yb):
        d.rectangle([transform((xa,ya)),transform((xb,yb))],outline='#657986',width=1)
    if cat == 'stairs':
        xa,xb = x0+w*.22,x1-w*.22
        for n in range(12):
            yy = y0+h*.18+n*h*.045
            d.line([transform((xa,yy)),transform((xb,yy))],fill='#657986',width=1)
        d.line([transform((x0+w*.5,y0+h*.15)),transform((x0+w*.5,y0+h*.76))],fill='#657986',width=1)
    elif cat.startswith('wc'):
        for n in range(2):
            xa = x0+w*(.17+n*.39)
            rectangle(xa,y0+h*.14,xa+w*.23,y0+h*.43)
    elif cat in {'racks','machine','electrical','hvac','archive'}:
        for n in range(3):
            xa = x0+w*(.13+n*.27)
            rectangle(xa,y0+h*.14,xa+w*.16,y0+h*.68)
    elif cat in {'office','control','duty'}:
        for n in range(2):
            xa = x0+w*(.16+n*.42)
            rectangle(xa,y0+h*.2,xa+w*.26,y0+h*.4)
            rectangle(xa+w*.06,y0+h*.45,xa+w*.19,y0+h*.53)
    elif cat == 'meeting':
        rectangle(x0+w*.23,y0+h*.2,x1-w*.23,y0+h*.64)
        for n in range(3):
            xa = x0+w*(.25+n*.19)
            rectangle(xa,y0+h*.1,xa+w*.09,y0+h*.18)
            rectangle(xa,y0+h*.66,xa+w*.09,y0+h*.74)


def render_floor(job: dict, floor: dict, size=(768,512), labels=False,
                 font_path=None, generated: Image.Image | None = None) -> Image.Image:
    transform,scale = frame(job,*size)
    img = Image.new('RGB',size,'white'); d = ImageDraw.Draw(img)
    for room in floor['rooms']:
        p = poly(room['polygon']); mask = polygon_mask(p,size,transform)
        fill = '#EDF3F6' if room.get('category') != 'corridor' else '#FFFFFF'
        img.paste(fill,(0,0,*size),mask)
        # Model pixels can only appear inside explicitly allowed, inset room areas.
        # This does NOT validate the semantic content of those pixels.
        if (generated is not None and room.get('allow_ai_surface',False)
                and not room.get('core_id')
                and room.get('category') not in {'stairs','wc_m','wc_f','corridor','shaft'}):
            inset = p.buffer(-max(0.7,4/scale))
            if inset.geom_type == 'Polygon' and not inset.is_empty:
                img.paste(generated,(0,0),polygon_mask(inset,size,transform))
        else:
            symbols = Image.new('RGB',size,'white'); sd = ImageDraw.Draw(symbols)
            draw_symbol(sd,room,transform)
            ink = (np.asarray(symbols).min(axis=2) < 250).astype(np.uint8)*255
            ink = Image.fromarray(np.minimum(ink,np.asarray(mask)))
            img.paste(symbols,(0,0),ink)
    # Always redraw authoritative walls and door openings AFTER model compositing.
    d = ImageDraw.Draw(img)
    for room in floor['rooms']:
        p=poly(room['polygon']); d.line([transform(v) for v in p.exterior.coords],fill='#233C50',width=2)
    outline=poly(floor['outline'])
    for ring in [outline.exterior,*outline.interiors]:
        d.line([transform(v) for v in ring.coords],fill='#142B3E',width=4)
    for door in floor.get('doors',[]):
        a,b = [transform(v) for v in door['segment']]
        d.line([a,b],fill='white',width=6)
        # Door gap only; door swing is deliberately not invented.
        d.line([a,(round(a[0]+(b[0]-a[0])*.22),round(a[1]+(b[1]-a[1])*.22))],fill='#233C50',width=2)
    if labels:
        font=load_font(14,font_path)
        for room in floor['rooms']:
            p=poly(room['polygon']); anchor=room.get('label_at')
            if anchor is None:
                point=p.representative_point(); anchor=[point.x,point.y]
            x,y=transform(anchor); label=room['label']
            available_width = max(18, (p.bounds[2]-p.bounds[0])*scale-9)
            font=load_font(14,font_path)
            for font_size in range(14,8,-1):
                font=load_font(font_size,font_path)
                if d.textlength(label,font=font)<=available_width: break
            bb=d.textbbox((0,0),label,font=font); tw,th=bb[2]-bb[0],bb[3]-bb[1]
            d.rectangle((x-tw/2-3,y-th/2-4,x+tw/2+3,y+th/2+4),fill='white')
            d.text((x-tw/2,y-th/2-bb[1]),label,font=font,fill='#152D40')
    return img


def guides(job: dict, out: Path, width=768,height=512):
    report=require_valid(job)
    if width%64 or height%64: raise ValueError('Generation dimensions must be multiples of 64')
    out.mkdir(parents=True,exist_ok=True)
    write_json(out/'geometry_qa.json',report)
    write_json(out/'job.snapshot.json',job)
    for f in job['floors']:
        level=f['level']; image=render_floor(job,f,(width,height))
        image.save(out/f'floor_{level}_guide.png')
        edges=cv2.Canny(np.asarray(image.convert('L')),80,160)
        Image.fromarray(edges).save(out/f'floor_{level}_canny.png')
    write_json(out/'render_manifest.json',{'canvas':[width,height], 'levels':[f['level'] for f in job['floors']],
                                        'geometry_job_sha256':hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest(),
                                        'file_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('floor_*_*.png'))}})


def compose(job: dict, out: Path, renders: Path | None = None, font_path=None, size=(768,512)):
    require_valid(job)
    width,height=size
    margin=32; right=330; header=135; row_h=height+80
    board=Image.new('RGB',(width+right+margin*2,header+row_h*len(job['floors'])+55),'white')
    d=ImageDraw.Draw(board); title_font=load_font(27,font_path); text_font=load_font(17,font_path)
    d.text((margin,27),job.get('name','建筑多楼层功能方案'),font=title_font,fill='#122D42')
    d.text((margin,76),'概念布置图｜非施工图｜无真实尺寸与北向校准',font=text_font,fill='#657887')
    d.line((margin,112,board.width-margin,112),fill='#B7C8D4',width=1)
    for idx,f in enumerate(job['floors']):
        y=header+idx*row_h
        generated=None
        if renders:
            generated=Image.open(renders/f'floor_{f["level"]}.png').convert('RGB')
            if generated.size!=size:
                raise ValueError(f'Generated image size {generated.size} != guide {size}. Do not stretch; rerender/register explicitly.')
        floor_img=render_floor(job,f,size,True,font_path,generated)
        d.text((margin,y),f'{f["level"]}F  {f.get("title", "平面图")}',font=title_font,fill='#122D42')
        board.paste(floor_img,(margin,y+45))
        x=margin+width+24
        d.text((x,y+58),'功能分区',font=text_font,fill='#122D42')
        for n,line in enumerate(f.get('description',[])):
            # Keep short Chinese lines in the job; no model-generated paragraph rendering.
            d.text((x,y+95+n*29),line,font=text_font,fill='#526A7C')
        d.text((x,y+height-20),'轮廓 / 核心位置由几何数据控制',font=load_font(14,font_path),fill='#657887')
    label='含本地生图结果；房间内像素需人工复核' if renders else '程序绘制结构样例；尚未调用生图模型'
    d.text((margin,board.height-39),label,font=text_font,fill='#657887')
    out.parent.mkdir(parents=True,exist_ok=True); board.save(out)


def main():
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare'); p.add_argument('image',type=Path); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',choices=['blue','black-fill','white-mask'],default='blue'); p.add_argument('--box',nargs=4,type=int)
    p.add_argument('--size',type=int,default=768)
    p=sub.add_parser('validate'); p.add_argument('job',type=Path); p.add_argument('--out',type=Path)
    p=sub.add_parser('guides'); p.add_argument('job',type=Path); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--width',type=int,default=768); p.add_argument('--height',type=int,default=512)
    p=sub.add_parser('compose'); p.add_argument('job',type=Path); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--renders',type=Path); p.add_argument('--font'); p.add_argument('--width',type=int,default=768); p.add_argument('--height',type=int,default=512)
    args=ap.parse_args()
    try:
        if args.command=='prepare':
            result=prepare(args.image,args.out,args.mode,args.box,args.size)
            print(json.dumps({'status':result['status'],'out':str(args.out)},ensure_ascii=False))
        elif args.command=='validate':
            report=validate(read_json(args.job)); print(json.dumps(report,ensure_ascii=False,indent=2))
            if args.out: write_json(args.out,report)
            if not report['passed']: return 2
        elif args.command=='guides': guides(read_json(args.job),args.out,args.width,args.height)
        elif args.command=='compose': compose(read_json(args.job),args.out,args.renders,args.font,(args.width,args.height))
        return 0
    except (ValueError,OSError,KeyError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
