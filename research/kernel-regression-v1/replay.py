"""Compile against one pinned build, then measure analytic geometry and reject wrong shapes."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
# Fixtures use one fixed length unit. Length, volume and discrete limits are distinct.
length, volume = 1e-6, 1e-5
solid = {"valid": (1, 0), "solids": (1, 0)}
hole = dict(solid, volume=(1000 - 40 * math.pi, volume), cx=(5, length),
            hole_out=(1, 0), wall_in=(1, 0))
CHECKS = {
    "box-common": dict(solid, volume=(500, volume), cx=(7.5, length),
                       swapped_volume=(500, volume), swapped_cx=(7.5, length)),
    "disjoint": {"solids": (0, 0), "volume": (0, volume), "valid": (1, 0)},
    "cut-fuse": dict(solid, volume=(500, volume), cx=(2.5, length),
                     fused_volume=(1500, volume), fused_valid=(1, 0)),
    "plane-sphere": {"length": (10 * math.pi, length), "witness_distance": (0, length),
                     "valid": (1, 0)},
    "hole-classification": hole,
    "brep-roundtrip": hole,
}
FAULT_KEYS = {"box-common": "cx", "disjoint": "solids", "cut-fuse": "fused_volume",
              "plane-sphere": "witness_distance", "hole-classification": "hole_out",
              "brep-roundtrip": "volume"}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def invoke(cmd, env, cwd, timeout):
    return subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True, timeout=timeout)


def measure(exe, case, mode, env, cwd):
    try:
        run = invoke([str(exe), case, mode], env, cwd, 45)
        if run.returncode:
            return {"status": "INCONCLUSIVE", "exit": run.returncode, "log": run.stdout[-2400:]}
        values = {}
        for row in run.stdout.splitlines():
            fields = row.split()
            if fields and fields[0] in CHECKS[case]:
                key, value = fields
                if key in values:
                    raise ValueError("duplicate metric " + key)
                values[key] = float(value)
        if values.keys() != CHECKS[case].keys():
            raise ValueError("incomplete measurements")
        if not all(math.isfinite(v) for v in values.values()):
            return {"status": "FAIL", "reason": "nonfinite geometry metric"}
        failed = [key for key, (gold, tolerance) in CHECKS[case].items()
                  if abs(values[key] - gold) > tolerance]
        return {"status": "FAIL" if failed else "PASS", "values": values, "failed": failed}
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "INCONCLUSIVE", "reason": str(exc)}


def replay(args, receipt, tmp):
    env = dict(os.environ, LD_LIBRARY_PATH=str(args.lib))
    exe = tmp / "probe"
    modules = "TKBO TKPrim TKTopAlgo TKBRep TKGeomAlgo TKG3d TKG2d TKGeomBase TKMath TKernel".split()
    command = [args.cxx, "-std=" + args.std, "-O0", "-I" + str(args.include),
               str(HERE / "probe.cxx"), "-L" + str(args.lib), "-o", str(exe)]
    command.extend("-l" + name for name in modules)
    receipt["compile_command"] = command
    receipt["compiler"] = invoke([args.cxx, "--version"], env, tmp, 10).stdout.splitlines()[0]
    build = invoke(command, env, tmp, 180)
    if build.returncode:
        receipt["build"] = {"status": "INCONCLUSIVE", "log": build.stdout[-4800:]}
        return
    receipt["build"] = {"status": "PASS"}
    deps = invoke(["ldd", str(exe)], env, tmp, 15)
    linked = {}
    for row in deps.stdout.splitlines():
        cols = row.split()
        if not cols or not cols[0].startswith("libTK"):
            continue
        if len(cols) < 3 or Path(cols[2]).resolve().parent != args.lib:
            raise ValueError("unlocked or missing kernel library: " + row)
        linked[cols[0]] = digest(cols[2])
    if deps.returncode or not linked or "not found" in deps.stdout:
        raise ValueError("incomplete runtime linkage")
    receipt["kernel_libraries_sha256"] = linked
    all_good = True
    for case in CHECKS:
        positive = measure(exe, case, "positive", env, tmp)
        negative = measure(exe, case, "negative", env, tmp)
        rejects = negative["status"] == "FAIL" and FAULT_KEYS[case] in negative.get("failed", [])
        receipt["cases"][case] = {"geometry": positive, "wrong_shape": negative,
                                  "expected_fault_rejected": rejects}
        all_good &= positive["status"] == "PASS" and rejects
    receipt["status"] = "PASS" if all_good else (
        "INCONCLUSIVE" if any(v["geometry"]["status"] == "INCONCLUSIVE" or
                              not v["expected_fault_rejected"] for v in receipt["cases"].values()) else "FAIL")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ("include", "lib", "out"):
        ap.add_argument("--" + key, required=True, type=Path)
    for key in ("source-id", "commit", "tree", "toolchain", "role", "cxx"):
        ap.add_argument("--" + key, required=True)
    ap.add_argument("--std", default="c++11")
    args = ap.parse_args()
    args.include, args.lib = args.include.resolve(), args.lib.resolve()
    if args.out.exists():
        ap.error("receipt already exists")
    t = time.monotonic()
    receipt = {"version": 1, "source_id": args.source_id, "baseline_commit": args.commit,
               "baseline_tree_sha256": args.tree, "toolchain": args.toolchain, "role": args.role,
               "files_sha256": {p: digest(HERE / p) for p in ("probe.cxx", "replay.py")},
               "cases": {}, "status": "INCONCLUSIVE"}
    try:
        with tempfile.TemporaryDirectory() as work:
            replay(args, receipt, Path(work))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        receipt["error"] = str(exc)
    receipt["elapsed_seconds"] = round(time.monotonic() - t, 3)
    with args.out.open("x") as f:
        json.dump(receipt, f, indent=2, allow_nan=False)
        f.write("\n")
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
