from copy import deepcopy
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
import pytest
from shapely.geometry import Polygon
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from plan_tools import read_json, validate, frame, prepare, guides, render_floor, polygon_mask
from comfy_client import local_url, build_workflow
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def job(): return read_json(ROOT/'examples/rectangle_job.json')

def test_valid_demo(job): assert validate(job)['passed']
def test_missing_floor(): assert not validate({'floors':[]})['passed']
def test_overlap(job):
    job['floors'][0]['rooms'][7]['polygon'][1][0]=30
    job['floors'][0]['rooms'][7]['polygon'][2][0]=30
    assert any('overlap' in x for x in validate(job)['errors'])
def test_room_outside(job):
    job['floors'][0]['rooms'][0]['polygon'][0][0]=-5
    assert any('outside' in x for x in validate(job)['errors'])
def test_core_shift(job):
    for p in job['floors'][1]['rooms'][0]['polygon']: p[0]+=.2
    assert any('core geometry' in x for x in validate(job)['errors'])
def test_duplicate_ids(job):
    job['floors'][0]['rooms'][1]['id']='STA'
    assert not validate(job)['passed']
def test_required_function_missing(job):
    job['floors'][0]['required_categories'].append('nonexistent')
    assert any('Missing required' in x for x in validate(job)['errors'])
def test_disconnected_room(job):
    job['floors'][0]['doors']=[d for d in job['floors'][0]['doors'] if 'S1' not in d['connects']]
    assert any('No topological' in x for x in validate(job)['errors'])
def test_wrong_door(job):
    job['floors'][0]['doors'][0]['segment']=[[1,1],[3,1]]
    assert any('shared boundary' in x for x in validate(job)['errors'])
def test_same_outline_locked(job):
    job['floors'][2]['outline'][1][0]=101
    job['floors'][2]['outline'][2][0]=101
    assert any('Outline changed' in x for x in validate(job)['errors'])
def test_stair_core_required(job):
    del job['floors'][0]['rooms'][0]['core_id']
    assert any('requires a core_id' in x for x in validate(job)['errors'])
def test_label_anchor_inside(job):
    job['floors'][0]['rooms'][0]['label_at']=[500,500]
    assert any('Label anchor' in x for x in validate(job)['errors'])
def test_common_transform(job):
    f,s=frame(job,768,512); a=f((0,0)); b=f((100,54))
    assert abs((b[0]-a[0])/(b[1]-a[1])-100/54)<.02

def test_prepare_blue_crop(tmp_path):
    result=prepare(ROOT/'examples/source_crops/02.png',tmp_path, size=256)
    assert result['status']=='awaiting_outline_review'
    assert (tmp_path/'mask.png').exists()
    assert len(result['outline']['outer'])>=6

def test_prepare_reject_multiple(tmp_path):
    img=Image.new('RGB',(200,100),'white'); d=ImageDraw.Draw(img)
    d.rectangle((10,10,70,80),fill=(160,205,235));d.rectangle((120,10,180,80),fill=(160,205,235))
    img.save(tmp_path/'input.png')
    with pytest.raises(ValueError,match='Multiple'): prepare(tmp_path/'input.png',tmp_path/'out')

def test_prepare_preserve_hole(tmp_path):
    img=Image.new('L',(100,100),0); d=ImageDraw.Draw(img)
    d.rectangle((10,10,90,90),fill=255); d.rectangle((35,35,65,65),fill=0)
    img.save(tmp_path/'input.png')
    result=prepare(tmp_path/'input.png',tmp_path/'out',mode='white-mask',size=256)
    assert len(result['outline']['holes'])==1

def test_guide_dimensions(job,tmp_path):
    guides(job,tmp_path,256,256)
    assert Image.open(tmp_path/'floor_1_guide.png').size==(256,256)
    assert len(list(tmp_path.glob('*_guide.png')))==3

def test_ai_pixels_cannot_modify_stair(job):
    f=job['floors'][0]; plain=render_floor(job,f,(256,256))
    enhanced=render_floor(job,f,(256,256),generated=Image.new('RGB',(256,256),'red'))
    t,_=frame(job,256,256); stair=Polygon(f['rooms'][0]['polygon']).buffer(-1)
    mask=np.asarray(polygon_mask(stair,(256,256),t))>0
    assert np.array_equal(np.asarray(plain)[mask],np.asarray(enhanced)[mask])

def test_ai_pixels_outside_outline_unchanged(job):
    f=job['floors'][0]; plain=render_floor(job,f,(256,256))
    enhanced=render_floor(job,f,(256,256),generated=Image.new('RGB',(256,256),'red'))
    t,_=frame(job,256,256); mask=np.asarray(polygon_mask(Polygon(f['outline']),(256,256),t))==0
    assert np.array_equal(np.asarray(plain)[mask],np.asarray(enhanced)[mask])

def test_localhost_only():
    assert local_url('http://127.0.0.1:8188/')=='http://127.0.0.1:8188'
    with pytest.raises(ValueError): local_url('https://example.com')

def test_workflow_connections():
    w=build_workflow('sd15.safetensors','canny.safetensors','g.png','c.png','p','n',42)
    assert w['7']['class_type']=='ControlNetApplyAdvanced'
    assert w['9']['inputs']['positive']==['7',0]
    assert w['11']['inputs']['images']==['10',0]

def test_invalid_sampler_options():
    with pytest.raises(ValueError): build_workflow('a','b','c','d','p','n',42,denoise=1.5)
