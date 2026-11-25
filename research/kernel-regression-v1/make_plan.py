"""Build the independent regression inventory from the actual locks and catalog."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] / "benchmarks/occt"
PROFILES = {
    "cells history partition": ["occt801-b8f597c67781"],
    "projection pcurve": ["occt801-b8f597c67781-singularity"],
    "offset": ["occt801-b8f597c67781-offset-plane", "occt801-b8f597c67781-offset2d",
               "occt801-b8f597c67781-offset3d"],
    "construction properties": ["occt23612-derived-e79fa864aeb8-torus"],
    "fillet pcurve": ["occt801-b8f597c67781-periodic-fillet"],
    "cells tolerance": ["occt33570-derived-381c5ec350fd-sphere-cut"],
    "properties": ["occt801-b8f597c67781-plane-properties"],
    "construction pcurve": ["occt801-b8f597c67781-coons"],
    "topology cells history": ["occt-3e80fad1779e"],
    "intersection cells tolerance pcurve": ["occt-ng04r-derived-fe81a63b",
        "occt-ng04t-v1-baseline-ef5af939", "occt-d9d3107d8df1",
        "occt-b55bd0235351", "occt-2613378e60ff", "occt-v4-b41ccce129d0"],
    "cells partition history": ["occt-v4-b84f42008b74", "occt-single20-6435b9c7fafd"],
    "cells topology tolerance": ["occt-v4-bdeea0a89759", "occt-single20-a016080bf673"],
    "intersection pcurve": ["occt-v4-e6afb5398317", "occt-single20-m25818-32ab8bfc4f09",
        "occt-single20-m24313-78b6b239841f", "occt-single20-029311e00f28",
        "occt-single20-cfde7eebb37b", "occt-single20-ea80ac2f61af"],
    "cells intersection pcurve tolerance history": ["occt-single20-1511c7e90f1a",
        "occt-single20-5163f4671951"],
    "fillet intersection tolerance topology": ["occt801-1738-b-b8f597c67781", "occt-1177-b-cbca11e97518",
        "occt75-32929-b-f2724d41b326", "occt801-1163-b-6ba582362af7", "occt801-1371-b-b8f597c67781",
        "occt801-1701-b-b8f597c67781", "occt801-1702-b-b8f597c67781"],
    "cells intersection topology pcurve tolerance": ["oce013-authoring-b-5434272be3ee"],
}
CORE = ["box-common", "disjoint", "cut-fuse", "plane-sphere", "hole-classification", "brep-roundtrip"]
OPTIONAL_SPECIALISTS = {
    "occt-single20-1511c7e90f1a": ("occt-boolean-regression-1511c7e9", "1"),
    "occt-3e80fad1779e": ("occt-544-samedomain-regression", "1"),
}


def read(path):
    return json.loads(path.read_text())


@lru_cache(None)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def build_plan(catalog_path=ROOT / "catalog.json"):
    catalog = read(catalog_path)
    locks = read(ROOT / "sources.lock.json")["sources"]
    families = read(HERE / "families.json")["families"]
    profile = {key: names.split() for names, keys in PROFILES.items() for key in keys}
    if set(profile) != {s["source_id"] for s in locks}:
        raise ValueError("update the source-specific profiles before freezing the catalog")
    suites, groups = {}, []
    counts = Counter()
    paths = set()
    for entry in catalog["evaluation_suites"]:
        path = ROOT / entry["path"]
        suite = read(path)
        key = (suite["id"], suite["version"])
        checks = []
        for cp in suite["checkpoints"]:
            if cp["category"] == "regression":
                checks.append({"id": cp["id"], "issue": cp["issue_id"], "runner": cp["runner"],
                               "required": cp["required"], "case": asset(ROOT / cp["case"])})
                counts[cp["runner"]] += 1
                paths.add(cp["case"])
        if key in suites:
            raise ValueError("duplicate suite " + str(key))
        suites[key] = {**asset(path), "id": key[0], "version": key[1], "groups": suite["group_ids"],
                       "sources": suite["source_ids"], "registered_regressions": checks,
                       "support": [asset(ROOT / x) for x in suite.get("support_files", [])]}
    for entry in catalog["groups"]:
        path = ROOT / entry["path"]
        group = read(path)
        active = group["evaluation_suite"]
        if group["source_id"] not in suites[(active["id"],active["version"])]["sources"]:
            raise ValueError("group / suite source mismatch: " + group["id"])
        groups.append({**asset(path), "group": group["id"], "version": group["version"],
                       "source": group["source_id"], "members": group["members"], "active_suite": active})
    rows = []
    for source in locks:
        identity = source["source_id"]
        tool = ROOT / "toolchains" / (source["toolchain"] + ".json")
        script = ROOT / "tools" / read(tool)["tools_directory"] / "build.sh"
        targets = re.findall(r"--target\s+([A-Za-z0-9]+(?: [A-Za-z0-9]+)*)",script.read_text())
        if not targets:
            raise ValueError("cannot identify build targets: " + str(script))
        targets = sorted(set(t for m in targets for t in m.split()))
        priority = profile[identity]
        if not set(priority) <= set(families):
            raise ValueError("unknown family")
        large = bool({"DRAWEXE", "TKBool", "TKBO", "TKFillet"} & set(targets))
        row_suites = [s for s in suites.values() if identity in s["sources"]]
        rows.append({"source_id": identity, "commit": source["commit"],
            "materialized_tree_sha256": source["materialized_tree_sha256"],
            "toolchain": source["toolchain"], "toolchain_config": asset(tool), "build_entry": asset(script),
            "declared_public_targets": targets, "groups": [g for g in groups if g["source"] == identity],
            "suites": row_suites, "priority_family_designs": priority,
            "cross_module_core": CORE,
            "core_build_policy": "probe_lock_first" if large else "additional_paired_build_required_unless_probe_succeeds",
            "additional_on_change": "families.json: triggers plus dependency fan-out",
            "scheduled_broad_checks": ["exchange", "mesh", "topology"]})
        if identity in OPTIONAL_SPECIALISTS:
            specialist = suites[OPTIONAL_SPECIALISTS[identity]]
            if specialist["sources"] != [identity]:
                raise ValueError("boolean regression source mismatch")
            rows[-1]["boolean_regression_suite"] = {"id": specialist["id"], "version": specialist["version"],
                                                   "checkpoint_ids": [c["id"] for c in specialist["registered_regressions"]]}
    return {"suite": "kernel-regression-v1", "catalog": {"path": "catalog.json", "sha256": sha(catalog_path)},
            "lock": asset(ROOT/"sources.lock.json"), "family_specs_sha256":sha(HERE/"families.json"),
            "probe_sha256":sha(HERE/"probe.cxx"), "oracle_sha256":sha(HERE/"replay.py"),
            "counts":{"source_ids":len(rows), "commits":len({s["commit"] for s in rows}),
                "toolchains":len({s["toolchain"] for s in rows}), "groups":len(groups), "suite_versions":len(suites),
                "registered_regression_refs":sum(counts.values()), "distinct_case_paths":len(paths),
                "registered_runner_counts":dict(counts),
                "suite_versions_without_regression_category":sum(not s["registered_regressions"] for s in suites.values())},
            "sources":rows}


def version_index(plan):
    names = dict(cells="布尔材料归属", intersection="交线与根", pcurve="参数曲线",
                 tolerance="容差传播", topology="拓扑与同域", history="API 历史",
                 partition="分块", offset="偏置", fillet="圆角", projection="点面投影",
                 properties="质量属性", construction="造型")
    lines = ["# 逐版本回归索引", "",
             "每行一个源码身份。题组数含组合题，旧回归列是评分器版本内的引用数。构建目标来自该身份的公开构建脚本，优先补充项为设计。",
             "", "| 源码身份 | 锁定提交 | 公开目标 | 题组 | 旧回归引用 | 优先补充 |",
             "|---|---|---|---:|---:|---|"]
    for row in plan["sources"]:
        n = sum(len(s["registered_regressions"]) for s in row["suites"])
        targets = ", ".join(row["declared_public_targets"])
        added = "、".join(names[k] for k in row["priority_family_designs"])
        lines.append(f"| `{row['source_id']}` | `{row['commit'][:12]}` | {targets} | {len(row['groups'])} | {n} | {added} |")
    for row in plan["sources"]:
        if "boolean_regression_suite" in row:
            suite = row["boolean_regression_suite"]
            lines.extend(["", f"源码 `{row['source_id']}` 的布尔专项使用 `{suite['id']}@{suite['version']}`，"
                          f"与六项通用探针分列。用例为 `{', '.join(suite['checkpoint_ids'])}`。"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    # The original version-plan.json is hash-bound to the first 18 calibration batches.
    ap.add_argument("--output-dir", type=Path, default=HERE / "rollout-v33")
    args = ap.parse_args()
    plan = build_plan()
    outputs = {"version-plan.json": json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
               "versions.md": version_index(plan)}
    for name, content in outputs.items():
        out = args.output_dir / name
        if args.check:
            if out.read_text() != content:
                raise SystemExit(name + " differs from catalog, locks, fixtures or runner")
        else:
            out.write_text(content)
