"""Verify the review checkout's evidence, source locks, and suite selection."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BENCH = REPO / "benchmarks/occt"
FINAL = HERE / "rollout-v33"

sys.path.insert(0, str(REPO))
from backend.catalog import public_task, validate_bundle
from backend.checkpoints import get_suite
from backend.reevaluate import _select_group
from make_plan import CORE, build_plan


def require(test, message):
    if not test:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO)


def audit_bytes(evidence):
    for name, checksum in evidence["files"].items():
        path = REPO / name
        require(path.is_file() and not path.is_symlink() and sha(path) == checksum, f"missing or changed file: {name}")
    tracked = set(git("ls-files", "-z").decode().split("\0"))
    missing = evidence["files"].keys() - tracked
    require(not missing, f"required files absent from Git: {sorted(missing)}")
    require(set(evidence["previously_ignored_required_files"]) <= tracked, "ignored evidence omitted from Git")
    print(f"Evidence: {len(evidence['files'])} verified files, "
          f"{len(evidence['previously_ignored_required_files'])} explicitly included despite ignore rules")


def compare_defaults(bundle, evidence):
    index = read(BENCH / "catalog.json")
    groups = {f"{row['id']}@{row['version']}": row for row in index["groups"]}
    suites = {(row["id"], row["version"]): row["path"] for row in index["evaluation_suites"]}
    defaults = {"benchmarks/occt/sources.lock.json"}
    for (name, version), group in bundle["groups"].items():
        default = group["evaluation_suite"]
        suite = suites[default["id"], default["version"]]
        task = public_task(bundle, group)
        require(task["evaluation_suite"] == default, f"default queue route changed on {name}")
        defaults.update("benchmarks/occt/" + path for path in (groups[f"{name}@{version}"]["path"], suite))
    case_paths = set()
    for group in bundle["groups"].values():
        default = group["evaluation_suite"]
        suite = bundle["suites"][default["id"], default["version"]]
        case_paths.update(suite.get("support_files", ()))
        for case in suite["checkpoints"]:
            case_paths.add(case["case"])
            case_paths.update(case.get("runner_options", {}).get("inputs", ()))
    defaults.update("benchmarks/occt/" + path for path in case_paths)
    for baseline, expected in (("base_commit", 88), ("target_main_commit", 84)):
        revision = evidence[baseline]
        old = json.loads(git("show", f"{revision}:benchmarks/occt/catalog.json"))
        require(len(old["evaluation_suites"]) == expected and old["groups"] == index["groups"]
                and old["issues"] == index["issues"], f"changed group or issue inventory vs {baseline}")
        for path in sorted(defaults):
            require(git("show", f"{revision}:{path}") == (REPO / path).read_bytes(),
                    f"changed default artifact vs {baseline}: {path}")
        dispatch = "benchmarks/occt/evaluation/cases/evaluator_assets/five_group_execution/dispatch_lock.json"
        frozen_routes = json.loads(git("show", f"{revision}:{dispatch}"))
        live_routes = read(REPO / dispatch)
        for name, entries in frozen_routes.items():
            if name in {"suite_routes", "checkpoint_routes"}:
                require(all(live_routes[name].get(k) == v for k, v in entries.items()), "historical dispatch changed")
            else:
                require(entries == live_routes[name], "historical dispatcher contract changed")
    print(f"Defaults: {len(groups)} groups and {len(case_paths)} declared default case materials "
          "byte-identical to main and the preparation base")


def audit_routes(bundle, evidence):
    old = json.loads(git("show", f"{evidence['base_commit']}:benchmarks/occt/catalog.json"))
    frozen = {(row["id"], row["version"]) for row in old["evaluation_suites"]}
    new = set(bundle["suites"]) - frozen
    require(len(frozen) == 88 and len(new) == 26, "unexpected added suite count")
    negative = 0
    for name, version in sorted(new):
        suite = get_suite(BENCH, name, version)
        source, = suite["source_ids"]
        group = _select_group(bundle, suite, source, None)
        require(group["id"] in suite["group_ids"] and group["source_id"] == source
                and group["evaluation_suite"] != {"id": name, "version": version},
                f"incorrect routing or default for {name}")
        lock = bundle["sources"][source]
        other = next((i for i, s in bundle["sources"].items() if i != source and s["commit"] == lock["commit"]),
                     next(i for i in bundle["sources"] if i != source))
        try:
            _select_group(bundle, suite, other, None)
        except ValueError as failure:
            require("incompatible" in str(failure), str(failure))
            negative += 1
        else:
            raise ValueError(f"{name} selected an unbound source identity")
    print(f"Routes: {len(new)} opt-in selections accepted, {negative} wrong identities rejected")
    return new


def audit_ledger(bundle):
    ledger = read(FINAL / "ledger.json")
    sources = {row["source_id"]: row for row in ledger["rows"]}
    require(len(sources) == len(ledger["rows"]) == 37 and sources.keys() == bundle["sources"].keys(), "source denominator")
    ref_counts = Counter()
    for source, row in sources.items():
        lock = bundle["sources"][source]
        for key in ("commit", "materialized_tree_sha256", "toolchain"):
            require(row[key] == lock[key], f"{source}: source identity drift")
        common = row["core"]["checks"]
        require(set(common) == set(CORE) and all(c["status"] == "CALIBRATED" for c in common.values()),
                f"{source}: common checks incomplete")
        statuses = []
        for entry in row["registered_suites"]:
            suite = bundle["suites"][tuple(entry["suite"].split("@"))]
            require(source in suite["source_ids"], f"{source}: unbound specialist")
            expected = {c["id"] for c in suite["checkpoints"] if c["category"] == "regression"}
            require(set(entry["rollout_status_by_checkpoint"]) == expected, f"{source}: counted unexpected check")
            statuses.extend(entry["rollout_status_by_checkpoint"].values())
        require("CALIBRATED" in statuses, f"{source}: no calibrated specialist")
        ref_counts.update(statuses)
    require(ref_counts == {"CALIBRATED": 37, "CALIBRATION_FAILED": 27, "NOT_RUN": 65},
            f"unexpected reference totals {ref_counts}")
    coons = sources["occt801-b8f597c67781-coons"]
    require(coons["coons_boundary_audit"]["status"] == "BASELINE_FAIL", "known Value defect history was lost")
    require(build_plan() == read(FINAL / "version-plan.json"), "final plan differs from the live bundle")
    print(f"Coverage: {len(sources)} locks, {len(sources)*len(CORE)} common checks, {dict(ref_counts)}")
    return sources


def audit_formal(bundle, evidence, optional):
    found = set()
    for filename in evidence["formal_manifests"]:
        path = REPO / filename
        manifest = read(path)
        folder = path.parent
        for name, checksum in manifest["receipts"].items():
            require(sha(folder / name) == checksum, f"{name}: failed recorded receipt checksum")
        for name, checksum in manifest.get("case_hashes", manifest.get("assets", {})).items():
            require(sha(BENCH / name) == checksum, f"{name}: frozen case materials changed")
        cli = read(folder / "cli.json")
        driver = read(folder / "driver.json")
        snap = read(folder / "snapshot.json")
        receipt = cli["reevaluation"]
        identity = receipt["source_id"]
        key = (receipt["suite_id"], receipt["suite_version"])
        require(key in optional and key not in found and identity in bundle["suites"][key]["source_ids"],
                f"formal receipt has wrong suite or identity: {path}")
        found.add(key)
        lock = bundle["sources"][identity]
        require(cli["returncode"] == 0 and receipt["model_called"] is False and driver["passed"]
                and receipt["snapshot_sha256"] == snap["snapshot_sha256"]
                and receipt["patch_sha256"] == manifest["patch"]
                and receipt["source_commit"] == snap["source_commit"] == lock["commit"]
                and receipt["source_tree_sha256"] == snap["source_tree_sha256"] == lock["materialized_tree_sha256"]
                and snap["toolchain_id"] == lock["toolchain"], f"unbound official result: {path}")
    require(len(found) == 13, "missing full-formal receipt bundle")
    print(f"Receipts: {len(found)} complete CLI bundles matched to the current suite, source and artifact hashes")


def main():
    evidence = read(HERE / "review-evidence.json")
    audit_bytes(evidence)
    bundle = validate_bundle(BENCH)
    compare_defaults(bundle, evidence)
    optional = audit_routes(bundle, evidence)
    audit_ledger(bundle)
    audit_formal(bundle, evidence, optional)


if __name__ == "__main__":
    main()
