"""Freeze a common OCCT adapter with suite-specific, immutable oracle contracts."""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

from .catalog import resolve_relative

RUNTIME = Path(__file__).with_name('runtime')

def configuration(root: Path, suite: dict, *, case_root: Path | None = None) -> dict | None:
    """Existing suites use a migration registry; new suites need only data."""
    path=root/'evaluation/runtime.json'
    if path.is_file():
        value=json.loads(path.read_text())
        if value.get('schema_version')!=1: raise ValueError('unsupported OCCT runtime manifest')
        key=f"{suite['id']}@{suite['version']}"
        if key in value['suites']: return value['suites'][key]
    cps=suite.get('checkpoints',[])
    if not cps or not all(cp['runner']=='draw_case_v1' and cp.get('runner_options',{}).get('expected_assertion_ids') for cp in cps):
        return None
    if len(suite['source_ids'])!=1 or len(suite['group_ids'])!=1:
        raise ValueError('standard OCCT suites must select one source and group')
    source_id=suite['source_ids'][0]
    source=next(s for s in json.loads((root/'sources.lock.json').read_text())['sources'] if s['source_id']==source_id)
    tc=json.loads(resolve_relative(root,f"toolchains/{source['toolchain']}.json").read_text())
    flags=tc.get('optimization_flags','-O3 -DNDEBUG' if tc['compiler_output_directory']=='clang-o3' else '-O0 -DNDEBUG')
    config={'schema_version':1,'suite':f"{suite['id']}@{suite['version']}",'group_id':suite['group_ids'][0],
            'source_id':source_id,'standard_build':True,
            'public_build_profile':{'compiler_output_directory':tc['compiler_output_directory'],'optimization_flags':flags},
            'build_helper':{'path':'unified_runtime/public_build.py','sha256':hashlib.sha256((RUNTIME/'public_build.py').read_bytes()).hexdigest()},
            'checkpoints':{}}
    for cp in cps:
        options=cp['runner_options']
        # During a frozen install paths are already normalized by the framework.
        material=resolve_relative(case_root or root,cp['case'])
        config['checkpoints'][cp['id']]={'checkpoint_id':cp['id'],'case':cp['case'],'category':cp['category'],
            'case_sha256':hashlib.sha256(material.read_bytes()).hexdigest(),
            'expected_assertion_ids':options['expected_assertion_ids'],'expected_failure_lines':options.get('expected_failure_lines',[]),
            'engine':{'kind':'assertions','path':'unified_runtime/draw_base.py','sha256':hashlib.sha256((RUNTIME/'public_draw.py').read_bytes()).hexdigest()}}
    return config

def enabled(root: Path, suite: dict) -> bool:
    return configuration(root,suite) is not None


def install(root: Path, suite: dict, supervisor: Path, *, assets_root: Path | None = None,
            case_root: Path | None = None, build_target: Path | None = None,
            draw_target: Path | None = None) -> dict | None:
    config=configuration(root,suite,case_root=case_root or supervisor/'cases/bundle')
    if config is None: return None
    assets_root=assets_root or supervisor/'evaluator_assets'
    case_root=case_root or supervisor/'cases/bundle'
    build_target=build_target or supervisor/'legacy/run_eval.py'
    draw_target=draw_target or supervisor/'legacy/scripts/run_draw_case.py'
    if config.get('standard_build'):
        dst=assets_root/'unified_runtime';dst.mkdir(parents=True,exist_ok=True)
        shutil.copy2(RUNTIME/'public_build.py',dst/'public_build.py')
        shutil.copy2(RUNTIME/'public_draw.py',dst/'draw_base.py')
        (dst/'build-profile.json').write_text(json.dumps(config['public_build_profile']))
    # Every suite receives the same Tcl initialization/standard DRAW runtime.
    dst=assets_root/'unified_runtime';dst.mkdir(parents=True,exist_ok=True)
    shutil.copy2(RUNTIME/'public_draw.py',dst/'draw_base.py')
    for cp in config['checkpoints'].values():
        if cp['engine']['kind']=='assertions':
            cp['engine']={'kind':'assertions','path':'unified_runtime/draw_base.py',
                          'sha256':hashlib.sha256((RUNTIME/'public_draw.py').read_bytes()).hexdigest()}
    expected={c['id'] for c in suite['checkpoints']}
    if set(config['checkpoints'])!=expected: raise ValueError('runtime must cover the exact selected suite')
    for cp in suite['checkpoints']:
        route=config['checkpoints'][cp['id']]
        if route['case']!=cp['case'] or route['category']!=cp['category']:
            raise ValueError('runtime checkpoint route differs from frozen suite')
        path=resolve_relative(case_root,cp['case'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=route['case_sha256']:
            raise ValueError('runtime checkpoint hash differs from suite material')
    if config.get('suite')!=f"{suite['id']}@{suite['version']}" or config.get('group_id') not in suite.get('group_ids',[]):
        raise ValueError('runtime suite/group identity mismatch')
    assets=assets_root
    for route in [config['build_helper'], *(cp['engine'] for cp in config['checkpoints'].values())]:
        path=resolve_relative(assets,route['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=route['sha256']:
            raise ValueError('runtime asset hash mismatch before freeze')
    # Store the exact suite contract next to trusted evaluator assets. Historical
    # snapshots remain self-contained; later framework edits cannot alter them.
    dst=assets_root/'unified_runtime'
    dst.mkdir(parents=True,exist_ok=True)
    (dst/'contract.json').write_text(json.dumps(config,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    shutil.copy2(RUNTIME/'occt_adapter.py',draw_target)
    shutil.copy2(RUNTIME/'occt_adapter.py',build_target)
    shutil.copy2(RUNTIME/'assertion_oracle.py',dst/'assertion_oracle.py')
    return config
