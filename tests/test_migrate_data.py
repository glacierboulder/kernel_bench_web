import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.migrate_data import migrate


class MigrationTests(unittest.TestCase):
    def test_dry_run_and_quiesced_copy_preserve_original(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/"old";source.mkdir();target=base/"new"
            database=source/"bench.sqlite3"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE values_table (value TEXT)")
                connection.execute("INSERT INTO values_table VALUES ('kept')")
            (source/"notes.txt").write_text("keep this")
            dry=migrate(source,target)
            self.assertTrue(dry["dry_run"]);self.assertFalse(target.exists())
            with self.assertRaisesRegex(ValueError,"--quiesced"):
                migrate(source,target,execute=True)
            result=migrate(source,target,execute=True,quiesced=True)
            self.assertFalse(result["dry_run"])
            self.assertEqual((source/"notes.txt").read_text(),"keep this")
            with sqlite3.connect(target/"bench.sqlite3") as connection:
                self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0],"ok")
                self.assertEqual(connection.execute("SELECT value FROM values_table").fetchone()[0],"kept")
            manifest=json.loads((target/"migration-manifest.json").read_text())
            self.assertTrue(manifest["original_preserved"])

    def test_destination_must_be_empty_and_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/"old";source.mkdir();target=root/"new";target.mkdir()
            (target/"sentinel").touch()
            with self.assertRaisesRegex(ValueError,"empty"):
                migrate(source,target)


if __name__=="__main__":
    unittest.main()
