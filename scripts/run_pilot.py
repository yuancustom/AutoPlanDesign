#!/usr/bin/env python3
"""Run one L-shaped three-floor pilot; geometry, API dry-run, and real local rendering are distinct."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import platform
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from plan_tools import require_valid, read_json, write_json, guides, compose
from l_shape_case import SOURCE, ROOT, make_case
from pilot_tools import audit_source, write_preview
from comfy_client import run_batch


def run(out: Path, mode='geometry', size=(512,512), config=None, ack=False, font=None, job_path: Path | None = None) -> dict:
    if mode not in {'geometry','dry-run','render'}: raise ValueError('Unknown run mode')
    if mode=='render' and not ack: raise ValueError('Real render requires --ack-concept-only')
    if out.exists() and any(out.iterdir()): raise ValueError('Use a new empty output directory; stale output is not reused')
    if any(type(x) is not int or x%64 or not 128<=x<=1024 for x in size):
        raise ValueError('Pilot canvas must be 128..1024 and divisible by 64')
    out.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    report={'case':'02_l_shape_pilot','mode':mode,'status':'started',
            'created_utc':datetime.now(timezone.utc).isoformat(),
            'environment':{'platform':platform.system(),'machine':platform.machine(),'python':platform.python_version()},
            'model_execution_tested':False,'all_floors_rendered':False,
            'review':{'outline_user_review':'pending','visual_review':'pending','engineering_review':'not_performed'},
            'remote_repository_updated':False}
    try:
        job=make_case(out)
        if job_path is not None:
            job=read_json(job_path)
            if len(job.get('floors',[]))!=3:
                raise ValueError('This pilot requires exactly three floors')
            write_json(out/'job.json',job)
        qa=require_valid(job); write_json(out/'geometry_qa.json',qa)
        extraction=read_json(out/'outline/outline.json')
        audit=audit_source(job,extraction,SOURCE,out/'outline/mask.png'); write_json(out/'source_audit.json',audit)
        if not audit['passed']: raise ValueError('Source polygon fidelity below pilot threshold')
        guides(job,out/'guides',*size)
        compose(job,out/'board_geometry.png',font_path=font,size=size)
        write_preview(job,out,size,audit,font)
        report.update(status='geometry_passed',geometry_passed=True,source_binding_passed=True,
                      canvas=list(size),floor_count=len(job['floors']))
        write_json(out/'run_report.json',report)
        if mode != 'geometry':
            execution=run_batch(out/'guides',out/('workflows' if mode=='dry-run' else 'generated'),
                                config or read_json(ROOT/'configs/comfy_sd15.json'),dry_run=mode=='dry-run')
            report['model_execution_tested']=execution['model_execution_tested']
            report['all_floors_rendered']=execution['all_floors_rendered']
            report['status']='workflow_dry_run_passed' if mode=='dry-run' else 'locally_rendered_unreviewed'
            if mode=='render':
                compose(job,out/'board_model_unreviewed.png',renders=out/'generated',font_path=font,size=size)
        return report
    except Exception as exc:
        report['status']='blocked'; report['error']=f'{type(exc).__name__}: {exc}'
        execution_path=out/'generated/execution.json'
        if execution_path.exists():
            execution=read_json(execution_path)
            report['model_execution_tested']=execution.get('model_execution_tested',False)
            report['all_floors_rendered']=execution.get('all_floors_rendered',False)
        raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        report['tool_versions']={k:importlib.metadata.version(k) for k in ['Pillow','numpy','shapely','requests','pytest']}
        write_json(out/'run_report.json',report)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['geometry','dry-run','render'],default='geometry')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--width',type=int,default=512); p.add_argument('--height',type=int,default=512)
    p.add_argument('--config',type=Path,default=ROOT/'configs/comfy_sd15.json')
    p.add_argument('--ack-concept-only',action='store_true'); p.add_argument('--font')
    p.add_argument('--job',type=Path,help='Use an edited L-shape job; source binding and geometry are rechecked')
    a=p.parse_args()
    try:
        report=run(a.out,a.mode,(a.width,a.height),read_json(a.config),a.ack_concept_only,a.font,a.job)
        print(json.dumps(report,ensure_ascii=False,indent=2)); return 0
    except Exception as exc:
        print(f'BLOCKED: {exc}',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
