"""Analytic material oracles for the two scoped controls, independent of the Boolean or fillet implementation."""
import math

def check(ok,why):
    if not ok:raise ValueError(why)
def close(x,y,t=1.e-6):
    return abs(x-y)<=t
def read_geometry(file):
    rows={}
    for line in file.read_text().splitlines():
        fields=line.split()
        if fields and fields[0] in {'SOLID','FACE','VERTEX','SEG','MATERIAL','PLANE','RIM','CYL','TORUS'}:
            values=list(map(float,fields[1:]))
            check(all(map(math.isfinite,values)),file.name)
            rows.setdefault(fields[0],[]).append(values)
    return rows

def material(rows,oracle):
    misses=[]
    for x,y,z,state in rows['MATERIAL']:
        expected=oracle(x,y,z)
        if state!=(0 if expected else 1):
            misses.append(dict(x=x,y=y,z=z,want='IN' if expected else 'OUT',observed={0:'IN',1:'OUT',2:'ON',3:'UNKNOWN'}.get(state,str(state))))
    return dict(tested=len(rows['MATERIAL']),mismatches=len(misses),examples=misses[:4])
def bounds(rows):
    return [op(v[i] for v in rows['VERTEX']) for op in (min,max) for i in (1,2,3)]

def rectangle_shell(rows,dims):
    """Prove the six planar rectangles are tiled exactly once by the reread single-wire linear trims."""
    lo,hi=dims[:3],dims[3:]
    tiles={(k,h):[] for k in range(3) for h in [0,1]}
    for face in rows['FACE']:
        n,kind,orient,area,wires,edges,lines=face[:7]
        if kind!=0 or wires!=1 or edges!=lines:return False
        plane,=[p for p in rows['PLANE'] if p[0]==n]
        normal=plane[4:7];axis=max(range(3),key=lambda j:abs(normal[j]))
        if abs(abs(normal[axis])-1)>1e-9:return False
        other=[j for j in range(3) if j!=axis]
        pts=[v[1:] for v in rows['VERTEX'] if v[0]==n]
        side=next((s for s in (0,1) if all(close(v[axis],(lo,hi)[s][axis]) for v in pts)),None)
        if side is None:return False
        outward=normal[axis]*(-1 if orient==1 else 1)
        if not close(outward,(-1,1)[side]):return False
        intervals=[(min(v[j] for v in pts),max(v[j] for v in pts)) for j in other]
        if any(a<lo[j]-1e-6 or b>hi[j]+1e-6 for (a,b),j in zip(intervals,other)):return False
        if not close(area,math.prod(b-a for a,b in intervals)):return False
        for seg in (v for v in rows['SEG'] if v[0]==n):
            # Each complete straight edge must occupy a side of the face rectangle.
            if not any(close(seg[2+j],t) and close(seg[5+j],t) for j,extent in zip(other,intervals) for t in extent):return False
        tiles[axis,side].append(intervals)
    for (axis,_),rectangles in tiles.items():
        if not rectangles:return False
        other=[j for j in range(3) if j!=axis]
        cuts=[sorted({lo[j],hi[j],*(u for r in rectangles for u in r[k])}) for k,j in enumerate(other)]
        for a,b in zip(cuts[0],cuts[0][1:]):
            for c,d in zip(cuts[1],cuts[1][1:]):
                if b-a<=1e-8 or d-c<=1e-8:continue
                x=(a+b)/2;y=(c+d)/2
                if sum(l<x<h and m<y<n for ((l,h),(m,n)) in rectangles)!=1:return False
    return True
def in_box(x,y,z,ext):
    return all(a<v<b for a,v,b in zip(ext[:3],[x,y,z],ext[3:]))
def merge_result(rows,dims):
    solid,=rows['SOLID'];mat=material(rows,lambda x,y,z:in_box(x,y,z,dims))
    shell=rectangle_shell(rows,dims)
    return dict(volume=solid[6],surface_area=solid[7],centroid=solid[8:11],faces=int(solid[1]),edges=int(solid[2]),
         bounds=bounds(rows),valid=solid[0]==solid[4]==solid[5]==1,closed_rectangle_shell=shell,
         one_face_per_side=shell and solid[1]==6,material=mat)


def verdict(m):
    dims = [0, 0, 0, 10, 8, 6]
    if not m["valid"]:
        return "invalid"
    if not all(close(a, b) for a, b in zip(m["bounds"], dims)):
        return "displaced"
    if m["volume"] < 480 - 1e-6 and m["material"]["mismatches"]:
        return "material_loss"
    if (not m["closed_rectangle_shell"] or m["material"]["mismatches"]
            or not close(m["volume"], 480) or not close(m["surface_area"], 376)):
        return "geometry_changed"
    if not m["one_face_per_side"]:
        return "seam_residual"
    return "pass"


def main(inputs):
    import hashlib
    import json
    from pathlib import Path
    if len(inputs) != 4:
        raise ValueError("expected the four catalogued control BREPs")
    expected = {"native": "pass", "healthy": "pass", "seam": "seam_residual",
                "shift": "displaced", "notch": "material_loss"}
    matched = True
    for (role, required), filename in zip(expected.items(), ["native.brep", *inputs]):
        rows = read_geometry(Path(role + ".measure"))
        # Make absence or duplication of the frozen material witnesses an execution error.
        grid = {(x,y,z) for x in (-.25,.25,3.5,4.75,5.25,9.75,10.25,11.25)
                for y in (-.25,2.5,6.,8.25) for z in (-.25,1.,5.,6.25)}
        check(len(rows["MATERIAL"]) == len(grid) and
              {tuple(p[:3]) for p in rows["MATERIAL"]} == grid, "incomplete material grid")
        metrics = merge_result(rows, [0,0,0,10,8,6])
        actual = verdict(metrics)
        disposition = "PASS" if actual == "pass" else "REJECT " + actual
        print(("NATIVE" if role == "native" else "CONTROL " + role), disposition)
        print("EVIDENCE", json.dumps(dict(role=role, observed=actual, metrics=metrics,
              brep_sha256=hashlib.sha256(Path(filename).read_bytes()).hexdigest()),
              separators=(",", ":"), allow_nan=False))
        matched = matched and actual == required
    if matched:
        print("TEST_DONE")
    return 0 if matched else 1


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
