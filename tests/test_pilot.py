"""L-shape regression and API-contract tests. FakeSession is NOT a model."""
from __future__ import annotations
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import json
import sys
import requests
import numpy as np
from PIL import Image
import pytest
from shapely.geometry import box
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import comfy_client as client
from plan_tools import read_json, validate, guides, poly, render_floor, polygon_mask, frame
from l_shape_case import SOURCE, make_case
from pilot_tools import audit_source
from run_pilot import run

@pytest.fixture
def case(tmp_path):
    root=tmp_path/'case'; job=make_case(root)
    return root,job


def test_l_shape_case_geometry(case):
    root,job=case
    assert validate(job)['passed']
    assert [len(f['rooms']) for f in job['floors']]==[10,10,10]
    assert len({tuple(r['label'] for r in f['rooms']) for f in job['floors']})==3


def test_source_trace_and_notch(case):
    root,job=case
    report=audit_source(job,read_json(root/'outline/outline.json'),SOURCE,root/'outline/mask.png')
    assert report['passed']
    assert report['raster_to_polygon_iou']>=.995
    assert all(f['allocated_fraction']==1 for f in report['floors'])
    assert all(f['notch_intrusion_area']==0 for f in report['floors'])
    assert report['generated_image_outline_iou'] is None


def test_replacing_l_by_box_is_rejected(case):
    root,job=case
    p=poly(job['floors'][0]['outline'])
    job['floors'][0]['outline']={'outer':list(box(*p.bounds).exterior.coords),'holes':[]}
    with pytest.raises(ValueError,match='source outline was changed'):
        audit_source(job,read_json(root/'outline/outline.json'),SOURCE,root/'outline/mask.png')


def test_source_hash_mismatch_rejected(case):
    root,job=case; job['source']['sha256']='0'*64
    with pytest.raises(ValueError,match='hash mismatch'):
        audit_source(job,read_json(root/'outline/outline.json'),SOURCE,root/'outline/mask.png')


def test_contiguous_floor_numbers_required(case):
    _,job=case; job['floors'].pop(1)
    assert not validate(job)['passed']


def test_missing_level_is_reported_without_crashing(case):
    _,job=case; del job['floors'][1]['level']
    assert not validate(job)['passed']


def test_boolean_level_is_not_a_floor_number(case):
    _,job=case;job['floors'][0]['level']=True
    assert not validate(job)['passed']


def test_cannot_allow_ai_on_core(case):
    _,job=case;job['floors'][0]['rooms'][0]['allow_ai_surface']=True
    assert any('Protected' in e for e in validate(job)['errors'])


def test_renderer_protects_core_even_if_flag_is_wrong(case):
    _,job=case; f=job['floors'][0];f['rooms'][0]['allow_ai_surface']=True
    plain=render_floor(job,f,(256,256))
    generated=render_floor(job,f,(256,256),generated=Image.new('RGB',(256,256),'red'))
    t,_=frame(job,256,256)
    mask=np.asarray(polygon_mask(poly(f['rooms'][0]['polygon']).buffer(-1),(256,256),t))>0
    assert np.array_equal(np.asarray(plain)[mask],np.asarray(generated)[mask])


def test_core_alignment_regression(case):
    _,job=case
    for v in job['floors'][2]['rooms'][0]['polygon']:v[0]+=.1
    assert any('core geometry' in e for e in validate(job)['errors'])


def test_pilot_geometry_mode_never_loads_model(tmp_path,monkeypatch):
    import run_pilot
    monkeypatch.setattr(run_pilot,'run_batch',lambda *a,**kw:pytest.fail('Model unexpectedly called'))
    out=tmp_path/'run';report=run(out)
    assert report['status']=='geometry_passed'
    assert not report['model_execution_tested']
    assert (out/'preview.html').exists() and (out/'board_geometry.png').exists()
    assert len(list(out.glob('floor_*_geometry.svg')))==3
    assert not (out/'generated').exists()


def test_dry_run_no_http(case,tmp_path,monkeypatch):
    _,job=case; folder=tmp_path/'guides';guides(job,folder,256,256)
    monkeypatch.setattr(client.LocalSession,'request',lambda *a,**kw:pytest.fail('Network in dry run'))
    result=client.run_batch(folder,tmp_path/'dry',read_json(client.ROOT/'configs/comfy_sd15.json'),True)
    assert not result['model_execution_tested'] and not result['all_floors_rendered']
    assert len(result['floors'])==3
    assert not list((tmp_path/'dry').glob('floor_[123].png'))


def test_guide_tamper_stops_before_http(case,tmp_path,monkeypatch):
    _,job=case;folder=tmp_path/'guides';guides(job,folder,256,256)
    Image.new('RGB',(256,256),'white').save(folder/'floor_1_guide.png')
    monkeypatch.setattr(client.LocalSession,'request',lambda *a,**kw:pytest.fail('Unexpected HTTP'))
    with pytest.raises(ValueError,match='hash mismatch'):
        client.run_batch(folder,tmp_path/'bad',read_json(client.ROOT/'configs/comfy_sd15.json'))
    assert read_json(tmp_path/'bad/execution.json')['status']=='failed'


def test_snapshot_tamper_rejected(case,tmp_path):
    _,job=case; folder=tmp_path/'guides'; guides(job,folder,256,256)
    snapshot=read_json(folder/'job.snapshot.json'); snapshot['name']='changed'
    (folder/'job.snapshot.json').write_text(json.dumps(snapshot))
    with pytest.raises(ValueError,match='snapshot hash'):client.validate_guides(folder)


def test_refuse_stale_output(tmp_path):
    folder=tmp_path/'old';folder.mkdir();(folder/'keep.txt').write_text('keep')
    with pytest.raises(ValueError,match='empty output'):run(folder)
    assert (folder/'keep.txt').read_text()=='keep'


def test_render_requires_concept_ack(tmp_path):
    with pytest.raises(ValueError,match='ack-concept-only'):run(tmp_path/'r',mode='render')
    assert not (tmp_path/'r').exists()


def test_model_failure_persisted_not_success(case,tmp_path,monkeypatch):
    _,job=case; folder=tmp_path/'guides'; guides(job,folder,256,256)
    def failed(*a,**kw):raise requests.ConnectionError('deliberately unavailable in test')
    monkeypatch.setattr(client,'check_server',failed)
    with pytest.raises(requests.ConnectionError):
        client.run_batch(folder,tmp_path/'result',read_json(client.ROOT/'configs/comfy_sd15.json'))
    report=read_json(tmp_path/'result/execution.json')
    assert report['status']=='failed' and not report['model_execution_tested']
    assert not list((tmp_path/'result').glob('floor_[123].png'))


def test_redirect_to_external_provider_rejected(monkeypatch):
    response=requests.Response();response.status_code=302;response.headers['Location']='https://example.com'
    def fake(*args,**kwargs):
        assert kwargs['allow_redirects'] is False
        return response
    monkeypatch.setattr(requests.Session,'request',fake)
    with client.LocalSession() as session:
        assert session.trust_env is False
        with pytest.raises(RuntimeError,match='redirect refused'):session.get('http://127.0.0.1:8188/prompt')


@pytest.mark.parametrize('seed,steps,cfg',[(True,24,6),(-1,24,6),(42,2.5,6),(42,24,float('nan')),(42,24,float('inf'))])
def test_bad_sampler_fails(seed,steps,cfg):
    with pytest.raises(ValueError):client.build_workflow('a','b','g','c','p','n',seed,steps=steps,cfg=cfg)


class FakeResponse:
    def __init__(self,data=None,content=b''):
        self._data=data;self.content=content;self.ok=True;self.status_code=200;self.text=''
    def json(self):return self._data
    def raise_for_status(self):pass


class FakeSession:
    """Synthetic transport response, not a diffusion engine."""
    def __init__(self):self.prompts=0;self.uploads=0
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def get(self,url,**kwargs):
        if url.endswith('/object_info'):
            info={node:{} for node in client.NODES}
            info['CheckpointLoaderSimple']={'input':{'required':{'ckpt_name':[['test_sd15']]}}}
            info['ControlNetLoader']={'input':{'required':{'control_net_name':[['test_canny']]}}}
            return FakeResponse(info)
        if url.endswith('/system_stats'):return FakeResponse({'test_transport':True})
        if '/history/' in url:
            pid=url.rsplit('/',1)[1]
            return FakeResponse({pid:{'status':{'completed':True,'status_str':'success'},
                'outputs':{'11':{'images':[{'filename':'synthetic.png','subfolder':'','type':'output'}]}}}})
        if url.endswith('/view'):
            b=BytesIO();Image.new('RGB',(256,256),'white').save(b,format='PNG');return FakeResponse(content=b.getvalue())
        raise AssertionError(url)
    def post(self,url,**kwargs):
        if url.endswith('/upload/image'):
            self.uploads+=1;return FakeResponse({'name':f'input{self.uploads}.png'})
        if url.endswith('/prompt'):
            self.prompts+=1;return FakeResponse({'prompt_id':f'mocked-prompt-{self.prompts}'})
        raise AssertionError(url)


def test_three_floor_transport_contract_mock_only(case,tmp_path,monkeypatch):
    _,job=case;folder=tmp_path/'guides';guides(job,folder,256,256)
    fake=FakeSession();monkeypatch.setattr(client,'LocalSession',lambda:fake)
    result=client.run_batch(folder,tmp_path/'mock_only',{'checkpoint':'test_sd15','controlnet':'test_canny'})
    assert fake.prompts==3 and fake.uploads==6
    assert len(result['floors'])==3 and result['visual_review']=='pending'
    assert all(f['prompt_id'].startswith('mocked-') for f in result['floors'])
    assert result['status']=='rendered_unreviewed' # Protocol branch only, no actual model performance evidence.


def test_edited_job_is_actually_used(case,tmp_path):
    root,job=case
    job['floors'][0]['rooms'][1]['label']='修改后的办公室'
    path=tmp_path/'edited.json';path.write_text(json.dumps(job,ensure_ascii=False))
    out=tmp_path/'edited-run'
    run(out,job_path=path)
    assert read_json(out/'job.json')['floors'][0]['rooms'][1]['label']=='修改后的办公室'
