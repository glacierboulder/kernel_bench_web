"""Build profiles must accept the deployment's one/two compiler job contract."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ASSETS = Path(__file__).resolve().parents[1] / 'benchmarks/occt/evaluation/cases/evaluator_assets'
PROFILES = [
    'five_group_originals/g1/run_eval.py',
    'five_group_originals/g2/run_eval.py',
    'occt-bf-group-d9d310-21494-29807-31835/routed_run_eval.py',
    'occt-bf-group-b55-27310-27773-27252-oracle-v2/routed_run_eval.py',
    'occt-bf-group-b2613378-27780-27252-21494-v1/build_helper.py',
]

class CompilerJobsProfilesTests(unittest.TestCase):
    def test_job_contract_reaches_actual_build_command(self):
        for index, relative in enumerate(PROFILES):
            spec = importlib.util.spec_from_file_location(f'compiler_profile_{index}', ASSETS / relative)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for jobs in ('1', '2', None):
                    with self.subTest(profile=relative, jobs=jobs):
                        with patch.dict(os.environ, {}, clear=False), patch.object(module, '_overlay', return_value=root), patch.object(module, 'run', return_value={'return_code': 0}) as run:
                            os.environ.pop('BENCH_COMPILER_JOBS', None)
                            if jobs is not None:
                                os.environ['BENCH_COMPILER_JOBS'] = jobs
                            result = module.configure_and_build(root, root / 'build')
                            self.assertEqual(result['build']['return_code'], 0)
                            build_command = run.call_args_list[-1].args[0]
                            self.assertEqual(build_command[build_command.index('--parallel') + 1], jobs or '2')
                for invalid in ('0', '3', 'two'):
                    with self.subTest(profile=relative, invalid=invalid):
                        with patch.dict(os.environ, {'BENCH_COMPILER_JOBS': invalid}), patch.object(module, 'run') as run:
                            result = module.configure_and_build(root, root / 'build')
                            self.assertIn('failure', result)
                            run.assert_not_called()
