"""Import catalog versions and, when configured, legacy public task manifests."""
import hashlib
import json
from pathlib import Path
from .register import register
from .proto_config import BENCHMARK_ROOT, PROTO

def import_legacy_tasks(proto_root):
    """Read only fixed task.json files; never scan private/ or source trees."""
    source=Path(proto_root)/'tasks'
    imported=0
    for folder, kind, title in [
        ('task_single', 'single', '单问题修复'),
        ('task_group', 'group', '问题组联合修复'),
        ('task_active', 'active', '问题组与主动搜索'),
        ('task_group_visible3', 'group', '三题全公开问题组'),
        ('task_group_visible4', 'group', '三题全公开扫掠/圆角问题组'),
        ('task_group_visible5', 'group', '三题全公开几何稳健性问题组'),
        ('task_group_visible5all', 'group', '五题全公开问题组'),
    ]:
        manifest = source / folder / 'task.json'
        if not manifest.is_file():
            continue
        raw = manifest.read_bytes()
        value = json.loads(raw)
        register(dict(id=value['task_id'], version='proto-1', title='OCCT Boolean · ' + title,
                      kind=kind, base_commit=value['base_commit'],
                      issues=[dict(id='occt-' + str(n), title='OCCT issue #' + str(n), visibility='public') for n in value['visible_issues']],
                      budget=dict(scope='group', wall_clock_minutes=value['budget']['wall_clock_minutes']),
                      has_hidden_checks=value.get('has_hidden_checks', kind != 'single'), execution_mode='joint', tags=['OCCT', 'Boolean', '原型'],
                      source_hash=hashlib.sha256(raw).hexdigest(),
                      required_output=list(value['required_output']),
                      description='同一源码基线，单次会话共享工作区，提交统一补丁。隐藏检查内容不进入公开目录。',
                      discovery_quality_scored=False))
        imported += 1
    return imported


if (BENCHMARK_ROOT / 'catalog.json').is_file():
    from .catalog import import_public_tasks
    imported, counts = import_public_tasks(BENCHMARK_ROOT)
    legacy_imported=0
    if PROTO.resolve()!=BENCHMARK_ROOT.resolve() and (PROTO/'tasks').is_dir():
        legacy_imported=import_legacy_tasks(PROTO)
    print(f"已校验题库并导入 {imported} 个 catalog 版本；issue={counts['issues']}，suite={counts['evaluation_suites']}；兼容导入旧版本 {legacy_imported} 个")
else:
    legacy_imported=import_legacy_tasks(PROTO)
    print(f'已导入 {legacy_imported} 个旧版公开题目版本')
