from pathlib import Path
import subprocess
import tempfile
import unittest
from backend.submission import materialize

class SubmissionTests(unittest.TestCase):
    def test_patch_applies_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);before=root/'before';after=root/'after'
            before.mkdir();after.mkdir()
            (before/'file.cxx').write_text('old\n')
            (after/'file.cxx').write_text('new')
            patch=root/'patch.diff'
            self.assertEqual(materialize(before,after,patch),['file.cxx'])
            result=subprocess.run(['git','apply','--check',str(patch)],cwd=before,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            link=root/'linked';link.symlink_to(after,target_is_directory=True)
            with self.assertRaises(ValueError):
                materialize(before,link,patch)
            (after/'secret').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                materialize(before,after,patch)
