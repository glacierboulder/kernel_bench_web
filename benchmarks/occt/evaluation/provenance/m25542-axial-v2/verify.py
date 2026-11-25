"""Verify frozen inputs, both outcome readers, control calibration, and the paired comparison."""
import hashlib
import json
import math
import re
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parents[2]
ROLES = ('B', 'F', 'round1', 'round2', 'round3')


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    archive = HERE / 'evidence.tar.gz'
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert all(m.isfile() for m in members) and len(members) == len({m.name for m in members})
        files = {m.name: tar.extractfile(m).read() for m in members}
    manifest = json.loads(files.pop('evidence-files.json'))
    assert {k: sha(v) for k, v in files.items()} == manifest

    def data(path):
        return json.loads(files[path])

    suite = data('final/benchmark-snapshot/suite.json')
    v1_path = BUNDLE / 'evaluation/suites/new/occt-25542/1.json'
    v1 = json.loads(v1_path.read_bytes())
    assert suite == json.loads(v1_path.with_name('2.json').read_bytes())
    assert suite['checkpoints'][:4] == v1['checkpoints']
    material = data('final-material-verification.json')
    freeze = data('freeze.json')
    assert material['executed_snapshot'] == freeze['snapshot_sha256']
    for key, value in material['files'].items():
        assert sha((BUNDLE / key).read_bytes()) == value
    spec, axial, gate = [data(f'{name}.json') for name in ('protocol', 'axial', 'gate')]
    assert gate['protocol_sha256'] == manifest['protocol.json']
    assert gate['axial_plan_sha256'] == manifest['axial.json']
    for name, digest in gate['tool_hashes'].items():
        assert manifest['tools/' + name] == digest

    def scored(label, pose, rep=1):
        path = f'jobs/{label}/{pose}/{rep}'
        row = data(path + '/score.json')
        assert (row['label'], row['pose'], row['repeat']) == (label, pose, rep)
        assert row['sha256'] == manifest[path + '/result.brep']
        target = axial['cases'].get(pose, spec['gold'])
        points = target['inside'] + target['outside']
        for operand in ('first', 'second', 'result'):
            lines = files[f'{path}/{operand}.log'].decode().splitlines()
            shape = [list(map(int, s.split()[1:])) for s in lines if s.startswith('SHAPE ')]
            probes = [list(map(int, s.split()[1:])) for s in lines if s.startswith('POINTS ')]
            assert len(shape) == len(probes) == 1 and probes[0][0] == points
            valid, solids, shells, _, closed = shape[0]
            if operand != 'result':
                assert valid and solids == 1 and shells and closed and probes[0] == [points, 0, 0]
                continue
            samples = [list(map(float, s.split()[1:])) for s in lines if s.startswith('MASS ')]
            assert [r[0] for r in samples] == [1e-7, 1e-10]
            observed = row['geometry']
            assert probes[0] == observed['witnesses']
            outcomes = {'points': 'FAIL' if probes[0][1] else 'INCONCLUSIVE' if probes[0][2] else 'PASS',
                        'topology': 'PASS' if valid and solids == 1 and shells and closed else 'FAIL'}
            for i, name in enumerate(('volume', 'area'), 1):
                error = samples[1][i] - target['fine'][name]
                drift = abs(samples[0][i] - samples[1][i])
                limit = spec['criteria'][name+'_absolute']
                assert math.isfinite(error) and math.isfinite(drift)
                assert error == observed['error'][name] and drift == observed['drift'][name]
                outcomes[name] = ('FAIL' if abs(error) > limit+2*drift else
                                  'INCONCLUSIVE' if abs(error)+2*drift > limit else 'PASS')
            assert outcomes == observed['checks']
            state = 'FAIL' if 'FAIL' in outcomes.values() else 'INCONCLUSIVE' if 'INCONCLUSIVE' in outcomes.values() else 'PASS'
            assert state == observed['status']
        assert b'GENERATION_COMPLETE' in files[path+'/produce.log'].splitlines()
        draw = files[path+'/draw.log'].decode()
        rejected = re.findall(r'^BENCH_ASSERT_FAIL (\w+)', draw, re.M)
        assert 'TEST_DONE assertions=5 numeric_assertions=3' in draw and rejected == row['failed_draw']
        assert row['status'] == ('FAIL' if rejected else state)

        return row

    poses = {c['id']: next(p for p, v in gate['qualified'].items() if v['role'] == c['category'])
             for c in suite['checkpoints'][4:]}
    roles = {}
    for role in ROLES:
        checks = {}
        record = {}
        if role in spec['rounds']:
            receipt = data(f'builds/{role}/receipt.json')
            assert receipt['patch'] == spec['rounds'][role]['sha256'] == manifest[f'patches/{role}.diff']
            assert receipt['build_exit'] == 0 and receipt['base'] == spec['baseline']
            record.update(patch_sha256=receipt['patch'], build_exit=0)
        for c in suite['checkpoints']:
            key = c['id']
            entry = f'registered/{role}/{key}.json'
            out = data(entry)
            obs = out['result']
            assert obs['oracle_ran'] and obs['checkpoint_id'] == key and not obs['timed_out']
            assert obs['case_sha256'] == material['files'][c['case']]
            raw = obs['raw_result']
            assert raw['summary_pair_valid'] and raw['completion_sentinel_count'] == 1
            assert not any(raw[k] for k in ('missing_assertions', 'unexpected_assertions', 'duplicate_assertions'))
            status = {'passed': 'PASS', 'failed': 'FAIL'}[out['status']]
            assert {'geometry_pass': 'PASS', 'geometry_fail': 'FAIL'}[obs['status']] == status
            checks[key] = dict(status=status, evidence=entry, sha256=manifest[entry],
                               failed_assertions=[e['id'] for e in raw['observed_assertion_events'] if e['status']=='FAIL'])
            if key in poses:
                measured = scored(role, poses[key])
                assert measured['status'] == status
                checks[key].update(independent=measured)
            elif role in spec['rounds']:
                assert spec['rounds'][role]['v1']['checks'][key]['passed'] == (status == 'PASS')
        record.update(checks=checks, passed=sum(r['status']=='PASS' for r in checks.values()))
        roles[role] = record
    bad = [k for k, x in roles['B']['checks'].items() if x['status']=='FAIL']
    healthy = [k for k in roles['B']['checks'] if k not in bad]
    for role in spec['rounds']:
        v = roles[role]
        v['restored'] = [k for k in bad if v['checks'][k]['status']=='PASS']
        v['regressions'] = [k for k in healthy if v['checks'][k]['status']=='FAIL']
        v['status'] = ('REG_FAIL' if v['regressions'] else 'PASS*' if len(v['restored'])==len(bad)
                       else 'PARTIAL' if v['restored'] else 'NO_FIX')

    controls = {}
    for p, case in gate['qualified'].items():
        for role, expected in [('B', case['baseline_status']), ('F', 'PASS')]:
            a, b = scored(role, p), scored(role, p, 2)
            assert a['sha256'] == b['sha256'] and a['status'] == b['status'] == expected
        controls[p] = {}
        for mode in ('gold','empty','cone','shifted'):
            control = data(f'registered-controls/{p}/{mode}/receipt.json')
            external = scored(mode,p)
            assert control['shape']==external['sha256'] and control['status']==external['status']
            assert control['status']==('PASS' if mode=='gold' else 'FAIL')
            controls[p][mode] = control

    def screened(labels, names):
        return {p:{k:dict(status=scored(k,p)['status'], error=scored(k,p)['geometry']['error'])
                   for k in labels} for p in names}

    other_file = HERE.parent/'m28195-rotations-v2/qualification.json'
    other = json.loads(other_file.read_bytes())
    assert other['baseline']['commit'] == spec['baseline']
    paired = {k:{'M25542_L2':roles[k]['status'],'M28195_L3':other['roles'][k]['status']}
              for k in spec['rounds']}
    result = dict(suite=suite['id'], version=suite['version'], base=spec['baseline'], reference=spec['reference'],
                  model=spec['model'], hard_cap_seconds=spec['budget_seconds'], model_runs_added=0,
                  endpoints='Final snapshots only', api='independent API contract unmeasured',
                  frozen_snapshot=freeze['snapshot_sha256'], suite_sha256=sha(v1_path.with_name('2.json').read_bytes()),
                  unchanged_v1_sha256=sha(v1_path.read_bytes()), evidence_sha256=sha(archive.read_bytes()),
                  reference_M28195_sha256=sha(other_file.read_bytes()), baseline_failures=bad, baseline_healthy=healthy,
                  selected=gate['qualified'], analytic_targets={k:axial['cases'][k] for k in poses.values()},
                  rigid_screen=screened(['B',*spec['reference_order']],spec['pose_order']),
                  axial_screen=screened(['B','F'],axial['order']), roles=roles, controls=controls, paired=paired)
    (HERE/'qualification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(len(files),'verified evidence files;', [(r, roles[r]['passed']) for r in ROLES], paired)


if __name__=='__main__':
    main()
