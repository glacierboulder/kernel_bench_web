# Data migration and rollback

The application never moves existing data automatically. If a deployment has an in-repository `data/bench.sqlite3`, default settings continue using that directory. Fresh clones use a per-user data directory outside the repository.

## Dry run

First inspect the current data path and available space. Stop the app and all workers before execution. A dry run does not copy or change files:

```bash
python -m backend.migrate_data --from <old-data-dir> --to <new-data-dir>
```

It reports source bytes and SQLite database count. It refuses symlinks, non-empty destinations and nested source/destination directories.

## Execute

After confirming the target has enough free space and the app/workers are quiesced:

```bash
python -m backend.migrate_data --from <old-data-dir> --to <new-data-dir> \
  --execute --quiesced
```

SQLite files are copied with SQLite's online backup API and checked with `PRAGMA quick_check`. Other files are copied and SHA256-verified. The tool stages the whole result beside the destination and atomically renames the completed directory into place. The original remains untouched. It skips transient worker status/lock files and SQLite WAL/SHM sidecars because the database backup API captures committed database state.

Migration can require a full second copy of run data, workspaces and assets. Check free space before execution. This repository session did not migrate the existing multi-gigabyte data tree.

## Switch and rollback

Only after migration succeeds, update the deployment config or `BENCH_DATA_DIR` to the new directory and restart the app. Verify the historical tasks, runs, evaluations, notes and assets through the UI/API. Keep the old directory until that review is complete.

To roll back, stop app/workers and point the config back to the old directory. No reverse copy is needed because the migration tool preserves the original. If new runs were created in the migrated directory after switching, they remain there; do not delete either tree while reconciling them.
