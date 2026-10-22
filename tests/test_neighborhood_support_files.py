"""Explicit supervisor dependencies must survive freezing without escaping the bundle."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from backend.catalog import CatalogError, validate_bundle
from backend.freeze import normalize_suite_case_material

ROOT = Path(__file__).resolve().parents[1]

class NeighborhoodSupportFilesTests(unittest.TestCase):
    def test_support_files_are_copied_with_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            helper = root / 'evaluation/cases/neighbor/helper.tcl'
            case = helper.with_name('case.tcl')
            helper.parent.mkdir(parents=True)
            helper.write_bytes(b'# trusted helper\n')
            case.write_bytes(b'source helper.tcl\n')
            suite = {'support_files': ['evaluation/cases/neighbor/helper.tcl'],
                     'checkpoints': [{'id': 'physical-check', 'case': 'evaluation/cases/neighbor/case.tcl'}]}
            target = Path(directory) / 'frozen'
            normalized, aliases = normalize_suite_case_material({'root': root}, {'issues': []}, suite, target)
            self.assertEqual((target / suite['support_files'][0]).read_bytes(), helper.read_bytes())
            self.assertEqual((target / suite['checkpoints'][0]['case']).read_bytes(), case.read_bytes())
            self.assertEqual(normalized['support_files'], suite['support_files'])
            self.assertEqual(aliases, [])

    def test_catalog_rejects_missing_escape_duplicate_and_non_string_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'bundle'
            shutil.copytree(ROOT / 'docs/benchmark-example', root)
            index = json.loads((root / 'catalog.json').read_text())
            suite_path = root / index['evaluation_suites'][0]['path']
            original = json.loads(suite_path.read_text())
            for paths in (['missing.tcl'], ['../escape.tcl'], ['a.tcl', 'a.tcl'], [None]):
                with self.subTest(paths=paths):
                    suite_path.write_text(json.dumps({**original, 'support_files': paths}))
                    with self.assertRaises(CatalogError):
                        validate_bundle(root)
