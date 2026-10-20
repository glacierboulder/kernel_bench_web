"""Validate the merged OCCT group's frozen paths and locked dispatcher routes."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import importlib.util, json, sys, tempfile
from pathlib import Path
from backend.catalog import public_task, validate_bundle
from backend.evaluator import _prepare_control
from backend.freeze import freeze_catalog_task, verify_snapshot
from backend.settings import SETTINGS

bundle = validate_bundle(SETTINGS.benchmark_root)
catalog = json.loads((SETTINGS.benchmark_root / 'catalog.json').read_text(encoding='utf-8'))
new_refs = [item for item in catalog['groups'] if item['path'].startswith('groups/new/')]
assert len(new_refs) == 5, len(new_refs)
route_total = 0
for ref in new_refs:
    group = bundle['groups'][(ref['id'], ref['version'])]
    task = public_task(bundle, group)
    with tempfile.TemporaryDirectory(prefix='occt-freeze-') as temporary:
        run_root = Path(temporary)
        manifest = freeze_catalog_task(task, run_root)
        snapshot = run_root / 'benchmark-snapshot'
        verify_snapshot(snapshot)
        suite = json.loads((snapshot / 'suite.json').read_text(encoding='utf-8'))
        control, source_dir = _prepare_control(run_root, None, [suite], group['kind'],
                                              group['source_id'], snapshot)
        assert source_dir == SETTINGS.cache_dir / 'sources' / group['source_id'] / 'source'
        case_root = control / 'cases' / 'bundle'
        lock_path = control / 'private' / 'evaluator_assets' / 'five_group_execution' / 'dispatch_lock.json'
        lock = json.loads(lock_path.read_text(encoding='utf-8'))
        suite_key = f"{suite['id']}@{suite['version']}"
        assert lock['suite_routes'][suite_key]['group_id'] == group['id']
        adapter_path = control / 'scripts' / 'run_draw_case.py'
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec = importlib.util.spec_from_file_location('occt_runtime_dispatch_' + group['id'].replace('-', '_'), adapter_path)
            adapter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(adapter)
            count = 0
            for checkpoint in suite['checkpoints']:
                case = checkpoint['case']
                route = lock['checkpoint_routes'].get(case)
                assert route is not None, (group['id'], checkpoint['id'], case)
                assert route['checkpoint_id'] == checkpoint['id'], (group['id'], checkpoint['id'], route)
                assert route['group_id'] == group['id'], (group['id'], checkpoint['id'], route)
                assert route['suite'] == suite_key, (group['id'], checkpoint['id'], route)
                target = case_root / case
                assert target.is_file(), (group['id'], case)
                origin, selected_runner = adapter._runner_for_case(str(target.parent), target.name)
                assert origin == route['origin'], (group['id'], case, origin, route)
                assert selected_runner.is_file(), selected_runner
                count += 1
            assert count == len(suite['checkpoints'])
            route_total += count
        finally:
            sys.dont_write_bytecode = previous
        print(json.dumps({'group_id': group['id'], 'suite_id': suite['id'],
                          'checkpoints': count, 'case_path_aliases': len(manifest['case_path_aliases']),
                          'snapshot_sha256': manifest['snapshot_sha256'],
                          'control_prepared': control.is_dir()}, ensure_ascii=False))
assert route_total == 49, route_total
print(json.dumps({'new_groups': len(new_refs), 'dispatcher_routes_validated': route_total,
                  'builds_run': 0, 'paid_model_calls': 0}, ensure_ascii=False))
