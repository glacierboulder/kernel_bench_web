import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from backend.sandbox import monitor

class MonitorTests(unittest.TestCase):
    def test_process_limit_records_evidence_without_raising_budget(self):
        proc=Mock(pid=9);proc.poll.return_value=None
        with tempfile.TemporaryDirectory() as d,patch('backend.sandbox.descendants',return_value=set(range(1000000,1000129))),patch('backend.sandbox.stop') as stop:
            with self.assertRaisesRegex(RuntimeError,'process_count=129/128'):
                monitor(proc,60,disk_root=Path(d)/'workspace')
            evidence=json.loads((Path(d)/'resource-limit-workspace.json').read_text())
            self.assertEqual(evidence['reason'],'process_count')
            self.assertEqual(evidence['process_limit'],128)
            self.assertEqual(evidence['rss_sum_limit_bytes'],12*1024**3)
            stop.assert_called_once_with(proc)
