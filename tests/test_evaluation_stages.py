import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.study import evaluation_record


class EvaluationStageTests(unittest.TestCase):
    def test_patch_application_failure_is_recorded_when_report_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'patch.diff').write_text('invalid patch')
            result={'failure_stage':'submission','report':{'provided':False},'tests':[],'passed':False}
            with patch('backend.study.put'):
                record=evaluation_record(None,result,1,directory=root)
            stages={item['name']:item['status'] for item in record['stages']}
            self.assertEqual(stages['submission'],'failed')
            self.assertEqual(stages['patch_application'],'failed')

    def test_successful_patch_application_is_separate_from_missing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'patch.diff').write_text('valid patch bytes')
            result={'patch_bytes':17,'report':{'provided':False},'tests':[],'passed':False}
            with patch('backend.study.put'):
                record=evaluation_record(None,result,0,directory=root)
            stages={item['name']:item['status'] for item in record['stages']}
            self.assertEqual(stages['submission'],'failed')
            self.assertEqual(stages['patch_application'],'passed')


if __name__=='__main__':
    unittest.main()
