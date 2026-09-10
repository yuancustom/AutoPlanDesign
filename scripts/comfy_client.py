#!/usr/bin/env python3
"""Sequential localhost-only ComfyUI SD1.5/Canny client. No cloud fallback."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
import requests
from PIL import Image
from plan_tools import read_json, write_json

NODES = ['CheckpointLoaderSimple','CLIPTextEncode','LoadImage','ControlNetLoader',
         'ControlNetApplyAdvanced','VAEEncode','KSampler','VAEDecode','SaveImage']
ROOT = Path(__file__).resolve().parents[1]


def local_url(url: str) -> str:
    value = urlparse(url)
    if (value.scheme != 'http' or value.hostname not in {'127.0.0.1','localhost','::1'}
            or value.username or value.password or value.query or value.fragment
            or value.path not in {'','/'}):
        raise ValueError('Only an unauthenticated local HTTP ComfyUI root URL is allowed')
    if value.port is not None and not 1 <= value.port <= 65535:
        raise ValueError('Invalid local server port')
    return url.rstrip('/')


class LocalSession(requests.Session):
    """Do not inherit proxy settings or follow a redirect to an external provider."""
    def __init__(self):
        super().__init__()
        self.trust_env = False

    def request(self, method, url, *args, **kwargs):
        value = urlparse(url)
        if (value.scheme != 'http' or value.hostname not in {'127.0.0.1','localhost','::1'}
                or value.username or value.password):
            raise ValueError('External HTTP destination refused')
        kwargs['allow_redirects'] = False
        result = super().request(method, url, *args, **kwargs)
        if result.is_redirect or result.is_permanent_redirect:
            raise RuntimeError('HTTP redirect refused; use the actual local ComfyUI endpoint')
        return result


def build_workflow(checkpoint: str, controlnet: str, guide: str, canny: str,
                   positive: str, negative: str, seed: int, steps: int = 24,
                   cfg: float = 6.0, denoise: float = 0.4, strength: float = 1.0,
                   output_prefix: str = 'floorplan') -> dict:
    if not checkpoint or not controlnet: raise ValueError('Model filenames are required')
    if type(seed) is not int or not 0 <= seed < 2**64: raise ValueError('Invalid seed')
    if type(steps) is not int or not 1 <= steps <= 100: raise ValueError('Invalid steps')
    if not all(math.isfinite(v) for v in [cfg,denoise,strength]): raise ValueError('Non-finite parameter')
    if not (0 <= cfg <= 30 and 0 < denoise <= 1 and 0 <= strength <= 2):
        raise ValueError('Invalid sampling parameters')
    def n(name, **inputs): return {'class_type':name,'inputs':inputs}
    return {
      '1':n('CheckpointLoaderSimple',ckpt_name=checkpoint),
      '2':n('CLIPTextEncode',text=positive,clip=['1',1]),
      '3':n('CLIPTextEncode',text=negative,clip=['1',1]),
      '4':n('LoadImage',image=guide), '5':n('LoadImage',image=canny),
      '6':n('ControlNetLoader',control_net_name=controlnet),
      '7':n('ControlNetApplyAdvanced',positive=['2',0],negative=['3',0],control_net=['6',0],
            image=['5',0],strength=strength,start_percent=0.0,end_percent=1.0),
      '8':n('VAEEncode',pixels=['4',0],vae=['1',2]),
      '9':n('KSampler',model=['1',0],positive=['7',0],negative=['7',1],latent_image=['8',0],
            seed=seed,steps=steps,cfg=cfg,sampler_name='euler',scheduler='normal',denoise=denoise),
      '10':n('VAEDecode',samples=['9',0],vae=['1',2]),
      '11':n('SaveImage',images=['10',0],filename_prefix=output_prefix),
    }


def check_server(session, base, checkpoint, controlnet):
    response=session.get(base+'/object_info',timeout=10); response.raise_for_status(); info=response.json()
    missing=[x for x in NODES if x not in info]
    if missing: raise ValueError(f'ComfyUI nodes unavailable: {missing}')
    for node,field,name in [('CheckpointLoaderSimple','ckpt_name',checkpoint),
                            ('ControlNetLoader','control_net_name',controlnet)]:
        choices=info[node]['input']['required'][field][0]
        if name not in choices: raise ValueError(f'{name} not installed; available {field}: {choices}')
    return info  # Filename existence is not proof of model-family compatibility.


def upload(session,base,path: Path):
    with path.open('rb') as handle:
        response=session.post(base+'/upload/image',files={'image':(uuid.uuid4().hex+'_'+path.name,handle,'image/png')},
                              data={'type':'input','overwrite':'false'},timeout=60)
    response.raise_for_status(); data=response.json()
    return '/'.join(x for x in [data.get('subfolder',''),data['name']] if x)


def run_one(session,base,workflow,out: Path,timeout=1800):
    response=session.post(base+'/prompt',json={'prompt':workflow,'client_id':uuid.uuid4().hex},timeout=60)
    if not response.ok: raise RuntimeError(f'ComfyUI rejected workflow: {response.status_code}\n{response.text}')
    data=response.json()
    if data.get('node_errors'): raise RuntimeError(json.dumps(data['node_errors'],ensure_ascii=False))
    prompt_id=data['prompt_id']; start=time.monotonic()
    write_json(out.with_suffix('.submitted.json'),{'prompt_id':prompt_id,'workflow':workflow})
    while time.monotonic()-start < timeout:
        response=session.get(base+f'/history/{prompt_id}',timeout=30); response.raise_for_status()
        item=response.json().get(prompt_id)
        if item:
            write_json(out.with_suffix('.history.json'),item)
            status=item.get('status',{})
            if status.get('status_str')=='error': raise RuntimeError(f'ComfyUI execution failed: {prompt_id}')
            images=item.get('outputs',{}).get('11',{}).get('images',[])
            if images:
                spec=images[0]
                response=session.get(base+'/view',params={k:spec[k] for k in ['filename','subfolder','type'] if k in spec},timeout=60)
                response.raise_for_status()
                temp=out.with_suffix('.partial.png'); temp.write_bytes(response.content)
                with Image.open(temp) as image: image.verify()
                temp.replace(out)
                return prompt_id
            if status.get('completed'): raise RuntimeError('Completed workflow returned no SaveImage output')
        time.sleep(2)
    raise TimeoutError(f'Timeout for {prompt_id}; check queue before retry. No automatic retry or global interrupt.')


def validate_guides(folder: Path) -> dict:
    manifest=read_json(folder/'render_manifest.json')
    job=read_json(folder/'job.snapshot.json')
    job_hash=hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()
    if job_hash != manifest['geometry_job_sha256']: raise ValueError('Job snapshot hash mismatch')
    if manifest['levels'] != [f['level'] for f in job['floors']]: raise ValueError('Floor manifest mismatch')
    from plan_tools import require_valid
    require_valid(job)
    for level in manifest['levels']:
        for suffix in ['guide','canny']:
            path=folder/f'floor_{level}_{suffix}.png'
            expected=manifest.get('file_sha256',{}).get(path.name)
            if not expected or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise ValueError(f'Guide hash mismatch: {path.name}; regenerate guides')
            with Image.open(path) as image:
                if list(image.size)!=manifest['canvas']: raise ValueError('Guide size mismatch')
    return manifest


def run_batch(guides: Path, out: Path, config: dict, dry_run: bool = False) -> dict:
    if out.exists() and any(out.iterdir()): raise ValueError('Output directory is not empty; refuse stale results')
    out.mkdir(parents=True,exist_ok=True)
    execution={'backend':'comfyui_sd15_canny_img2img','mode':'dry-run' if dry_run else 'render',
               'model_execution_tested':False,'all_floors_rendered':False,
               'visual_review':'pending','floors':[],'config':config,
               'model_weights_sha256':None,'status':'initializing'}
    started=time.monotonic()
    try:
        if config.get('family','sd15')!='sd15': raise ValueError('Pilot backend only supports SD1.5 + matching Canny')
        base=local_url(config.get('server','http://127.0.0.1:8188'))
        manifest=validate_guides(guides)
        positive=(ROOT/'prompts/render_sd15.txt').read_text().strip()
        negative=(ROOT/'prompts/negative_sd15.txt').read_text().strip()
        # Parameter validation precedes any upload or prompt submission.
        values={k:config.get(k,default) for k,default in
                [('seed',42001),('steps',24),('cfg',6.0),('denoise',.3),('strength',.9)]}
        build_workflow(config['checkpoint'],config['controlnet'],'guide','canny',positive,negative,**values)
        execution['geometry_job_sha256']=manifest['geometry_job_sha256']
        execution['canvas']=manifest['canvas']
        with LocalSession() as session:
            if not dry_run:
                execution['status']='checking_local_server'; write_json(out/'execution.json',execution)
                check_server(session,base,config['checkpoint'],config['controlnet'])
                try:
                    response=session.get(base+'/system_stats',timeout=10); response.raise_for_status()
                    write_json(out/'server_system_stats.json',response.json())
                except (ValueError,requests.RequestException): pass
            for level in manifest['levels']:
                g=guides/f'floor_{level}_guide.png'; c=guides/f'floor_{level}_canny.png'
                guide,canny=(g.name,c.name) if dry_run else (upload(session,base,g),upload(session,base,c))
                per_floor={**values,'seed':values['seed']+level}
                workflow=build_workflow(config['checkpoint'],config['controlnet'],guide,canny,
                                        positive,negative,**per_floor,output_prefix=f'autoplandesign_{level}F')
                write_json(out/f'floor_{level}_api.json',workflow)
                if dry_run:
                    execution['floors'].append({'level':level,'status':'dry_run_only'})
                else:
                    began=time.monotonic(); output=out/f'floor_{level}.png'
                    prompt_id=run_one(session,base,workflow,output,config.get('timeout',1800))
                    with Image.open(output) as image:
                        if list(image.size)!=manifest['canvas']: raise ValueError('Output size mismatch; no automatic stretching')
                    execution['model_execution_tested']=True
                    execution['floors'].append({'level':level,'status':'rendered_unreviewed',
                        'prompt_id':prompt_id,'elapsed_including_queue_seconds':round(time.monotonic()-began,3),
                        'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
                write_json(out/'execution.json',execution)
        execution['all_floors_rendered']=not dry_run and len(execution['floors'])==len(manifest['levels'])
        execution['status']='dry_run_only' if dry_run else 'rendered_unreviewed'
        return execution
    except Exception as exc:
        execution['status']='failed'; execution['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        execution['elapsed_seconds']=round(time.monotonic()-started,3)
        write_json(out/'execution.json',execution)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--guides',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config',type=Path,default=ROOT/'configs/comfy_sd15.json')
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    result=run_batch(args.guides,args.out,read_json(args.config),args.dry_run)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,RuntimeError,TimeoutError,requests.RequestException) as exc:
        raise SystemExit(f'ERROR: {exc}')
