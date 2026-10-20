"""Organize existing terminal runs without rewriting their original provenance."""
import copy
import json
import secrets
import sqlite3
from .app import DATA,db,now,rows

GROUPS=[('occt_boolean_group_visible_544_506_847','544 / 506 / 847','visible3'),('occt_boolean_group_visible_690_693_172','690 / 693 / 172','visible4'),('occt_boolean_group_visible_370_872_1452','370 / 872 / 1452','visible5')]

def organize():
    marker='three-joint-groups-history-v1'
    existing=[e for e in rows('experiments') if e.get('organization_tag')==marker]
    if existing:return existing
    run_list=rows('runs');before=rows('experiments')
    directory=DATA/'backups'/('group-plan1a-'+now().replace(':','-'));directory.mkdir(parents=True,mode=0o700)
    with db() as c,sqlite3.connect(directory/'bench.sqlite3') as backup:c.backup(backup)
    created=[]
    for task_id,label,suite in GROUPS:
        members=sorted([r for r in run_list if r['task']['id']==task_id],key=lambda r:r['created_at'])
        if not members or any(r['status'] in ('queued','preparing','running','collecting','evaluating') for r in members):raise ValueError('Expected existing terminal runs for '+task_id)
        representative=next((r for r in reversed(members) if r.get('plan1a_protocol')),members[-1])
        config=representative.get('plan1a_protocol',{})
        valid=[r for r in members if not r.get('exclude_from_agent_score')]
        item=dict(id=secrets.token_hex(8),created_at=now(),title='Plan 1A · 三 issue 联合修复 · '+label,phase='1A',
            retrospective=True,organization_tag=marker,asset_policy='independent_group',evaluation_suites=[suite],
            member_run_ids=[r['id'] for r in members],source_experiment_ids=sorted({r['experiment_id'] for r in members if r.get('experiment_id')}),
            task_snapshots=[copy.deepcopy(representative['task'])],agent=copy.deepcopy(representative['agent']),
            repeats=len(valid),request_limit=representative.get('cumulative_request_limit'),wall_seconds=config.get('wall_seconds',1800),
            max_output_tokens=representative.get('provenance',{}).get('per_request_max_output_tokens'),baseline=representative['task']['base_commit'],knowledge=None,
            prompt_version='historical-per-run',submission_version='historical-per-run',input_policy='Historical grouping only; actual protocol and budgets remain in each original run.',
            evaluator_sha256=config.get('evaluator_sha256'),gate={'repeat_success_per_group':1,'combined_regression_required':False,'limitations':'Success of one joint patch is sufficient; no cross-group combination.'},
            run_protocols=[{'run_id':r['id'],'original_experiment_id':r.get('experiment_id'),'original_attempt':r.get('attempt'),'request_limit':r.get('cumulative_request_limit'),'protocol':r.get('plan1a_protocol'),'excluded':bool(r.get('exclude_from_agent_score'))} for r in members])
        created.append(item)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        # Refuse to regroup if another operator has changed the source records.
        for run in run_list:
            stored=json.loads(c.execute('SELECT payload FROM runs WHERE id=?',(run['id'],)).fetchone()['payload'])
            if stored!=run:raise ValueError('Runs changed during organization')
        for item in created:c.execute('INSERT INTO experiments VALUES (?,?)',(item['id'],json.dumps(item,ensure_ascii=False)))
        replaced=set(x for item in created for x in item['source_experiment_ids'])
        for old in before:
            if old['id'] in replaced:
                old.update(archived_at=now(),superseded_by=[e['id'] for e in created if old['id'] in e['source_experiment_ids']],archive_reason='按三 issue 问题组拆分展示；原始运行和评测归属保留。')
                c.execute('UPDATE experiments SET payload=? WHERE id=?',(json.dumps(old,ensure_ascii=False),old['id']))
    (directory/'organization.json').write_text(json.dumps(created,ensure_ascii=False,indent=2))
    return created

if __name__=='__main__':
    from .study import summary
    print(json.dumps([{'id':e['id'],'title':e['title'],'runs':e['member_run_ids'],'groups':summary(e)['groups']} for e in organize()],ensure_ascii=False,indent=2))
