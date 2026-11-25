"""Apply the official checkpoint to the existing verified clean build for the paired run."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
INPUT = Path("/inputs")
OUTPUT = Path("/out")
ARCHIVE = "/var/tmp/cad-regression-batch5.fjg2gEMa"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def inside():
    from suite_driver import _execute, checkpoint_status
    os.environ["BENCH_CXX"] = "g++"
    os.environ["BENCH_TOOLCHAIN_NAME"] = "gcc"
    os.environ["LD_LIBRARY_PATH"] = "/workspace/build/lin64/gcc/lib"
    work = Path("/tmp/work")
    work.mkdir()
    suite = read(INPUT / "suite.json")
    check, = suite["checkpoints"]
    result = _execute(check, case_root=INPUT / "bundle", build=Path("/workspace/build"),
                      source=Path("/workspace/source"), work=work, draw_runner=Path("/unused"))
    save(OUTPUT / "checkpoint.json", {
        "suite": suite["id"] + "@1", "checkpoint": check["id"], "status": checkpoint_status(result), **result,
    })


def launch():
    sys.path.insert(0, ARCHIVE)
    from sandbox_v3 import tree_sha256
    data = HERE / "inputs"
    identity = read(data / "identity.json")
    runtime = read(data / "runtime.json")
    argv = read(data / "prior-sandbox.json")["argv"]
    source = Path(argv[argv.index("/workspace/source") - 1])
    build = Path(argv[argv.index("/workspace/build") - 1])
    assert str(source) == identity["source_location"]
    tree = tree_sha256(source)
    assert tree == identity["materialized_tree_sha256"] == identity["observed_tree"]
    assert sha(build / "CMakeCache.txt") == runtime["cache_sha256"]
    lib = build / "lin64/gcc/lib"
    assert {p.name: sha(p) for p in sorted(lib.glob("libTK*.so"))} == runtime["libraries"]

    output = HERE / "receipts"
    output.mkdir()
    # Keep kernel source, build and inputs read-only. Only the bounded receipts
    # directory is writable, both for the runner and the live BREP.
    workspace = argv.index("/workspace")
    assert argv[workspace - 1] == "--dir"
    argv[workspace - 1:workspace + 1] = ["--bind", str(output), "/workspace"]
    argv[argv.index("/inputs") - 1] = str(data)
    argv[argv.index("/out") - 1] = str(output)
    argv = argv[:argv.index("/inputs/inside.py")] + ["/inputs/clean.py", "--inside"]
    with (output / "execution.txt").open("wb") as log:
        run = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    artifact = output / "gh1550-tangents.csv"
    save(output / "process.json", {
        "exit": run.returncode, "host": os.uname().nodename, "tree_sha256": tree,
        "input_hashes": {p.relative_to(data).as_posix(): sha(p) for p in sorted(data.rglob("*")) if p.is_file()},
        "identity": identity, "runtime": runtime, "sandbox": argv,
        "artifact_sha256": sha(artifact) if artifact.is_file() else None,
    })
    return run.returncode


if __name__ == "__main__":
    if sys.argv[1:] == ["--inside"]:
        inside()
    else:
        raise SystemExit(launch())
