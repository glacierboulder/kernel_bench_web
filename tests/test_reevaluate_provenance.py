import unittest

from backend.catalog import validate_bundle
from backend.reevaluate import _source_for_run
from backend.settings import SETTINGS


class ReevaluationSourceProofTests(unittest.TestCase):
    def test_commit_identifier_without_tree_proof_is_rejected(self):
        bundle=validate_bundle(SETTINGS.benchmark_root)
        source=next(iter(bundle["sources"].values()))
        run={"task":{"base_commit":source["commit"]}}
        with self.assertRaisesRegex(ValueError,"refusing commit-only inference"):
            _source_for_run(run,bundle)

    def test_locked_tree_hash_is_required_even_when_source_id_is_present(self):
        bundle=validate_bundle(SETTINGS.benchmark_root)
        source_id,source=next(iter(bundle["sources"].items()))
        with self.assertRaisesRegex(ValueError,"commit identity alone is insufficient"):
            _source_for_run({"task":{"source_id":source_id}},bundle)
        found,proof=_source_for_run({"task":{"source_id":source_id},
                                     "provenance":{"source_tree_sha256_locked":source["materialized_tree_sha256"]}},bundle)
        self.assertEqual(found,source_id)
        self.assertEqual(proof,"run_provenance.source_tree_sha256_locked")


if __name__=="__main__":
    unittest.main()
