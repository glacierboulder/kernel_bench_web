"""Keep official production CLI and sandbox receipts without moving original evidence."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(directory, output):
    run, = (directory / "data/reevaluations").iterdir()
    frozen = run / "benchmark-snapshot"
    control = run / "evaluation-control"
    suite = json.loads((frozen / "suite.json").read_text())
    checkpoint, = suite["checkpoints"]
    materials = [checkpoint["case"], *checkpoint.get("runner_options", {}).get("inputs", []),
                 *suite.get("support_files", [])]
    material_hashes = {}
    for material in materials:
        actual = sha(control / "cases/bundle" / material)
        if actual != sha(frozen / "supervisor/cases/bundle" / material):
            raise ValueError(f"frozen / mounted mismatch: {material}")
        material_hashes[material] = actual
    files = {name: directory / name for name in ("cli.json", "cli.stderr")}
    files.update({
        "driver.json": run / "evaluation.raw.json",
        "internal.json": run / "evaluation.internal.json",
        "driver.stderr.txt": run / "evaluation-stderr.log",
        **{name: frozen / name for name in ("snapshot.json", "suite.json", "source-lock.json", "toolchain.json")},
    })
    output.mkdir(parents=True, exist_ok=False)
    for name, path in files.items():
        shutil.copyfile(path, output / name)
    manifest = {
        "host": platform.node(), "run": run.name, "patch": sha(run / "patch.diff"),
        "case_hashes": material_hashes, "runner": sha(control / "suite_driver.py"),
        "build_helper": sha(control / "private/evaluators/run_eval.py"),
        "receipts": {name: sha(path) for name, path in files.items()},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    collect(*map(Path, sys.argv[1:]))
