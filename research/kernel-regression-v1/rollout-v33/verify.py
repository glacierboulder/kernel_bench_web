"""Verify the independent Coons tangent references and formal build before registration."""
import argparse
import csv
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import sys

from stage import BENCH, HERE, PREVIOUS, REPO, candidate

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE.parent))
from backend.catalog import validate_bundle
from make_plan import CORE, build_plan, version_index

PRIOR = HERE.parent / "rollout-v32"
PRIOR_BUILD = HERE.parent / "rollout-v5/receipts/coons"
VALUE_HISTORY = HERE.parent / "rollout-v29"
RECEIPTS = HERE / "receipts"
NEUTRAL = HERE.parent / "rollout-v21/neutral.diff"
HELPER = BENCH / "evaluation/cases/occt1115-coons-gcc/run_eval.py"
ARTIFACT = "gh1550-tangents.csv"
BUILD_RECORD = "gh1550-build-sha256.txt"
BUILD_COMMANDS = "gh1550-build-commands.txt"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path):
    return {"path": str(path.relative_to(REPO)), "sha256": sha(path)}


def require(condition, label):
    if not condition:
        raise ValueError(label)


STATIONS = (0, .125, .5, .875, 1)
FIXTURES = {"rectangle": (10, 6), "bilinear": (1, 1)}
CONTROL_COUNTS = {"native": (25, 25), "swap": (0, 0), "reverse-u": (0, 25), "reverse-v": (25, 0)}
TOLERANCE = 1e-7


def vectors(artifact):
    expected_columns = ["fixture", "control", "u", "v", "dux", "duy", "duz", "dvx", "dvy", "dvz"]
    records = {}
    with artifact.open(newline="") as stream:
        data = csv.reader(stream)
        require(next(data) == expected_columns, "invalid trace columns")
        for fixture, control, us, vs, *vector in data:
            u, v = map(float, (us, vs))
            pair = tuple(map(float, vector))
            key = (fixture, control, u, v)
            require(len(pair) == 6 and key not in records and all(math.isfinite(x) for x in pair),
                    "duplicate or invalid tangent sample")
            records[key] = (pair[:3], pair[3:])
    expected = {(fixture, control, u * u_span, v * v_span)
                for fixture, (u_span, v_span) in FIXTURES.items() for control in CONTROL_COUNTS
                for u in STATIONS for v in STATIONS}
    require(records.keys() == expected, "wrong fixture stations or missing controls")
    return records


def measurements(result, artifact):
    require(result["passed"] and result["status"] == "passed"
            and result["compile"]["return_code"] == 0 and not result["compile"]["timed_out"],
            "checkpoint did not compile and pass")
    data = result["result"]
    require(data["return_code"] == 0 and not data["timed_out"], "checkpoint did not complete")
    lines = data["output_tail"].splitlines()
    require(lines[-1] == "TEST_DONE", "missing completed evaluation")
    observed = {}
    statement = re.compile(r"CONTROL (\w+) (\S+) good_u=(\d+) good_v=(\d+) "
                           r"max_u=(\S+) max_v=(\S+) verdict=(PASS|FAIL)")
    for line in lines[:-1]:
        match = statement.fullmatch(line)
        require(match is not None, "unexpected evaluator output")
        fixture, control, count_u, count_v, max_u, max_v, verdict = match.groups()
        key = (fixture, control)
        require(fixture in FIXTURES and control in CONTROL_COUNTS and key not in observed, "wrong reported control")
        observed[key] = (int(count_u), int(count_v), float(max_u), float(max_v), verdict)
    records = vectors(artifact)
    states = {name: {} for name in FIXTURES}
    for fixture, (u_span, v_span) in FIXTURES.items():
        for control, counts in CONTROL_COUNTS.items():
            errors = []
            for s in STATIONS:
                for t in STATIONS:
                    u, v = s * u_span, t * v_span
                    du, dv = records[fixture, "native", u, v]
                    neg_u, neg_v = (tuple(-x for x in vec) for vec in (du, dv))
                    transformed = {"native": (du, dv), "swap": (dv, du),
                                   "reverse-u": (neg_u, dv), "reverse-v": (du, neg_v)}
                    actual = records[fixture, control, u, v]
                    require(actual == transformed[control], "negative injection did not produce real transformed vectors")
                    expected = ((.6, 0., .8), (0., 1., 0.)) if fixture == "rectangle" else (
                        (10., 0., 2. - 3. * v), (0., 10., 1. - 3. * u))
                    errors.append(tuple(math.dist(a, b) for a, b in zip(actual, expected)))
            axis_errors = list(zip(*errors))
            recomputed = tuple(sum(e <= TOLERANCE for e in axis) for axis in axis_errors)
            max_errors = tuple(max(axis) for axis in axis_errors)
            verdict = "PASS" if control == "native" else "FAIL"
            reported = observed[fixture, control]
            require(recomputed == counts == reported[:2] and verdict == reported[4]
                    and all(abs(a - b) <= 1e-13 for a, b in zip(max_errors, reported[2:4])),
                    "independent derivative check differs from the recorded verdict")
            states[fixture][control] = {"verdict": verdict, "good_u": counts[0], "good_v": counts[1],
                                         "max_u": max_errors[0], "max_v": max_errors[1], "stations": 25}
    require(len(observed) == 8, "missing fixture metrics")
    return states


def clean(suite):
    folder = RECEIPTS / "clean"
    process = read(folder / "process.json")
    identity, runtime = (read(PRIOR_BUILD / label) for label in ("identity.json", "runtime.json"))
    require(process["exit"] == 0 and process["host"] == "ws01"
            and "--unshare-all" in process["sandbox"]
            and process["identity"] == identity and process["runtime"] == runtime
            and process["tree_sha256"] == identity["observed_tree"]
            and identity["source_id"] == suite["source_ids"][0], "wrong verified clean build")
    case, = suite["checkpoints"]
    input_hashes = process["input_hashes"]
    require(input_hashes["clean.py"] == sha(HERE / "clean.py")
            and input_hashes["suite_driver.py"] == sha(REPO / "backend/suite_driver.py")
            and input_hashes["suite.json"] == sha(HERE / "proposed.json")
            and all(input_hashes["bundle/" + p] == sha(BENCH / p)
                    for p in [case["case"], *case["runner_options"].get("inputs", ())]), "wrong clean-run input bytes")
    artifact = folder / ARTIFACT
    require(process["artifact_sha256"] == sha(artifact), "live clean artifact differs from the receipt")
    checkpoint = read(folder / "checkpoint.json")
    require(checkpoint["suite"] == suite["id"] + "@1" and checkpoint["checkpoint"] == case["id"],
            "wrong clean checkpoint")
    return {"controls": measurements(checkpoint, artifact), "artifact": ref(artifact),
            "checkpoint": ref(folder / "checkpoint.json"), "build": ref(folder / "process.json")}


def check_build_hashes(folder):
    configure, build = map(shlex.split, (folder / BUILD_COMMANDS).read_text().splitlines())
    require(configure[:2] == ["/usr/bin/cmake", "-S"]
            and {"-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++", "-DCMAKE_BUILD_TYPE=Release",
                 "-DBUILD_ADDITIONAL_TOOLKITS=TKGeomAlgo"} <= set(configure)
            and build[:2] == ["/usr/bin/cmake", "--build"]
            and build[3:] == ["--parallel", "2", "--target", "TKGeomAlgo"], "wrong actual build commands")
    directory = Path(build[2])
    require(configure[configure.index("-B") + 1] == str(directory), "build output mismatch")
    recorded = (folder / BUILD_RECORD).read_text().splitlines()
    require(recorded[0] == "13.3.0" and set(recorded[1:3]) ==
            {"BUILD_ADDITIONAL_TOOLKITS:STRING=TKGeomAlgo", "CMAKE_CXX_FLAGS_RELEASE:STRING=-O3 -DNDEBUG"},
            "wrong compiler, targets or Release flags")
    entries = [line.split(maxsplit=1) for line in recorded[3:]]
    require(all(re.fullmatch("[0-9a-f]{64}", digest) for digest, _ in entries), "invalid recorded build hashes")
    files = {Path(path).name: {"sha256": digest, "path": path} for digest, path in entries}
    libs = directory / "lin64/gcc/lib"
    require(len(files) == len(entries) and files["CMakeCache.txt"]["path"] == str(directory / "CMakeCache.txt")
            and all(entry["path"] == str(libs / name) for name, entry in files.items() if name != "CMakeCache.txt")
            and {"libTKGeomAlgo.so", "libTKGeomBase.so", "libTKG3d.so"} <= files.keys(),
            "recorded hashes do not belong to the executed build")
    return files


def formal(suite, staged_catalog):
    folder = RECEIPTS / "formal"
    manifest, snap, lock, tool, cache, cli, raw = (read(folder / name) for name in (
        "manifest.json", "snapshot.json", "source-lock.json", "toolchain.json",
        "verified-source.json", "cli.json", "driver.json"))
    for name, digest in manifest["receipts"].items():
        require(sha(folder / name) == digest, "raw receipt changed: " + name)
    require(manifest["host"] == "ws01" and read(folder / "suite.json") == suite
            and manifest["runner"] == sha(REPO / "backend/suite_driver.py")
            and manifest["build_helper"] == sha(HELPER), "wrong formal evaluator")
    source, = suite["source_ids"]
    require(snap["catalog_hash"] == hashlib.sha256(staged_catalog.encode()).hexdigest()
            and snap["task_id"] == suite["group_ids"][0] and snap["suite_id"] == suite["id"]
            and snap["suite_version"] == suite["version"], "wrong formal suite selection")
    require(source == lock["source_id"] == cache["source_id"] == snap["source_id"]
            and cache["verification_status"] == "verified_git"
            and lock["commit"] == cache["commit"] == snap["source_commit"]
            and lock["materialized_tree_sha256"] == cache["tree_sha256"] == snap["source_tree_sha256"]
            and lock["toolchain"] == tool["id"] == snap["toolchain_id"], "wrong formal source lock")
    case, = suite["checkpoints"]
    paths = [case["case"], *case["runner_options"].get("inputs", ())]
    require(manifest["case_hashes"] == {path: sha(BENCH / path) for path in paths}, "formal inputs differ")
    reevaluation = cli["reevaluation"]
    require(cli["returncode"] == 0 and cli["run_id"] is None and not reevaluation["model_called"]
            and reevaluation["snapshot_sha256"] == snap["snapshot_sha256"]
            and reevaluation["patch_sha256"] == manifest["patch"] == sha(NEUTRAL)
            and raw["passed"] and raw["patch_bytes"] == NEUTRAL.stat().st_size
            and not raw.get("failure_stage"), "formal neutral build did not pass")
    require(all(raw["build"][key]["return_code"] == 0 for key in ("configure", "build")),
            "wrong formal build result")
    artifacts = check_build_hashes(folder)
    artifact = folder / ARTIFACT
    names = (ARTIFACT, BUILD_RECORD, BUILD_COMMANDS)
    records = dict(line.split(maxsplit=1) for line in (folder / "run-artifact-sha256.txt").read_text().splitlines())
    require(records == {sha(folder / name): name for name in names}, "trace or build record not bound to the run")
    checkpoint, = raw["checkpoints"]
    require(checkpoint["id"] == case["id"], "wrong formal checkpoint")
    roles = measurements(checkpoint["result"] | {"status": checkpoint["status"]}, artifact)
    return {
        "source_id": source, "commit": cache["commit"], "tree_sha256": cache["tree_sha256"],
        "toolchain": tool["id"], "suite": suite["id"] + "@1", "checkpoint": checkpoint["id"],
        "elapsed_seconds": raw["elapsed_seconds"], "controls": roles, "build_artifacts": artifacts,
        "artifact": ref(artifact), "receipts": [ref(folder / p) for p in ("cli.json", "driver.json",
                    "manifest.json", BUILD_RECORD, BUILD_COMMANDS, "run-artifact-sha256.txt", "verified-source.json")],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--clean-only", action="store_true")
    args = parser.parse_args()
    suite = read(HERE / "proposed.json")
    paired = clean(suite)
    if args.clean_only:
        print({fixture: {role: data["verdict"] for role, data in cases.items()}
               for fixture, cases in paired["controls"].items()})
        return
    staged = candidate()
    proof = formal(suite, staged["catalog.json"])
    for fixture, controls in paired["controls"].items():
        for role, observed in controls.items():
            actual = proof["controls"][fixture][role]
            require(actual["verdict"] == observed["verdict"] and actual["stations"] == observed["stations"]
                    and actual["good_u"] == observed["good_u"] and actual["good_v"] == observed["good_v"]
                    and all(abs(actual[key] - observed[key]) <= TOLERANCE for key in ("max_u", "max_v")),
                    "paired builds gave inconsistent tangents")
    require("Ran 17 tests" in (RECEIPTS / "framework-tests.txt").read_text()
            and (RECEIPTS / "framework-tests.txt").read_text().strip().endswith("OK"), "staged framework tests did not pass")
    prior_plan = read(PREVIOUS / "version-plan.json")
    for version in prior_plan["sources"]:
        for record in (*version["suites"], *version["groups"]):
            require(sha(BENCH / record["path"]) == record["sha256"], "historical score manifest was changed")
    path, = [p for p in staged if p != "catalog.json"]

    def write(target, text):
        if args.register:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        else:
            require(target.read_text() == text, "stale: " + str(target))

    if args.register:
        require(read(BENCH / "catalog.json") in (
                read(PREVIOUS / "catalog.snapshot.json"), json.loads(staged["catalog.json"])),
                "concurrent registry changes")
    for target, content in staged.items():
        write(BENCH / target, content)
    validate_bundle(BENCH)
    snapshot = HERE / "catalog.snapshot.json"
    write(snapshot, staged["catalog.json"])
    plan = build_plan(snapshot)
    write(HERE / "version-plan.json", json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    write(HERE / "versions.md", version_index(plan))

    old = PRIOR / "ledger.json"
    ledger = read(old)
    row, = [r for r in ledger["rows"] if r["source_id"] == proof["source_id"]]
    require(row["status"] == "PARTIALLY_CALIBRATED" and row["commit"] == proof["commit"]
            and row["materialized_tree_sha256"] == proof["tree_sha256"] and row["toolchain"] == proof["toolchain"]
            and row["coons_boundary_audit"]["status"] == "BASELINE_FAIL"
            and all(check["status"] == "CALIBRATED" for check in row["core"]["checks"].values()),
            "wrong prior locked identity or coverage")
    row["status"] = "CALIBRATED"
    checkpoint = proof["checkpoint"]
    row["registered_suites"].append({
        "suite": proof["suite"], "manifest": path, "sha256": sha(BENCH / path), "regressions": [checkpoint],
        "rollout_status_by_checkpoint": {checkpoint: "CALIBRATED"},
    })
    scope = "D1U and D1V only, on the locked tilted rectangle and straight-sided bilinear Coons fixtures."
    row["registered_addition"] = {
        "suite": proof["suite"], "checkpoint": checkpoint, "execution_scope": scope, "receipts": proof["receipts"],
    }
    archived_value = read(VALUE_HISTORY / "results.json")
    require(archived_value["status"] == "BASELINE_FAIL"
            and archived_value["registered_status"]["original-0"] == "FAILED", "lost Value baseline evidence")
    history = {"status": "BASELINE_FAIL", "receipt": ref(VALUE_HISTORY / "results.json")}
    row["tangent_integration"] = {"status": "CALIBRATED", "scope": scope,
                                  "formal_vectors": proof["artifact"], "clean_vectors": paired["artifact"],
                                  "value_history": history}
    rows = ledger["rows"]
    locks = read(BENCH / "sources.lock.json")["sources"]
    require(len(rows) == len(locks) == 37
            and {r["source_id"] for r in rows} == {lock["source_id"] for lock in locks},
            "coverage denominator does not match the locked inventory")
    require(all(set(r["core"]["checks"]) == set(CORE)
                and all(c["status"] == "CALIBRATED" for c in r["core"]["checks"].values())
                and any(state == "CALIBRATED" for s in r["registered_suites"]
                        for state in s["rollout_status_by_checkpoint"].values()) for r in rows),
            "some identity has missing common or registered coverage")
    counts = Counter(r["status"] for r in rows)
    refs = Counter(state for r in ledger["rows"] for s in r["registered_suites"]
                   for state in s["rollout_status_by_checkpoint"].values())
    require(counts == {"CALIBRATED": 37}
            and refs == {"NOT_RUN": 65, "CALIBRATED": 37, "CALIBRATION_FAILED": 27}
            and sum(refs.values()) == plan["counts"]["registered_regression_refs"] == 129, "wrong coverage total")
    ledger.update(version=33, previous=ref(old), protocol=ref(HERE / "proposed.json"),
                  current_catalog=ref(snapshot), source_matrix=ref(HERE / "version-plan.json"),
                  counts={key: counts[key] for key in ledger["counts"]})
    ledger["coverage"]["both_portable_and_registered_specialist"] = counts["CALIBRATED"]
    proof.update(clean=paired, scope=scope, value_history=history, registered_references=dict(refs),
                 coverage=ledger["coverage"], model_runs=0, behavior_changing_patches_evaluated=0)
    if not args.register:
        archived = read(HERE / "results.json")
        # math.dist can round the same raw vectors differently across Python
        # versions. The classification and archived result bytes stay fixed.
        for calculated, recorded in (
            (proof["controls"], archived["controls"]),
            (proof["clean"]["controls"], archived["clean"]["controls"]),
        ):
            for fixture, controls in calculated.items():
                for role, row in controls.items():
                    for axis in ("max_u", "max_v"):
                        prior_value = recorded[fixture][role][axis]
                        require(abs(row[axis] - prior_value) <= 2 * math.ulp(prior_value),
                                "archived tangent metric changed beyond floating-point roundoff")
                        row[axis] = prior_value
    for name, data in (("results.json", proof), ("ledger.json", ledger)):
        write(HERE / name, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(ledger["counts"], dict(refs))


if __name__ == "__main__":
    main()
