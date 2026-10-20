#!/usr/bin/env python3
"""Case-specific G3 geometry predicates over this invocation's raw DRAW output."""
from __future__ import annotations
import hashlib, math, re

_SOFT_FAILURE_RE = re.compile(
    r"^\s*(?:Call of function\b.*\bfailed\b|"
    r"(?:DRAW\s+)?function\b.*\bfailed\b|"
    r"DRAW\s+command\b.*\bfailed\b|"
    r"unknown\s+(?:command|function|variable)\b|"
    r"invalid command name\b|command not found\b)", re.I | re.M)
_ORACLE_ERROR_RE = re.compile(r"^BF_ORACLE_EVAL_ERROR\s*[:=]", re.M)
_OFFICIAL_GEOMETRY_ERRORS = {
    "M21494_original": "Error: 1 curves is expected but 0 ones are found",
    "M27780_original": "Error: p-curve has reversed direction at its end",
}

def _result(case_id, passed, detail):
    return {"status":"geometry_pass" if passed else "geometry_fail",
            "checks":[{"id":"geometry_predicate","passed":bool(passed)}],"detail":detail}

def _one(text, pattern, label):
    found=re.findall(pattern,text,re.M)
    if len(found)!=1: raise ValueError(f"{label}: expected exactly one marker, got {len(found)}")
    return found[0]

def _source_rc(text):
    return int(_one(text,r"^BF_SOURCE_RC=(\d+)$","source return code"))

def _common(case_id,text,draw_rc,need_source_rc=None):
    if draw_rc!=0: raise ValueError(f"DRAW returned {draw_rc}; geometry oracle not run")
    if "DRAW is running in batch mode" not in text: raise ValueError("DRAW did not start in batch mode")
    if text.count(f"BF_HARNESS_CASE={case_id}")!=1 or text.count("BF_HARNESS_COMPLETED=1")!=1:
        raise ValueError("frozen harness completion markers missing or duplicated")
    missing=re.findall(r"^BF_REQUIRED_COMMANDS_MISSING=(.*)$",text,re.M)
    if missing and (len(missing)!=1 or missing[0].strip()): raise ValueError("required DRAW commands are missing")
    if _ORACLE_ERROR_RE.search(text): raise ValueError("oracle Tcl/Python evaluation error")
    if _SOFT_FAILURE_RE.search(text): raise ValueError("DRAW function/command failure diagnostic")
    source_errors=re.findall(r"^BF_SOURCE_ERROR=(.*)$",text,re.M)
    if len(source_errors)>1: raise ValueError("raw Tcl source error field duplicated")
    source_rc=_source_rc(text)
    if source_rc!=0 and len(source_errors)!=1:
        raise ValueError("raw Tcl source error field missing")
    if source_errors and source_errors[0]:
        # M27252 baseline has a later unset NbCurv read after its official BOP
        # log already establishes an empty-curve geometry failure. This exact
        # source error is case-scoped and is validated again by its parser.
        allowed=(case_id=="M27252_original" and
                 source_errors[0]=='can\'t read "NbCurv": no such variable')
        if not allowed: raise ValueError("unapproved raw Tcl source error")
    for line in re.findall(r"^Error\s*:[^\n]*$",text,re.M):
        if line not in {_OFFICIAL_GEOMETRY_ERRORS.get(case_id)}:
            raise ValueError(f"unapproved DRAW error diagnostic: {line}")
    if need_source_rc is not None and source_rc!=need_source_rc:
        raise ValueError(f"unexpected raw Tcl source return code {source_rc}")
    return source_rc

def _bop_log(text):
    m=re.search(r"^BF_OFFICIAL_BOP_LOG_BEGIN\n(.*?)\nBF_OFFICIAL_BOP_LOG_END$",text,re.M|re.S)
    if not m: raise ValueError("official BOP log block missing")
    return m.group(1)

def _var(text,name):
    return _one(text,rf"^BF_VAR_{re.escape(name)}=(.*)$",f"variable {name}").strip()

def _samples(text, prefix="BF_CURVE"):
    if "BF_TCL_SAMPLING_COMPLETE=1" not in text: raise ValueError("Tcl sampling did not complete")
    pat=re.compile(r"^"+re.escape(prefix)+r"_(\d+)_SAMPLE_(\d+)=([^,]+),([^,]+),([^\s]+)$",re.M)
    raw={}
    for m in pat.finditer(text):
        idx,seq=int(m.group(1)),int(m.group(2))
        pt=tuple(float(m.group(i)) for i in (3,4,5))
        if not all(math.isfinite(x) for x in pt): raise ValueError("non-finite sampled point")
        raw.setdefault(idx,[]).append((seq,pt))
    out={}
    for idx,items in raw.items():
        items.sort()
        if [n for n,_ in items]!=list(range(17)): raise ValueError(f"incomplete samples for curve {idx}")
        out[idx]=[pt for _,pt in items]
    count=re.search(r"^BF_CURVE_COUNT=(\d+)$",text,re.M)
    if count and int(count.group(1))!=len(out): raise ValueError("curve count/sample mismatch")
    return out

def _m21494_original(role,text):
    if _source_rc(text)!=0: raise ValueError("M21494 original Tcl did not finish")
    fail="Error: 1 curves is expected but 0 ones are found"
    if fail in text:
        if text.count(fail)!=1 or "BF_CASE_ORACLE=fail" not in text:
            raise ValueError("M21494 original failure signature is malformed")
        return _result("M21494_original",False,{"official_predicate":fail,"curve_count":0,"expected_curve_count":1})
    if "BF_CASE_ORACLE=pass" not in text or "TEST_DONE" not in text:
        raise ValueError("M21494 original did not produce an official pass or geometry-fail predicate")
    return _result("M21494_original",True,{"official_predicate":"one intersection curve and official topology/tolerance checks passed"})

def _m27252_original(role,text):
    source_rc=_source_rc(text); log=_bop_log(text)
    empty_curve="has no 3d curves" in log and "has no 3d points" in log
    source_error=re.findall(r"^BF_SOURCE_ERROR=(.*)$",text,re.M)
    if empty_curve:
        exact='can\'t read "NbCurv": no such variable'
        if source_rc!=1 or source_error!=[exact]:
            raise ValueError("M27252 empty-curve failure lacks its exact later NbCurv error")
        if re.search(r"^BF_VAR_NbCurv=",text,re.M): raise ValueError("M27252 B unexpectedly has NbCurv")
        return _result("M27252_original",False,{"observed_curve_count":0,"expected_curve_count":1,
            "official_bop_log_sha256":hashlib.sha256(log.encode()).hexdigest(),
            "later_tcl_error":"can't read NbCurv","geometry_predicate_precedes_error":True,
            "tolerance":"not_evaluated_no_3d_curves"})
    curves=int(_var(text,"NbCurv")); tol=float(_var(text,"Toler"))
    if curves!=1 or tol>1e-7 or "1 curve(s) found" not in log:
        raise ValueError("M27252 original curve/tolerance predicate failed")
    if source_rc==1 and ('procedure "smallview"' not in text or "view 1 $v 728 450 400 400" not in text):
        raise ValueError("M27252 original has an unapproved post-predicate Tcl failure")
    if source_rc not in (0,1): raise ValueError("M27252 original source execution did not complete")
    return _result("M27252_original",True,{"observed_curve_count":curves,"observed_tolerance":tol,
        "maximum_tolerance":1e-7,"later_runtime_error":"smallview view command after geometry predicate"})

def _m27780_original(role,text):
    source_rc=_source_rc(text)
    reversed_marker="Error: p-curve has reversed direction at its end"
    correct_marker="OK: p-curve has correct direction at its end"
    if text.count(reversed_marker)+text.count(correct_marker)!=1: raise ValueError("official p-curve direction predicate missing or duplicated")
    if reversed_marker in text:
        marker=reversed_marker; passed=False
    else:
        marker=correct_marker; passed=True
    if source_rc==1:
        view=text.find("view 1 -2D- 728 450 400 400")
        if view<0 or "while executing" not in text or text.index(marker)>=view:
            raise ValueError("M27780 source failure is not the exact late view tail after geometry")
    elif source_rc!=0:
        raise ValueError("M27780 original source execution did not complete")
    return _result("M27780_original",passed,{"official_predicate":marker,
        "raw_tcl_source_return_code":source_rc,
        "later_runtime_error":"view command" if source_rc==1 else None,
        "predicate_precedes_runtime_error":source_rc==1})

def _m21494_hidden(case_id,role,text,draw_rc):
    _common(case_id,text,draw_rc,0)
    if "BF_HIDDEN_GEOMETRY_ORACLE=pass" not in text or "TEST_DONE" not in text:
        raise ValueError("M21494 analytic oracle did not pass")
    return _result(case_id,True,{"oracle":"locked analytic roots with DRAW-read curve samples","role":role})

def _m27252_hidden(case_id,role,text,draw_rc):
    _common(case_id,text,draw_rc,0)
    curves=_samples(text)
    if set(curves)!={1}: raise ValueError("M27252 hidden oracle requires one sampled curve")
    pts=curves[1]
    if case_id=="M27252_neighbor_translated_plane":
        cx,cy,r=-7.49999999999998,-7.49999999999996,4.99999999999999
        nx,ny,nz=0.0,-0.873177869039721,0.487401691645866
        px,py,pz=12.5,12.5,44.887384
        ends=((-12.5,-7.5,9.0574768),(-7.5,-12.5,0.1))
        radial=[abs(math.hypot(x-cx,y-cy)-r) for x,y,z in pts]
        plane=[abs(nx*(x-px)+ny*(y-py)+nz*(z-pz)) for x,y,z in pts]
        gap=math.dist(pts[0],pts[-1])
        end=min(max(math.dist(pts[0],ends[0]),math.dist(pts[-1],ends[1])),max(math.dist(pts[0],ends[1]),math.dist(pts[-1],ends[0])))
        wrong=[abs(nx*(x-px)+ny*(y-py)+nz*(z-(pz+0.2))) for x,y,z in pts]
        passed=end<=3e-5 and gap>1 and max(radial)<=2e-5 and max(plane)<=2e-5 and min(wrong)>0.09
        return _result(case_id,passed,{"curve_count":1,"sample_count":len(pts),"endpoint_error":end,"endpoint_gap":gap,
            "max_cylinder_radial_residual":max(radial),"max_plane_residual":max(plane),"wrong_plane_offset_min_residual":min(wrong)})
    gap=math.dist(pts[0],pts[-1]); radial=[abs(math.hypot(x,y)-5.0) for x,y,z in pts]
    plane=[abs(z) for x,y,z in pts]; wrong=[abs(math.hypot(x,y)-4.5) for x,y,z in pts]
    passed=gap<=1e-5 and max(radial)<=1e-5 and max(plane)<=1e-5 and min(wrong)>0.49
    return _result(case_id,passed,{"curve_count":1,"sample_count":len(pts),"endpoint_gap":gap,
        "max_cylinder_radial_residual":max(radial),"max_plane_residual":max(plane),"wrong_radius_min_residual":min(wrong)})

def _m27780_neighbor(case_id,role,text,draw_rc):
    _common(case_id,text,draw_rc,0)
    if "BF_TCL_SAMPLING_COMPLETE=1" not in text: raise ValueError("M27780 neighbor samples incomplete")
    matches=re.findall(r"^BF_SAMPLE_(\d+)=([^\n]+)$",text,re.M)
    indexed={}
    for index,raw in matches:
        i=int(index); vals=[float(x) for x in raw.split(",")]
        if len(vals)!=9 or not all(math.isfinite(v) for v in vals): raise ValueError("bad M27780 neighbor sample")
        indexed[i]=vals
    if sorted(indexed)!=list(range(17)): raise ValueError("M27780 neighbor needs 17 synchronized support samples")
    # The observed branch count is metadata. Require the selected branch to exist, but do not gate on a global count.
    count=re.search(r"^BF_CURVE_COUNT=(\d+)$",text,re.M)
    if count is None or int(count.group(1))<1: raise ValueError("selected M27780 branch is missing")
    residual1=max(v[7] for v in indexed.values()); residual2=max(v[8] for v in indexed.values())
    dot=float(_one(text,r"^BF_DIRECTION_DOT=([-+0-9.eE]+)$","endpoint direction"))
    passed=residual1<=1e-5 and residual2<=1e-5 and dot>0
    return _result(case_id,passed,{"sample_count":len(indexed),"max_residual_surface_1":residual1,
        "max_residual_surface_2":residual2,"official_endpoint_direction_dot":dot,
        "mapping_residual_limit_model_units":1e-5,"branch_count_is_global_gate":False,
        "branch_count_observed":int(count.group(1))})

def _m27780_regression(case_id,role,text,draw_rc):
    _common(case_id,text,draw_rc,0)
    if "BF_SHAPE_CHECK_BEGIN" not in text or "BF_SHAPE_CHECK_END" not in text:
        raise ValueError("M27780 finite-face shape checks missing")
    if "number of VERTEX entities is equal to number of expected VERTEX entities" not in text or "number of EDGE entities is equal to number of expected EDGE entities" not in text:
        raise ValueError("M27780 finite-face section is not one edge/two vertices")
    matches=re.findall(r"^BF_SAMPLE_(\d+)=([^\n]+)$",text,re.M); indexed={}
    for index,raw in matches:
        i=int(index); vals=[float(x) for x in raw.split(",")]
        if len(vals)!=9 or not all(math.isfinite(v) for v in vals): raise ValueError("bad M27780 finite-face sample")
        indexed[i]=vals
    if sorted(indexed)!=list(range(17)): raise ValueError("M27780 finite-face sampling incomplete")
    values=list(indexed.values()); ys=[v[1] for v in values]
    residual=max(max(v[7],v[8]) for v in values)
    maxx=max(abs(v[0]) for v in values); maxz=max(abs(v[2]) for v in values)
    endpoint=min(max(abs(ys[0]+5),abs(ys[-1]-5)),max(abs(ys[0]-5),abs(ys[-1]+5)))
    spacing=max(abs((ys[i+1]-ys[i])-0.625) for i in range(16))
    passed=maxx<=1e-7 and maxz<=1e-7 and endpoint<=1e-7 and spacing<=1e-7 and residual<=1e-7
    return _result(case_id,passed,{"sample_count":len(values),"section_edge_count":1,"section_vertex_count":2,
        "max_abs_x":maxx,"max_abs_z":maxz,"max_y_spacing_or_endpoint_error":max(endpoint,spacing),
        "max_pcurve_to_surface_residual":residual,"tolerance_model_units":1e-7})

def validate_draw_text(case_id,role,text,draw_return_code):
    if case_id=="M21494_original":
        _common(case_id,text,draw_return_code,0); return _m21494_original(role,text)
    if case_id=="M27252_original":
        _common(case_id,text,draw_return_code); return _m27252_original(role,text)
    if case_id=="M27780_original":
        _common(case_id,text,draw_return_code); return _m27780_original(role,text)
    if case_id in {"M21494_neighbor_sphere9p5","M21494_regression_cone10_sphere9"}:
        return _m21494_hidden(case_id,role,text,draw_return_code)
    if case_id in {"M27252_neighbor_translated_plane","M27252_regression_cylinder_plane"}:
        return _m27252_hidden(case_id,role,text,draw_return_code)
    if case_id=="M27780_neighbor_translated_face": return _m27780_neighbor(case_id,role,text,draw_return_code)
    if case_id=="M27780_regression_finite_plane": return _m27780_regression(case_id,role,text,draw_return_code)
    raise ValueError(f"unmapped G3 case: {case_id}")
