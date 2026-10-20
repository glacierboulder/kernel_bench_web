import unittest

from backend.checkpoints import normalize_checkpoints
from backend.public_results import public_evaluation


def checkpoint(identity,category,visibility="public",required=True,issue_id="occt-1"):
    return {"id":identity,"issue_id":issue_id,"category":category,"visibility":visibility,
            "runner":"legacy_occt_suite","case":identity,"oracle":"legacy_test_done_v1",
            "timeout_seconds":15,"required":required}


class CheckpointTests(unittest.TestCase):
    def test_categories_statuses_and_empty_category(self):
        suite={"id":"fixture","version":"2","checkpoints":[
            checkpoint("orig-pass","original"),checkpoint("orig-timeout","original"),
            checkpoint("neigh-fail","neighborhood"),checkpoint("reg-hidden","regression","hidden"),
            checkpoint("optional","regression",required=False)]}
        raw={"tests":[
            {"test":"orig-pass","passed":True,"result":{"elapsed_seconds":0.2}},
            {"test":"orig-timeout","passed":False,"result":{"timed_out":True}},
            {"test":"neigh-fail","passed":False,"result":{"output_tail":"failure detail"}},
            {"test":"reg-hidden","passed":True,"result":{"output_tail":"SECRET_HIDDEN_EVIDENCE"}}]}
        value=normalize_checkpoints(suite,raw)
        self.assertFalse(value["technical_passed"])
        self.assertEqual(value["category_summary"]["original"]["passed"],1)
        self.assertEqual(value["category_summary"]["original"]["timeout"],1)
        self.assertEqual(value["category_summary"]["neighborhood"]["failed"],1)
        self.assertEqual(value["category_summary"]["regression"]["state"],"configured")
        hidden=value["checkpoints"][-2]
        self.assertEqual(hidden["visibility"],"hidden")
        public=public_evaluation({**value,"tests":raw["tests"]})
        serialized=str(public)
        self.assertNotIn("reg-hidden",serialized)
        self.assertNotIn("SECRET_HIDDEN_EVIDENCE",serialized)
        self.assertNotIn("output_tail",serialized)

    def test_empty_category_is_not_configured_and_required_missing_is_error(self):
        suite={"id":"missing","version":"1","checkpoints":[checkpoint("missing","original"),
               checkpoint("optional","regression",required=False)]}
        value=normalize_checkpoints(suite,{"tests":[]})
        self.assertFalse(value["technical_passed"])
        self.assertEqual(value["checkpoints"][0]["status"],"error")
        self.assertEqual(value["checkpoints"][1]["status"],"skipped")
        self.assertEqual(value["category_summary"]["neighborhood"]["state"],"未配置")


if __name__=="__main__":
    unittest.main()
