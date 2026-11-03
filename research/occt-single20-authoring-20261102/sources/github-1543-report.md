### Description

`BRepAlgoAPI_Cut(cylinder, tool)` returns the cylinder unchanged — `IsDone()` true, no errors, no warnings, volume identical to the argument — when the tool is a `BRepOffsetAPI_MakePipeShell` sweep of a circle along a helix that starts inside the cylinder and leaves it through the top planar face. Whether it fails depends only on where the tool crosses the top face relative to the cylinder's seam. `Common` returns empty and `Fuse` returns two solids for the same arguments, i.e. the operands are treated as non-interfering.

Reproduced on OCCT 7.9.3 (native, via cadquery-ocp 7.9.3.1) and OCCT 8.0.1 (native and WebAssembly builds) with identical volumes and face counts. The two files involved are unchanged on the current `IR` (f2929057ea).

**Configuration** (C++ below): cylinder `BRepPrimAPI_MakeCylinder(8, 30)`; helix as a `Geom2d_Line(u = t, v = t·pitch/2π)` on a `Geom_CylindricalSurface(r = 8)`, pitch 2, height 15, one edge, `BRepLib::BuildCurves3d`; tool = `MakePipeShell(helix)` with `SetMode(gp_Dir(0,0,1))`, circle profile r = 0.6, `BRepBuilderAPI_RoundCorner`, `MakeSolid`, translated by DZ along Z.

| DZ | tool exits the top face at | Cut volume | faces | `IntTools_FaceFace(tube, lateral)` curves |
|---|---|---|---|---|
| 15.4 | θ = 108° | 5830.86 | 13 | 20 |
| 15.5 | θ = 90° | 5832.39 | 13 | 20 |
| 16.0 | θ = 0° | 5839.06 | 12 | 20 |
| **16.2** | θ = 324° | **6031.86 (= untouched)** | 19 | **19** |
| **16.4** | θ = 288° | **6031.86** | 18 | **18** |
| **16.6** | θ = 252° | **6031.86** | 18 | **18** |

Rotating the cylinder about Z by 90° or 180° (moving its seam) makes the failing cases succeed with the same tool. A box instead of a cylinder succeeds for every DZ. `SetUseOBB`, `SetRunParallel`, `SetFuzzyValue(1e-6 … 1e-4)`, `SetNonDestructive` and `ShapeUpgrade_ShapeDivideClosed` on either operand do not change the outcome.

**Where it goes wrong** — `BRepAlgoAPI_Section` returns the tool ∩ top-plane curve correctly and completely in the failing cases. In `BOPAlgo_Builder` the tube's lateral face is split into 2 faces instead of 3 (and the result has 2 solids instead of 3): the final segment of one helical tube ∩ cylinder curve — from its last crossing of the cylinder's seam (θ = 0, z = 29.6) to the tool's end cap (θ = 180°, z = 30.6), passing the face boundary z = 30 at θ = 72° — is absent from the whole result, although both of its end vertices exist. `IntTools_FaceFace(tubeFace, cylinderLateralFace)` itself returns 19 curves instead of 20. In the passing case DZ = 16.0 the analogous segment (z 29.4 → 30.4) is returned. The two configurations are mirror images across z = 30 (0.4 below / 0.6 above vs 0.6 below / 0.4 above).

**Root cause** (traced in a debug build of 8.0.1) — two defects, both in IntPatch:

1. In `IntPatch_ImpPrmIntersection::Perform`, `IntPatch_RstInt::PutVertexOnLine` first puts the restriction vertices (face boundary and seam crossings) on each walking line; then `DecomposeResult` splits the lines at the seam of the periodic quadric, and the pieces it builds carry only their two end vertices — the boundary vertex is lost. Downstream, `GeomInt_LineConstructor` (called from `IntTools_FaceFace`) sees each piece as a single part and classifies it by its midpoint: the last piece here runs z 29.6 → 30.6 against a face bounded at z = 30, its midpoint is outside, and the whole piece is discarded together with the part that lies inside the face. The mirror configuration (z 29.4 → 30.4) has its midpoint inside and survives, which is why DZ = 16.0 works and 16.2 does not.
2. In `IntPatch_RstInt::PutVertexOnLine`, for closed surfaces the 2D check that the found point and the line point agree uses `std::abs(U - U1) > tolUClosed`. A walking line that has just crossed the seam carries U on the far side of the period, so a correct intersection point differs by 2π and is rejected (`FindParameter` returns the right parameter; the vertex is then dropped). With the first defect fixed this still loses the boundary vertex whenever the boundary crossing sits within the last part-turn before a seam crossing — e.g. a 60-degree groove profile swept through both end faces of the cylinder, DZ in −5.1 … −4.7: nothing removed, or the whole result vanishes.

**Fix** — a pull request follows: (1) after the decomposition loop at the end of `IntPatch_ImpPrmIntersection::Perform`, run `PutVertexOnLine` again on every resulting walking line; (2) in `IntPatch_RstInt::PutVertexOnLine`, compare the closed-surface parameters modulo the period. With both, all 19 DZ values in 15.0 … 16.8 cut correctly for circle and groove profiles, the groove-through-both-faces scan over DZ −5.3 … +1 is correct everywhere, previously passing values change by ≤ 0.06 mm³ (curves now end exactly on the boundary), and 8 unrelated quadric × B-spline booleans (sphere/cone/torus cut by helical tubes, arc-swept tubes, quadric × quadric) give volumes identical to 7.9.3 to four decimals.

### Expected Behavior

Either the groove is cut (volume ≈ 5841.80 for DZ = 16.2), or the algorithm reports an error or warning.

### Actual Behavior

The cylinder comes back untouched (volume 6031.86, one valid solid) with `IsDone() == true` and no warning. A silent wrong result is the worst outcome for callers: nothing downstream can distinguish it from a tool that lies outside the object.

### Sample Code or DRAW Tcl Script

Build against 7.9 or 8.0 and run; it prints, per DZ, the number of `IntTools_FaceFace` curves between the tube and the cylinder's lateral face and the Cut volume (6031.86 = cylinder untouched). A Python (cadquery-ocp) twin is available on request.

```cpp
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAdaptor_CompCurve.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepGProp.hxx>
#include <BRepLib.hxx>
#include <BRepOffsetAPI_MakePipeShell.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <Geom2d_Line.hxx>
#include <Geom_CylindricalSurface.hxx>
#include <Geom_Surface.hxx>
#include <IntTools_Curve.hxx>
#include <IntTools_FaceFace.hxx>
#include <IntTools_SequenceOfCurves.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <gp_Circ.hxx>
#include <gp_Trsf.hxx>
#include <cmath>
#include <cstdio>
#include <cstdlib>

static const double PITCH = 2, HEIGHT = 15, R = 8, PR = 0.6;

static TopoDS_Wire helix(int nseg) {
  Handle(Geom_CylindricalSurface) cs = new Geom_CylindricalSurface(gp_Ax3(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), R);
  double slope = PITCH / (2 * M_PI);
  double uMax = (HEIGHT / PITCH) * 2 * M_PI * std::sqrt(1 + slope * slope);
  Handle(Geom2d_Line) l = new Geom2d_Line(gp_Pnt2d(0, 0), gp_Dir2d(1, slope));
  BRepBuilderAPI_MakeWire mw;
  for (int i = 0; i < nseg; ++i) mw.Add(BRepBuilderAPI_MakeEdge(l, cs, uMax * i / nseg, uMax * (i + 1) / nseg).Edge());
  TopoDS_Wire w = mw.Wire();
  if (!BRepLib::BuildCurves3d(w, 1e-6, GeomAbs_C1, 14, 2000)) { std::puts("BuildCurves3d failed"); std::exit(1); }
  return w;
}

static TopoDS_Shape tool(double dz, int nseg) {
  TopoDS_Wire spine = helix(nseg);
  BRepAdaptor_CompCurve cc(spine); gp_Pnt p; gp_Vec v; cc.D1(cc.FirstParameter(), p, v);
  gp_Dir t(v); gp_Dir x(gp_Vec(t.XYZ()).Crossed(gp_Vec(0, 0, 1)));
  TopoDS_Wire prof = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(p, t, x), PR)).Edge()).Wire();
  BRepOffsetAPI_MakePipeShell mk(spine);
  mk.SetMode(gp_Dir(0, 0, 1));
  mk.SetTransitionMode(BRepBuilderAPI_RoundCorner);
  mk.Add(prof); mk.Build(); if (!mk.IsDone()) { std::puts("sweep failed"); std::exit(1); }
  mk.MakeSolid();
  gp_Trsf tr; tr.SetTranslation(gp_Vec(0, 0, dz));
  return BRepBuilderAPI_Transform(mk.Shape(), tr, true).Shape();
}

static double volume(const TopoDS_Shape& s) { GProp_GProps g; BRepGProp::VolumeProperties(s, g); return g.Mass(); }

int main(int argc, char** argv) {
  int nseg = argc > 1 ? std::atoi(argv[1]) : 1;
  double dzs[] = {16.0, 16.2, 16.6};
  for (double dz : dzs) {
    TopoDS_Shape cyl = BRepPrimAPI_MakeCylinder(R, 30.0).Shape();
    TopoDS_Shape tl = tool(dz, nseg);
    TopoDS_Face lat, tube;
    for (TopExp_Explorer e(cyl, TopAbs_FACE); e.More(); e.Next())
      if (BRep_Tool::Surface(TopoDS::Face(e.Current()))->IsKind(STANDARD_TYPE(Geom_CylindricalSurface))) lat = TopoDS::Face(e.Current());
    TopExp_Explorer te(tl, TopAbs_FACE); tube = TopoDS::Face(te.Current());
    IntTools_FaceFace ff; ff.SetParameters(true, true, true, 1e-7); ff.Perform(tube, lat);
    const IntTools_SequenceOfCurves& L = ff.Lines();
    BRepAlgoAPI_Cut cut(cyl, tl);
    std::printf("DZ=%.1f  FaceFace curves=%d  cut volume=%.2f (%s)
", dz, L.Length(), volume(cut.Shape()),
                volume(cut.Shape()) < 6031.8 ? "cut" : "NOTHING REMOVED");
    for (int i = 1; i <= L.Length(); ++i) {
      Handle(Geom_Curve) c = L(i).Curve(); if (c.IsNull()) continue;
      gp_Pnt a = c->Value(c->FirstParameter()), b = c->Value(c->LastParameter());
      if (a.Z() > 29 || b.Z() > 29)
        std::printf("   top-region curve %2d: theta %6.1f -> %6.1f  z %.3f -> %.3f
", i,
                    std::fmod(std::atan2(a.Y(), a.X()) * 180 / M_PI + 360, 360), std::fmod(std::atan2(b.Y(), b.X()) * 180 / M_PI + 360, 360), a.Z(), b.Z());
    }
  }
  return 0;
}
```

### Operating System

Linux (Debian 13, x86-64)

### Compiler

GCC 14 (native 8.0.1 and 7.9.3), Emscripten/Clang (WebAssembly 8.0.1) — same result

### Bitness

64-bit

### OCCT Version

7.9.3 and 8.0.1 (the affected code is unchanged on current IR)
