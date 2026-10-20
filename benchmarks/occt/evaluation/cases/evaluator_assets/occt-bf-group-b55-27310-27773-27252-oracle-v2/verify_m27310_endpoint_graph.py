#!/usr/bin/env python3
"""Recheck M27310 regression logs with a seam-independent physical oracle.

This is an addendum verifier. It reads frozen logs only and leaves the v1
verifier and its result matrix untouched.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import defaultdict, deque
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOGS = HERE / "logs"
RESULTS = HERE / "results"
OUTPUT = RESULTS / "m27310_regression_endpoint_graph_review.json"
R1 = 5.0
R2 = 4.0
RADIAL_TOL = 1e-4
ENDPOINT_TOL = 1e-3
WINDING_TOL_TURNS = 0.01


Point = tuple[float, float, float]
Curves = dict[int, list[Point]]


class EvidenceError(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def distance(a: Point, b: Point) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


_FATAL_DIAGNOSTICS = re.compile(
    r"(?:"
    r"\bDRAW\s+function\s+failed\b|"
    r"\b(?:invalid command name|unknown command|wrong # args)\b|"
    r"\bcan't read\b|\bcouldn't (?:open|read|load)\b|"
    r"\bno such file or directory\b|"
    r"\bwhile executing\b|\binvoked from within\b|"
    r"\bBF_ORACLE_EVAL_ERROR\s*=|\bStandard_[A-Za-z0-9_]+Exception\b|"
    r"\bError\s*:"
    r")",
    re.IGNORECASE,
)
_EXPECTED_B_M27773_EMPTY_ASSERTION = (
    'Error :  is WRONG because number of VERTEX entities in shape "result" is 0'
)


def check_draw_log(text: str, role: str, case: str) -> None:
    """Reject command/evaluation failures even when the shell rc is zero.

    One existing B/M27773 neighborhood log has the exact checknbshapes
    mismatch that is itself its recorded geometric failure. That one line is
    allowed only for that exact role/case; all other Error diagnostics fail.
    """
    require("DRAW is running in batch mode" in text, f"DRAW did not start: {role}/{case}")
    case_markers = re.findall(r"^BF_CASE=(.+)$", text, re.MULTILINE)
    require(len(case_markers) == 1, f"missing/duplicate case marker: {role}/{case}")
    rc_markers = re.findall(r"^BF_DRAW_RC=(-?\d+)$", text, re.MULTILINE)
    require(rc_markers == ["0"], f"DRAW return marker missing, nonzero, or duplicated: {role}/{case}")
    require(text.rstrip().endswith("BF_DRAW_RC=0"), f"return marker is not final: {role}/{case}")

    diagnostics = []
    for line in text.splitlines():
        if not _FATAL_DIAGNOSTICS.search(line):
            continue
        if (
            role == "B"
            and case == "m27773_neighborhood"
            and line.strip() == _EXPECTED_B_M27773_EMPTY_ASSERTION
        ):
            continue
        diagnostics.append(line)
    require(not diagnostics, f"DRAW/Tcl/oracle diagnostic present: {role}/{case}: {diagnostics[:2]}")


def parse_samples(text: str, role: str, case: str) -> Curves:
    require("BF_TCL_SAMPLING_COMPLETE=1" in text, f"sampling incomplete: {role}/{case}")
    values: dict[int, list[tuple[int, Point]]] = defaultdict(list)
    pattern = re.compile(
        r"^BF_CURVE_(\d+)_SAMPLE_(\d+)=([^,]+),([^,]+),([^\s]+)$", re.MULTILINE
    )
    for match in pattern.finditer(text):
        point = tuple(float(match.group(i)) for i in (3, 4, 5))
        require(all(math.isfinite(x) for x in point), f"non-finite sample: {role}/{case}")
        values[int(match.group(1))].append((int(match.group(2)), point))
    require(bool(values), f"no curve samples parsed: {role}/{case}")
    curves: Curves = {}
    for curve_id, indexed in values.items():
        indexed.sort(key=lambda item: item[0])
        require(
            [index for index, _ in indexed] == list(range(17)),
            f"incomplete/duplicate sample indices: {role}/{case}/curve{curve_id}",
        )
        curves[curve_id] = [point for _, point in indexed]
    count_match = re.search(r"^BF_CURVE_COUNT=(\d+)$", text, re.MULTILINE)
    require(count_match is not None, f"curve count marker missing: {role}/{case}")
    require(int(count_match.group(1)) == len(curves), f"curve count/sample mismatch: {role}/{case}")
    return curves


def _cluster_endpoints(curves: Curves) -> tuple[dict[int, tuple[int, int]], dict[int, list[int]]]:
    edge_ids = sorted(curves)
    endpoints: list[Point] = []
    edge_endpoint_indices: dict[int, tuple[int, int]] = {}
    for edge_id in edge_ids:
        edge_endpoint_indices[edge_id] = (len(endpoints), len(endpoints) + 1)
        endpoints.extend((curves[edge_id][0], curves[edge_id][-1]))

    parent = list(range(len(endpoints)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(endpoints)):
        for j in range(i + 1, len(endpoints)):
            if distance(endpoints[i], endpoints[j]) <= ENDPOINT_TOL:
                union(i, j)

    root_ids: dict[int, int] = {}
    node_for_index: dict[int, int] = {}
    for index in range(len(endpoints)):
        root = find(index)
        node_for_index[index] = root_ids.setdefault(root, len(root_ids))

    edge_nodes = {
        edge_id: (node_for_index[pair[0]], node_for_index[pair[1]])
        for edge_id, pair in edge_endpoint_indices.items()
    }
    adjacency: dict[int, list[int]] = defaultdict(list)
    for edge_id, (a, b) in edge_nodes.items():
        adjacency[a].append(edge_id)
        adjacency[b].append(edge_id)
    return edge_nodes, adjacency


def _endpoint_components(
    curves: Curves,
) -> tuple[list[dict[str, object]], dict[int, tuple[int, int]], dict[int, list[int]]]:
    edge_nodes, adjacency = _cluster_endpoints(curves)
    remaining = set(curves)
    components: list[dict[str, object]] = []
    while remaining:
        seed = min(remaining)
        pending_edges = [seed]
        component_edges: set[int] = set()
        component_nodes: set[int] = set()
        while pending_edges:
            edge_id = pending_edges.pop()
            if edge_id in component_edges:
                continue
            component_edges.add(edge_id)
            remaining.discard(edge_id)
            for node in edge_nodes[edge_id]:
                component_nodes.add(node)
                pending_edges.extend(e for e in adjacency[node] if e not in component_edges)
        degrees = {node: len(adjacency[node]) for node in component_nodes}
        components.append(
            {
                "edges": sorted(component_edges),
                "nodes": sorted(component_nodes),
                "degrees": degrees,
            }
        )
    return components, edge_nodes, adjacency


def _component_winding(
    component_edges: list[int],
    curves: Curves,
    edge_nodes: dict[int, tuple[int, int]],
    adjacency: dict[int, list[int]],
) -> float:
    start_edge = component_edges[0]
    start_node = edge_nodes[start_edge][0]
    current_node = start_node
    used: set[int] = set()
    ordered_points: list[Point] = []
    while True:
        choices = sorted(set(e for e in adjacency[current_node] if e in component_edges and e not in used))
        if not choices:
            require(current_node == start_node and used == set(component_edges), "endpoint walk did not close")
            break
        if not used:
            require(start_edge in choices, "chosen start edge is not incident to the start node")
            edge_id = start_edge
        else:
            require(len(choices) == 1, f"endpoint walk is ambiguous at node {current_node}: {choices}")
            edge_id = choices[0]
        node_a, node_b = edge_nodes[edge_id]
        if node_a == current_node:
            points = curves[edge_id]
            next_node = node_b
        else:
            require(node_b == current_node, "endpoint incidence mismatch")
            points = list(reversed(curves[edge_id]))
            next_node = node_a
        if ordered_points:
            gap = distance(ordered_points[-1], points[0])
            require(gap <= ENDPOINT_TOL, f"joined sample endpoints exceed tolerance: {gap}")
            ordered_points.extend(points[1:])
        else:
            ordered_points.extend(points)
        used.add(edge_id)
        current_node = next_node
        if current_node == start_node:
            require(used == set(component_edges), "cycle returned to start before consuming all edges")
            break
    require(len(ordered_points) >= 3, "closed component has too few samples")
    ordered_points.append(ordered_points[0])
    angles = [math.atan2(z, y) for _, y, z in ordered_points]
    total = 0.0
    for a, b in zip(angles, angles[1:]):
        delta = (b - a + math.pi) % (2.0 * math.pi) - math.pi
        total += delta
    return total / (2.0 * math.pi)


def verify_geometry(curves: Curves, *, second_radius: float = R2) -> dict[str, object]:
    require(bool(curves), "no curves")
    curve_sign: dict[int, str] = {}
    radial_residuals: list[float] = []
    wrong_radius_residuals: list[float] = []
    for curve_id, points in curves.items():
        require(len(points) >= 2, f"curve {curve_id} has fewer than two samples")
        xs = [point[0] for point in points]
        require(min(abs(x) for x in xs) >= 3.0 - RADIAL_TOL, f"curve {curve_id} leaves analytic x branch")
        if min(xs) > 0:
            sign = "positive_x"
        elif max(xs) < 0:
            sign = "negative_x"
        else:
            raise EvidenceError(f"curve {curve_id} crosses x=0 or mixes branches")
        curve_sign[curve_id] = sign
        for x, y, z in points:
            r1_residual = abs(math.hypot(x, y) - R1)
            r2_residual = abs(math.hypot(y, z) - second_radius)
            radial_residuals.extend((r1_residual, r2_residual))
            if second_radius != R2:
                wrong_radius_residuals.append(r2_residual)
            require(abs(x) <= 6.0 + RADIAL_TOL and abs(z) <= 6.0 + RADIAL_TOL, "sample leaves finite cylinder axial trims")
            require(abs(y) <= 4.0 + RADIAL_TOL, "sample leaves analytic intersection y range")
    max_residual = max(radial_residuals)
    require(max_residual <= RADIAL_TOL, f"cylinder residual exceeds {RADIAL_TOL}: {max_residual}")

    components, edge_nodes, adjacency = _endpoint_components(curves)
    require(len(components) == 2, f"expected two endpoint-connected components, got {len(components)}")
    component_results = []
    signs_seen: set[str] = set()
    for component in components:
        edges = component["edges"]
        nodes = component["nodes"]
        degrees = component["degrees"]
        require(all(degree == 2 for degree in degrees.values()), f"component endpoint graph is not a cycle: degrees={degrees}")
        require(len(edges) == len(nodes), f"component graph cycle rank is not one: E={len(edges)} V={len(nodes)}")
        signs = {curve_sign[edge_id] for edge_id in edges}
        require(len(signs) == 1, f"one endpoint component mixes x branches: {sorted(signs)}")
        sign = next(iter(signs))
        require(sign not in signs_seen, f"duplicate component for branch {sign}")
        signs_seen.add(sign)
        winding = _component_winding(edges, curves, edge_nodes, adjacency)
        require(
            abs(abs(winding) - 1.0) <= WINDING_TOL_TURNS,
            f"component does not make one closed y-z revolution: winding={winding}",
        )
        component_results.append(
            {
                "branch": sign,
                "curve_ids_observed": edges,
                "endpoint_node_count": len(nodes),
                "all_endpoint_degrees_two": True,
                "winding_turns_about_yz_origin": winding,
            }
        )
    require(signs_seen == {"positive_x", "negative_x"}, f"expected one loop per x branch, got {sorted(signs_seen)}")
    return {
        "status": "pass",
        "curve_piece_count_observed_only": len(curves),
        "component_count": len(components),
        "components": component_results,
        "max_two_cylinder_radial_residual_model_units": max_residual,
        "radial_tolerance_model_units": RADIAL_TOL,
        "endpoint_cluster_tolerance_model_units": ENDPOINT_TOL,
        "x_branch_min_abs_bound": 3.0 - RADIAL_TOL,
    }


def expect_rejected(callable_, fragment: str) -> str:
    try:
        callable_()
    except EvidenceError as error:
        message = str(error)
        require(fragment.lower() in message.lower(), f"negative control failed for an unexpected reason: {message}")
        return message
    raise EvidenceError(f"negative control unexpectedly accepted; expected {fragment!r}")


def inject_before_return_marker(text: str, diagnostic: str) -> str:
    marker = "\nBF_DRAW_RC=0"
    require(text.count(marker) == 1, "test fixture must contain exactly one final zero return marker")
    return text.replace(marker, "\n" + diagnostic + marker, 1)


def _read_raw(role: str) -> tuple[Path, str]:
    case = "m27310_regression"
    path = LOGS / f"{role}_{case}.log"
    require(path.is_file(), f"missing raw log: {path}")
    text = path.read_text(encoding="utf-8", errors="strict")
    check_draw_log(text, role, case)
    return path, text


def run_review() -> dict[str, object]:
    logs: dict[str, dict[str, object]] = {}
    curve_data: dict[str, Curves] = {}
    for role in ("B", "F"):
        path, text = _read_raw(role)
        curves = parse_samples(text, role, "m27310_regression")
        geometry = verify_geometry(curves)
        logs[role] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "draw_return_code": 0,
            "geometry": geometry,
        }
        curve_data[role] = curves

    # A deliberately wrong second-cylinder radius must fail against the same raw samples.
    wrong_radius_error = expect_rejected(
        lambda: verify_geometry(curve_data["B"], second_radius=4.5),
        "cylinder residual",
    )

    # Break one positive-loop endpoint to another exact point on both cylinders.
    # This keeps the per-sample equations and branch valid, isolating graph closure.
    broken = {curve_id: list(points) for curve_id, points in curve_data["B"].items()}
    on_surface_endpoint = (math.sqrt(21.0), 2.0, math.sqrt(12.0))
    require(abs(math.hypot(on_surface_endpoint[0], on_surface_endpoint[1]) - 5.0) < 1e-12, "broken endpoint x/y is off cylinder 1")
    require(abs(math.hypot(on_surface_endpoint[1], on_surface_endpoint[2]) - 4.0) < 1e-12, "broken endpoint y/z is off cylinder 2")
    broken[2][-1] = on_surface_endpoint
    broken_endpoint_error = expect_rejected(lambda: verify_geometry(broken), "endpoint graph is not a cycle")

    # Recheck process/log classification across all twelve saved runs, without rerunning DRAW.
    raw_log_checks = []
    for path in sorted(LOGS.glob("*.log")):
        name = path.stem
        role, case = name.split("_", 1)
        text = path.read_text(encoding="utf-8", errors="strict")
        check_draw_log(text, role, case)
        raw_log_checks.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "accepted": True})

    sample = _read_raw("B")[1]
    parser_negative_controls = {}
    for label, diagnostic in (
        ("draw_function_failure", "DRAW function failed while evaluating cvalue"),
        ("invalid_command", "invalid command name \"cvalue_missing\""),
        ("tcl_error_stack", "while executing\n\"bad_command\""),
        ("generic_error_with_zero_rc", "Error: failed to evaluate geometric oracle"),
    ):
        parser_negative_controls[label] = expect_rejected(
            lambda diagnostic=diagnostic: check_draw_log(
                inject_before_return_marker(sample, diagnostic), "B", "m27310_regression"
            ),
            diagnostic.splitlines()[0].split(":")[0],
        )

    old_verifier = HERE / "verify_calibration.py"
    old_matrix = RESULTS / "hidden_calibration_matrix.json"
    return {
        "review_version": "m27310-physical-loop-oracle-v2",
        "scope": "read-only re-verification of the saved M27310 regression DRAW logs; no DRAW invocation",
        "physical_oracle": {
            "support_equations": ["x^2 + y^2 = 25", "y^2 + z^2 = 16"],
            "components": "two closed connected components, one with x >= 3 and one with x <= -3",
            "representation_independent_checks": [
                "every sampled point satisfies both support-cylinder equations",
                "each observed curve remains on exactly one x-sign branch",
                "endpoint clustering at 1e-3 creates exactly two connected cycle graphs",
                "each graph component has degree 2 at every node and cycle rank 1",
                "ordered sampled component winds once around the y-z circle",
            ],
            "not_a_gate": "observed curve-piece count and seam coordinates; retained only as run metadata",
        },
        "runs": logs,
        "negative_controls": {
            "wrong_second_radius_4_5": {"result": "rejected", "reason": wrong_radius_error},
            "broken_endpoint_to_other_valid_support_point": {
                "result": "rejected",
                "replacement_point": list(on_surface_endpoint),
                "per_sample_equations_remain_valid": True,
                "reason": broken_endpoint_error,
            },
        },
        "draw_log_classifier": {
            "raw_logs_checked_without_reexecution": len(raw_log_checks),
            "accepted_raw_logs": raw_log_checks,
            "expected_geometry_assertion_exception": {
                "role": "B",
                "case": "m27773_neighborhood",
                "exact_line": _EXPECTED_B_M27773_EMPTY_ASSERTION,
                "meaning": "previously reported completed empty section; not treated as a command failure",
            },
            "synthetic_command_error_negative_controls": parser_negative_controls,
            "boundary": "log markers and diagnostics improve classification, but do not authenticate the trusted DRAW binary or prove the geometric oracle beyond the recorded samples",
        },
        "preserved_v1_evidence": {
            "verifier_path": str(old_verifier.relative_to(ROOT)),
            "verifier_sha256": sha256(old_verifier),
            "matrix_path": str(old_matrix.relative_to(ROOT)),
            "matrix_sha256": sha256(old_matrix),
        },
    }


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    report = run_review()
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"M27310 B/F raw-log physical loop oracle: pass ({len(report['runs'])} saved runs)")
    print("negative controls: wrong radius rejected; broken endpoint rejected")
    print(f"process classifier: {report['draw_log_classifier']['raw_logs_checked_without_reexecution']} saved logs checked; command-error injections rejected")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"verification failed: {error}", file=sys.stderr)
        sys.exit(1)
