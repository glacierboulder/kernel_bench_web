"""Merge v4 tasks and generate data contracts for the common framework adapter.

Preserves original scripts, thresholds, source locks and historical snapshots.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil
import sys
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--v4',type=Path,required=True);a=p.parse_args();root=a.bundle;v4=a.v4
 # Idempotent merge: no overwrite on conflicts. Manifests retain identity.
 for src in v4.rglob('*'):
  if not src.is_file():continue
  rel=src.relative_to(v4)
  if rel.as_posix() in {'catalog.json','sources.lock.json','README.md'}:continue
  dst=root/rel
  if dst.exists():
   if sha(dst)!=sha(src):raise ValueError('merge conflict '+str(rel))
  else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 cat=json.loads((root/'catalog.json').read_text());new=json.loads((v4/'catalog.json').read_text())
 for kind in ('issues','groups','evaluation_suites'):
  known={(r['id'],r['version']):r for r in cat[kind]}
  for row in new[kind]:
   k=(row['id'],row['version'])
   if k in known and row!=known[k]:raise ValueError('identity conflict '+str(k))
   if k not in known:cat[kind].append(row)
 write(root/'catalog.json',cat)
 old=json.loads((root/'sources.lock.json').read_text());new=json.loads((v4/'sources.lock.json').read_text())
 for row in new['sources']:
  found=next((r for r in old['sources'] if r['source_id']==row['source_id']),None)
  if found and found!=row:raise ValueError('source conflict')
  if not found:old['sources'].append(row)
 write(root/'sources.lock.json',old)
 assets=root/'evaluation/cases/evaluator_assets';lock=json.loads((assets/'five_group_execution/dispatch_lock.json').read_text());vl=json.loads((assets/'occt_single_v4/dispatch_lock.json').read_text())
 configs={}
 for ref in cat['groups']:
  g=json.loads((root/ref['path']).read_text());sr=g['evaluation_suite'];sk=f"{sr['id']}@{sr['version']}"
  origin=lock['suite_routes'].get(sk)
  is_v4=g['id'].startswith('occt-boolean-intersection-v4-mantis-')
  if not origin and not is_v4:continue
  se=next(r for r in cat['evaluation_suites'] if r['id']==sr['id'] and r['version']==sr['version']);suite=json.loads((root/se['path']).read_text())
  if is_v4:
   source=next(s for s in old['sources'] if s['source_id']==g['source_id']);tc=json.loads((root/'toolchains'/f"{source['toolchain']}.json").read_text())
   helper=root/tc['evaluator_directory']/'run_eval.py'
   # Retain the selected historical build implementation as a source profile,
   # but dispatch every suite through the same framework build interface.
   hp=assets/'unified_runtime'/(tc['id']+'-build.py');hp.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(helper,hp)
   build={'path':hp.relative_to(assets).as_posix(),'sha256':sha(hp)}
  else:build=lock['helper_routes'][origin['origin']]
  config={'schema_version':1,'suite':sk,'group_id':g['id'],'source_id':g['source_id'],'build_helper':build,'checkpoints':{}}
  source=next(s for s in old['sources'] if s['source_id']==g['source_id'])
  tc=json.loads((root/'toolchains'/f"{source['toolchain']}.json").read_text())
  optimization='-O3 -DNDEBUG' if (origin and origin['origin']=='part1') or tc['compiler_output_directory']=='clang-o3' else '-O0 -DNDEBUG'
  config['public_build_profile']={'compiler_output_directory':tc['compiler_output_directory'],'optimization_flags':optimization}
  if origin:config['geometry_helper']=lock['g3_geometry_oracle']
  for cp in suite['checkpoints']:
   case=cp['case'];original_case=case
   if case.startswith('issues/'):
    parts=Path(case).parts
    ir=next(r for r in cat['issues'] if str(Path(r['path']).parent)==str(Path(*parts[:3])))
    case=Path('issues',ir['id'],ir['version'],*parts[3:]).as_posix()
   route={'checkpoint_id':cp['id'],'case':case,'case_sha256':sha(root/original_case),'category':cp['category']}
   if is_v4:
    vr=vl['checkpoint_routes'][case]
    if vr['case_sha256']!=route['case_sha256']:raise ValueError('v4 hash differs')
    route.update(expected_assertion_ids=vr['expected_assertion_ids'],expected_failure_lines=vr.get('expected_failure_lines',[]))
    route['engine']={'kind':'assertions','path':'occt_single_v4/draw_case_v1_base.py','sha256':vl['base_runner_sha256']}
   else:
    cr=lock['checkpoint_routes'][case];route['engine']={'kind':'legacy',**lock['runner_routes'][cr['origin']]}
    if cr['origin']=='g3':route['engine']['role']='agent'
   config['checkpoints'][cp['id']]=route
  configs[sk]=config
 if len(configs)!=15:raise ValueError(f'expected 15 suites, got {len(configs)}')
 write(root/'evaluation/runtime.json',{'schema_version':1,'suites':configs})
 print(json.dumps({'suites':len(configs),'checkpoints':sum(len(c['checkpoints']) for c in configs.values())}))
if __name__=='__main__':main()
