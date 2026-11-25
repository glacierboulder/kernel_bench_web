"""Compare a frozen patch with its own unmodified baseline on the six portable cases."""
import argparse
import json
from pathlib import Path
import re
from replay import CHECKS

IDENTITY = ("source_id", "baseline_commit", "baseline_tree_sha256", "toolchain",
            "files_sha256", "version", "compiler")


def transition(baseline, patched, qualified=True):
    if not qualified:
        return "INCONCLUSIVE"
    return {("PASS", "FAIL"): "NEW_REGRESSION", ("PASS", "PASS"): "PRESERVED",
            ("FAIL", "PASS"): "RECOVERED", ("FAIL", "FAIL"): "BASELINE_FAILURE"}.get(
                (baseline, patched), "INCONCLUSIVE")


def compare(b, p):
    if b.get("role") != "baseline" or p.get("role") != "patched":
        raise ValueError("expected a baseline and a frozen patched run")
    if not re.fullmatch(r"[0-9a-f]{64}", p.get("patch_sha256", "")):
        raise ValueError("patch identity missing")
    if any(not b.get(k) or b[k] != p.get(k) for k in IDENTITY):
        raise ValueError("different build provenance, probe or oracle")
    # Temporary output paths differ between runs. Retain defines, language/ABI flags and toolkit list.
    def build_signature(receipt):
        command = receipt.get("compile_command", [])
        return [part for i, part in enumerate(command)
                if part != "-o" and not (i and command[i-1] == "-o")]
    if not build_signature(b) or build_signature(b) != build_signature(p):
        raise ValueError("probe compile flags or target library set differ")
    rows = {}
    for case in CHECKS:
        left, right = b["cases"].get(case, {}), p["cases"].get(case, {})
        a = left.get("geometry", {}).get("status")
        z = right.get("geometry", {}).get("status")
        calibrated = left.get("expected_fault_rejected") and right.get("expected_fault_rejected")
        state = transition(a, z, calibrated)
        rows[case] = {"baseline": a, "patch": z, "transition": state}
    states = [row["transition"] for row in rows.values()]
    complete = (all(s == "PRESERVED" for s in states)
                and all(x.get("build", {}).get("status") == "PASS" for x in (b,p))
                and p.get("patch_build_exit") == 0)
    result = "FAIL" if "NEW_REGRESSION" in states else ("PASS" if complete else "INCONCLUSIVE")
    return {"scope": "six portable regression fixtures", "source_id": b["source_id"],
            "patch_sha256": p["patch_sha256"], "status": result, "cases": rows}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ("baseline", "patched"):
        ap.add_argument(key, type=Path)
    args = ap.parse_args()
    print(json.dumps(compare(*(json.loads(p.read_text()) for p in (args.baseline, args.patched))),
                     indent=2))
