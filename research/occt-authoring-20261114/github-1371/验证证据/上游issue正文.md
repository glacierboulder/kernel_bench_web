### Description

**Affected version:** OCCT 8.0.0.p1 (official tag `V8_0_0_p1`, commit `4f95ecaa`), built from source, shared libraries.
**Platform:** macOS arm64, Apple clang 21. The defect is topological and should not depend on the platform.
**Component:** Modeling Algorithms, `TKFillet` / `BRepFilletAPI_MakeFillet` (`ChFi3d`).

## Summary

`BRepFilletAPI_MakeFillet` accepts the top rim of a prism whose profile is one
closed rational B-spline edge, reports full success, and returns a corrupt
solid. `IsDone()` is true, `NbFaultyContours()` and `NbFaultyVertices()` are 0,
yet `BRepCheck_Analyzer` rejects the result and `BRepAlgoAPI_Check` finds
self-intersections and eight edges below tolerance. The invalid topology
clusters around the seam vertex of the closed spine edge, so the fillet stripe
appears to close incorrectly across the seam.

Three control cases isolate the trigger. A circular rim (also one closed edge)
fillets cleanly. The identical oval geometry authored as four tangent-continuous
arcs joined at real vertices also fillets cleanly. Converting the failing curve
with `SetPeriodic()` changes nothing: the strictly periodic representation
fails with the same signature, so the defect is tied to the closed freeform
spine itself rather than to clamped parameterization.

The silent success is the damaging part. Downstream code that trusts `IsDone()`
feeds the corrupt solid into Boolean operations and export.

## Steps to reproduce

Compile and run the attached `ClosedSplineRimFillet.cpp`:

```
c++ -std=c++17 ClosedSplineRimFillet.cpp -I<occt>/include/opencascade \
  -L<occt>/lib -lTKernel -lTKMath -lTKG2d -lTKG3d -lTKGeomBase -lTKGeomAlgo \
  -lTKBRep -lTKTopAlgo -lTKPrim -lTKBO -lTKBool -lTKShHealing -lTKFillet \
  -o ClosedSplineRimFillet
./ClosedSplineRimFillet
```

The program builds three prisms of height 10 and fillets every top-rim edge
with radius 0.35:

1. a circle of radius 3 (one closed edge);
2. an oval profile as one closed rational quadratic B-spline edge
   (9 poles, knots `[0,1,2,3,4]`, multiplicities `[3,2,2,2,3]`);
3. the same oval as four rational quadratic arcs with vertices at the
   quadrant points.


### Expected Behavior

Either a valid solid, or a reported failure through `IsDone() == false` or a
nonzero faulty-contour count. A result that fails `BRepCheck_Analyzer` should
never be returned as an unqualified success.

### Actual Behavior

```
circle rim: IsDone=true faultyContours=0 BRepCheck=valid selfInterference=clean
closed B-spline rim: IsDone=true faultyContours=0 BRepCheck=INVALID selfInterference=FAULTY
  invalid face #1: BRepCheck_UnorientableShape
  faults: selfIntersect=3 tooSmallEdge=8 other=1
periodic B-spline rim: IsDone=true faultyContours=0 BRepCheck=INVALID selfInterference=FAULTY
  invalid face #1: BRepCheck_UnorientableShape
  faults: selfIntersect=3 tooSmallEdge=8 other=1
four-edge rim: IsDone=true faultyContours=0 BRepCheck=valid selfInterference=clean
BUG REPRODUCED: closed B-spline rim is invalid in both the clamped and SetPeriodic representations, while the identical four-edge geometry and the circle are valid
```

The invalid face is the prism's lateral face, flagged
`BRepCheck_UnorientableShape`. The self-intersections and undersized edges lie
near the closed edge's start point (3, 0, 10), which is the seam of both the
spine edge and the periodic lateral surface.

## Additional observations

- The failure is radius independent. Radii 0.05, 0.1, 0.2, and 0.35 produce
  the same signature on this profile.
- The defect was first observed on a swept solid built with
  `BRepOffsetAPI_MakePipeShell` from the same closed profile. Filleting either
  terminal rim of the sweep fails identically, so the prism is a
  simplification, not a special case.
- Periodicity is not the trigger. The clamped and `SetPeriodic()`
  representations of the same curve fail identically, and both are closed with
  matching tangents at the join.
- Splitting the profile into a multi-edge wire is an effective workaround.

### Sample Code or DRAW Tcl Script

```
// Reproducer for an OCCT defect: BRepFilletAPI_MakeFillet reports success on
// the rim of a prism whose profile is one closed rational B-spline edge, but
// returns a self-intersecting solid with an unorientable face. The identical
// geometry authored as a four-edge wire fillets cleanly, as does a circle.
//
// Build (OCCT 8.0.0.p1 or newer):
//   c++ -std=c++17 ClosedSplineRimFillet.cpp -I<occt>/include/opencascade \
//     -L<occt>/lib -lTKernel -lTKMath -lTKG2d -lTKG3d -lTKGeomBase \
//     -lTKGeomAlgo -lTKBRep -lTKTopAlgo -lTKPrim -lTKBO -lTKBool \
//     -lTKShHealing -lTKFillet -o ClosedSplineRimFillet
#include <BRepAlgoAPI_Check.hxx>
#include <BRepBndLib.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepCheck.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepCheck_Result.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <Bnd_Box.hxx>
#include <Geom_BSplineCurve.hxx>
#include <TColStd_Array1OfInteger.hxx>
#include <TColStd_Array1OfReal.hxx>
#include <TColgp_Array1OfPnt.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <gp_Circ.hxx>
#include <iostream>
#include <sstream>

namespace {

constexpr double kHeight = 10.0;
constexpr double kRadius = 0.35;
constexpr double kWeight = 0.7071067811865476;

// Oval profile as one closed rational quadratic B-spline curve.
Handle(Geom_BSplineCurve) ovalCurve() {
  TColgp_Array1OfPnt poles(1, 9);
  poles(1) = gp_Pnt(3, 0, 0);    poles(2) = gp_Pnt(3, 2, 0);
  poles(3) = gp_Pnt(0, 2, 0);    poles(4) = gp_Pnt(-3, 2, 0);
  poles(5) = gp_Pnt(-3, 0, 0);   poles(6) = gp_Pnt(-3, -1.5, 0);
  poles(7) = gp_Pnt(0, -1.5, 0); poles(8) = gp_Pnt(3, -1.5, 0);
  poles(9) = gp_Pnt(3, 0, 0);
  TColStd_Array1OfReal weights(1, 9);
  for (int i = 1; i <= 9; ++i) weights(i) = (i % 2 == 0) ? kWeight : 1.0;
  TColStd_Array1OfReal knots(1, 5);
  for (int i = 1; i <= 5; ++i) knots(i) = i - 1;
  TColStd_Array1OfInteger mults(1, 5);
  mults(1) = 3; mults(2) = 2; mults(3) = 2; mults(4) = 2; mults(5) = 3;
  return new Geom_BSplineCurve(poles, weights, knots, mults, 2);
}

TopoDS_Wire singleEdgeProfile() {
  return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(ovalCurve()).Edge())
      .Wire();
}

TopoDS_Wire periodicProfile() {
  Handle(Geom_BSplineCurve) curve = ovalCurve();
  curve->SetPeriodic();
  return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(curve).Edge()).Wire();
}

// The same oval as four rational quadratic arcs joined at real vertices.
TopoDS_Wire fourEdgeProfile() {
  const gp_Pnt corners[5] = {gp_Pnt(3, 0, 0), gp_Pnt(0, 2, 0),
                             gp_Pnt(-3, 0, 0), gp_Pnt(0, -1.5, 0),
                             gp_Pnt(3, 0, 0)};
  const gp_Pnt middles[4] = {gp_Pnt(3, 2, 0), gp_Pnt(-3, 2, 0),
                             gp_Pnt(-3, -1.5, 0), gp_Pnt(3, -1.5, 0)};
  BRepBuilderAPI_MakeWire wire;
  for (int s = 0; s < 4; ++s) {
    TColgp_Array1OfPnt poles(1, 3);
    poles(1) = corners[s]; poles(2) = middles[s]; poles(3) = corners[s + 1];
    TColStd_Array1OfReal weights(1, 3);
    weights(1) = 1.0; weights(2) = kWeight; weights(3) = 1.0;
    TColStd_Array1OfReal knots(1, 2);
    knots(1) = 0.0; knots(2) = 1.0;
    TColStd_Array1OfInteger mults(1, 2);
    mults(1) = 3; mults(2) = 3;
    Handle(Geom_BSplineCurve) curve =
        new Geom_BSplineCurve(poles, weights, knots, mults, 2);
    wire.Add(BRepBuilderAPI_MakeEdge(curve).Edge());
  }
  return wire.Wire();
}

TopoDS_Wire circleProfile() {
  gp_Circ circ(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 3.0);
  return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circ).Edge()).Wire();
}

// Fillet every edge lying in the z == kHeight plane and validate the result.
bool filletTopRim(const TopoDS_Wire& profile, const char* label) {
  const TopoDS_Shape prism =
      BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(profile, true).Face(),
                            gp_Vec(0, 0, kHeight))
          .Shape();
  BRepFilletAPI_MakeFillet maker(prism);
  TopTools_IndexedMapOfShape edges;
  TopExp::MapShapes(prism, TopAbs_EDGE, edges);
  for (int i = 1; i <= edges.Extent(); ++i) {
    Bnd_Box box;
    BRepBndLib::Add(edges(i), box);
    double x0, y0, z0, x1, y1, z1;
    box.Get(x0, y0, z0, x1, y1, z1);
    if (z0 > kHeight - 1e-6 && z1 < kHeight + 1e-6) {
      maker.Add(kRadius, TopoDS::Edge(edges(i)));
    }
  }
  maker.Build();
  if (!maker.IsDone()) {
    std::cout << label << ": Build not done\n";
    return false;
  }
  const TopoDS_Shape result = maker.Shape();

  BRepCheck_Analyzer analyzer(result);
  BRepAlgoAPI_Check interference(result, true, true);
  std::cout << label << ": IsDone=true faultyContours="
            << maker.NbFaultyContours()
            << " BRepCheck=" << (analyzer.IsValid() ? "valid" : "INVALID")
            << " selfInterference="
            << (interference.IsValid() ? "clean" : "FAULTY") << "\n";
  if (analyzer.IsValid() && interference.IsValid()) return true;

  TopTools_IndexedMapOfShape faces;
  TopExp::MapShapes(result, TopAbs_FACE, faces);
  for (int i = 1; i <= faces.Extent(); ++i) {
    if (analyzer.IsValid(faces(i))) continue;
    std::ostringstream statuses;
    for (const BRepCheck_Status status : analyzer.Result(faces(i))->Status()) {
      BRepCheck::Print(status, statuses);
    }
    std::string text = statuses.str();
    for (char& c : text) {
      if (c == '\n') c = ' ';
    }
    std::cout << "  invalid face #" << i << ": " << text << "\n";
  }
  int selfIntersections = 0, smallEdges = 0, other = 0;
  for (const BOPAlgo_CheckResult& fault : interference.Result()) {
    switch (fault.GetCheckStatus()) {
      case BOPAlgo_SelfIntersect: ++selfIntersections; break;
      case BOPAlgo_TooSmallEdge: ++smallEdges; break;
      default: ++other; break;
    }
  }
  std::cout << "  faults: selfIntersect=" << selfIntersections
            << " tooSmallEdge=" << smallEdges << " other=" << other << "\n";
  return false;
}

}  // namespace

int main() {
  const bool circleOk = filletTopRim(circleProfile(), "circle rim");
  const bool splineOk = filletTopRim(singleEdgeProfile(), "closed B-spline rim");
  const bool periodicOk = filletTopRim(periodicProfile(), "periodic B-spline rim");
  const bool fourOk = filletTopRim(fourEdgeProfile(), "four-edge rim");
  if (circleOk && fourOk && !splineOk && !periodicOk) {
    std::cout << "BUG REPRODUCED: closed B-spline rim is invalid in both the "
                 "clamped and SetPeriodic representations, while the identical "
                 "four-edge geometry and the circle are valid\n";
  }
  return (splineOk && periodicOk) ? 0 : 1;
}
```


### Operating System

macOS

### Compiler

Clang

### Bitness

64-bit

### OCCT Version

latest

### Additional Files

_No response_