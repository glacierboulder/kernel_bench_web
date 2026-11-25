"""Verify archive, registered assets and checks, then reconstruct the six-case matrix."""
from hashlib import sha256
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
ARCHIVE=HERE/'raw-evidence.tar.gz'
BUNDLE=HERE.parents[2]
ISSUES=('25237','28366')


def recompute():
    with tarfile.open(ARCHIVE) as t:
        files={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
    def read(key):return json.loads(files[key])
    def digest(key):return sha256(files[key]).hexdigest()
    hashes=read('file-hashes.json')
    assert set(hashes)==set(files)-{'file-hashes.json'}
    assert all(digest(k)==h for k,h in hashes.items())
    for k,h in read('evidence/seal.json').items():
        assert digest(k)==h
        if k.startswith('evaluation/'):
            assert sha256((BUNDLE/k).read_bytes()).hexdigest()==h
    identity=read('evidence/identity.json')
    output={}
    for n in ISSUES:
        assert identity['references'][n]['patch']==digest(f'reference/{n}.patch')
        suite=read(f'evaluation/suites/occt-{n}-suite/2.json')
        ids=[c['id'] for c in suite['checkpoints']]
        result={}
        for name in ('B','F','trial1','trial2'):
            root=f'evidence/{n}/{name}'
            native=read(root+'/native.json')
            run=read(root+'/outcomes.json')
            status={}
            for cp in suite['checkpoints']:
                key=cp['id']
                v=native[key]
                assert v['compile']['return_code']==0 and not v['result']['timed_out']
                code=v['result']['return_code']
                assert code in (0,1)
                passed=code==0 and all(marker in v['result']['output_tail']
                                        for marker in cp['runner_options']['stdout_contains'])
                assert passed==v['passed']
                status[key]=passed
            for role,key in zip(('defect','healthy'),ids[4:]):
                entries=run['extended'][key]
                assert len(entries)==(2 if name in ('B','F') else 1)
                for i,e in enumerate(entries,1):
                    folder=f'{root}/{role}{i}'
                    for s,h in e['shapes'].items(): assert digest(folder+'/'+s)==h
                    passed=e['producer']==0 and all(rc==0 for rc in e['reader'].values())
                    assert passed==status[key] and all(rc in (0,1) for rc in e['reader'].values())
                    if name=='F':
                        log=files[folder+'/controls.log'].decode()
                        controls=('half','adjacent','chord') if n=='25237' else ('empty','same_area_in_plane','wrong_plane')
                        assert all(c in log for c in controls)
                if len(entries)==2:
                    assert entries[0]['producer']==entries[1]['producer']
                    assert entries[0]['reader']==entries[1]['reader']
            assert status==run['status']
            if name.startswith('trial'):
                loc=f'patches/{n}/{name}'
                build=read(root+'/build.json')
                assert digest(loc+'/patch.diff')==build['patch_sha256']==read(loc+'/capture.json')['sha256']
                assert build['commit']==read(loc+'/prepared.json')['source_commit']==identity['warm_artifacts']['commit']
                assert read(loc+'/prepared.json')['tree']==identity['warm_artifacts']['tree']
                assert read(loc+'/prepared.json')['suite_sha256']==digest(f'evaluation/suites/occt-{n}-suite/1.json')
                assert build['apply']==build['build']==0
                old=read(loc+'/v1.json')['checks']
                assert {k:status[k] for k in ids[:4]}=={k:v['passed'] for k,v in old.items()}
                legacy=read(root+'/legacy-geometry.json')
                assert len(legacy)==3
                for k,v in zip(ids[:3],legacy):
                    status[k]=status[k] and v['status']=='PASS' and v['exit']==0
                failed=[k for k,v in result['B']['checks'].items() if not v]
                healthy=[k for k,v in result['B']['checks'].items() if v]
                recovered=sum(status[k] for k in failed)
                broken=sum(not status[k] for k in healthy)
                result[name]=dict(patch_sha256=build['patch_sha256'],apply='PASS',build='PASS',
                     checks=status,passed=sum(status.values()),total=len(ids),recovery=[recovered,len(failed)],
                     broken=[broken,len(healthy)],api=None,verdict='REG_FAIL' if broken else
                     ('PASS*' if recovered==len(failed) else 'PARTIAL' if recovered else 'NO_FIX'))
            else:
                assert list(status.values())==([False,False,False,True,False,True] if name=='B' else [True]*6)
                result[name]=dict(checks=status,passed=sum(status.values()),total=len(ids))
        output[n]=result
    return dict(archive_sha256=sha256(ARCHIVE.read_bytes()).hexdigest(),source=identity['warm_artifacts']['commit'],
                model='gpt-6.2-sol',effort='high',hard_cap_seconds=600,checkpoint='final',new_model_runs=0,
                api_coverage='not measured',suite_version='2',issues=output)


if __name__=='__main__':
    import sys
    matrix=recompute()
    if sys.argv[1:]==['--write']:
        (HERE/'qualification.json').write_text(json.dumps(matrix,indent=2)+'\n')
    else:
        assert matrix==json.loads((HERE/'qualification.json').read_text())
        for n,r in matrix['issues'].items():
            print(n, {k:v.get('verdict',v['passed']) for k,v in r.items()})
