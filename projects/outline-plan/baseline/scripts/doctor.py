#!/usr/bin/env python3
"""Read-only environment/model-service check; never install, submit jobs, or change Mac settings."""
import argparse, importlib.util, json, platform, sys
from pathlib import Path
from comfy_client import LocalSession, local_url, check_server
from plan_tools import read_json, write_json
ROOT=Path(__file__).resolve().parents[1]

def inspect(config):
    result={'platform':platform.system(),'machine':platform.machine(),'python':platform.python_version(),
            'target_is_apple_silicon':platform.system()=='Darwin' and platform.machine()=='arm64',
            'mps_available':False,'cuda_available':False,'torch_installed':False,
            'local_service_available':False,'model_inference_performed':False}
    if importlib.util.find_spec('torch'):
        import torch
        result.update(torch_installed=True,torch_version=torch.__version__,
                      mps_available=torch.backends.mps.is_available(),cuda_available=torch.cuda.is_available())
    try:
        with LocalSession() as session:
            check_server(session,local_url(config['server']),config['checkpoint'],config['controlnet'])
        result['local_service_available']=True
    except Exception as exc: result['service_error']=f'{type(exc).__name__}: {exc}'
    result['note']='Checks this process host only. It does not inspect another Mac or prove model-family compatibility.'
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=ROOT/'configs/comfy_sd15.json');p.add_argument('--out',type=Path)
    a=p.parse_args();data=inspect(read_json(a.config))
    if a.out:write_json(a.out,data)
    print(json.dumps(data,ensure_ascii=False,indent=2))
    sys.exit(0 if data['local_service_available'] else 2)
