"""One explicit layout proposal for the user's 02 L-shape; NOT a general solver."""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
from shapely import affinity
from shapely.geometry import box
from shapely.ops import unary_union
from plan_tools import poly, prepare, write_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/source_crops/02.png'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_outline(extraction: dict):
    shape = poly(extraction['outline'])
    x0, y0, x1, _ = shape.bounds
    return affinity.scale(affinity.translate(shape, -x0, -y0),
                          xfact=100/(x1-x0), yfact=100/(x1-x0), origin=(0, 0))


def ring(shape) -> dict:
    return {'outer': [list(v) for v in list(shape.exterior.coords)[:-1]],
            'holes': [[list(v) for v in list(h.coords)[:-1]] for h in shape.interiors]}


def build_job(extraction: dict, source_hash: str) -> dict:
    """Clip each proposed room to the actual raster polygon, never replace it with a generic L."""
    shape = normalized_outline(extraction)
    max_y = shape.bounds[3]
    if not (76 < max_y < 79) or not shape.covers(box(26, 4, 33, 43)):
        raise ValueError('This preset only supports the selected 02 crop. A new outline needs a new proposal.')

    def room(rid, label, category, region, core=None):
        clipped = shape.intersection(region)
        if clipped.geom_type != 'Polygon' or clipped.is_empty or clipped.interiors:
            raise ValueError(f'{rid}: expected one simply connected room')
        point = clipped.representative_point()
        x0, y0, x1, y1 = clipped.bounds
        # Label low in a room, keeping central schematic equipment visible.
        label_at = [(x0+x1)/2, y0+(y1-y0)*.85]
        from shapely.geometry import Point
        if category == 'corridor': label_at = [48, 48]
        if not clipped.contains(Point(label_at)): label_at = [point.x, point.y]
        value = {'id': rid, 'label': label, 'category': category,
                 'polygon': ring(clipped)['outer'], 'label_at': label_at,
                 'allow_ai_surface': not core and category != 'corridor'}
        if core: value['core_id'] = core
        return value

    floors = []
    specs = [
        ('设备运行与值守', ('运行办公室', 'office'),
         [(0,24,'辅助机房','machine'), (24,46,'机柜区','racks'),
          (46,65,'配电辅助间','electrical'), (65,83,'值班室','duty')],
         ['辅助机房、机柜与配电分区', '运行办公与值班空间', '两处楼梯、卫生间跨层固定']),
        ('集中控制与技术办公', ('资料室', 'archive'),
         [(0,28,'控制室','control'), (28,55,'通信机柜区','racks'),
          (55,70,'技术办公室','office'), (70,83,'小会议室','meeting')],
         ['控制室与通信机柜分区', '技术办公、会议与资料', '公共走廊连接所有功能空间']),
        ('办公会议与支持保障', ('值班室', 'duty'),
         [(0,30,'综合办公室','office'), (30,55,'会议室','meeting'),
          (55,69,'资料室','archive'), (69,83,'设备保障间','hvac')],
         ['综合办公与会议交流', '资料与辅助设备保障', '保留原凹口，不新增悬挑']),
    ]
    for level, (title, north, bottom, description) in enumerate(specs, 1):
        corridor = unary_union([box(25,-1,34.2,52), box(-1,38,101,52)])
        rooms = [
            room('STA','楼梯 A','stairs',box(-1,-1,25,16),'STA'),
            room('NORTH',*north,box(-1,16,25,26)),
            room('WCM','男卫','wc_m',box(-1,26,12.5,38),'WCM'),
            room('WCF','女卫','wc_f',box(12.5,26,25,38),'WCF'),
            room('C','公共走廊','corridor',corridor),
            room('STB','楼梯 B','stairs',box(83,52,101,max_y+1),'STB'),
        ]
        doors = [
            {'connects':['STA','C'],'segment':[[25,7],[25,10]]},
            {'connects':['NORTH','C'],'segment':[[25,20],[25,23]]},
            {'connects':['WCM','C'],'segment':[[4,38],[7,38]]},
            {'connects':['WCF','C'],'segment':[[17,38],[20,38]]},
            {'connects':['STB','C'],'segment':[[90,52],[93,52]]},
        ]
        for i, (xa,xb,label,category) in enumerate(bottom, 1):
            rid=f'B{i}'
            rooms.append(room(rid,label,category,box(xa if xa else -1,52,xb,max_y+1)))
            center=(xa+xb)/2
            doors.append({'connects':[rid,'C'],'segment':[[center-1.5,52],[center+1.5,52]]})
        if level == 1:
            doors += [
                {'connects':['C','outside'],'segment':[[100,46],[100,49]]},
                {'connects':['STA','outside'],'segment':[[0,7],[0,10]]},
                {'connects':['STB','outside'],'segment':[[100,63],[100,66]]},
            ]
        floors.append({'level':level,'title':title,'description':description,
                       'outline':ring(shape), 'rooms':rooms, 'doors':doors,
                       'required_categories':['stairs','wc_m','wc_f','corridor','office'] +
                         (['machine','racks','electrical','duty'] if level == 1 else
                          ['control','racks','meeting','archive'] if level == 2 else
                          ['meeting','archive','hvac'])})
    return {'schema_version':'1.0','id':'02_l_shape_pilot',
            'name':'02 L形｜发电厂辅助用房三层概念布置',
            'units':'diagram_units','footprint_policy':'same','allow_cantilever':False,
            'source':{'image':'examples/source_crops/02.png','sha256':source_hash,
                      'extraction_mode':'blue','extraction_canvas':512,
                      'transform':'translate bbox minimum to origin; uniform scale so width = 100',
                      'outline_review':'agent_checked_user_review_pending'},
            'assumptions':['用户仅提供一个轮廓，三层采用相同边界。',
                           '房间由显式 L 形样例规则提出；不是自动排房模型的输出。',
                           '无真实尺寸；双楼梯数量是演示配置，不是消防合规结论。',
                           '机房按辅助设备用房演示，非主发电机组工艺设计。'],
            'review_status':'proposal_not_user_approved','floors':floors}


def make_case(output: Path) -> dict:
    extraction = prepare(SOURCE, output/'outline', mode='blue', size=512)
    job = build_job(extraction, sha256(SOURCE))
    write_json(output/'job.json', job)
    return job


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() and any(a.out.iterdir()): p.error('Use a new output directory')
    make_case(a.out)
