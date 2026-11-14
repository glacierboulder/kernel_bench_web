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
#include <NCollection_Array1.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <NCollection_IndexedMap.hxx>
#include <fstream>


#include <TopExp.hxx>

#include <TopoDS.hxx>
#include <gp_Circ.hxx>
#include <iostream>
#include <sstream>

namespace {

constexpr double kHeight = 10.0;
double kRadius = 0.35;
constexpr double kWeight = 0.7071067811865476;

// Oval profile as one closed rational quadratic B-spline curve.
Handle(Geom_BSplineCurve) ovalCurve() {
  NCollection_Array1<gp_Pnt> poles(1, 9);
  poles(1) = gp_Pnt(3, 0, 0);    poles(2) = gp_Pnt(3, 2, 0);
  poles(3) = gp_Pnt(0, 2, 0);    poles(4) = gp_Pnt(-3, 2, 0);
  poles(5) = gp_Pnt(-3, 0, 0);   poles(6) = gp_Pnt(-3, -1.5, 0);
  poles(7) = gp_Pnt(0, -1.5, 0); poles(8) = gp_Pnt(3, -1.5, 0);
  poles(9) = gp_Pnt(3, 0, 0);
  NCollection_Array1<double> weights(1, 9);
  for (int i = 1; i <= 9; ++i) weights(i) = (i % 2 == 0) ? kWeight : 1.0;
  NCollection_Array1<double> knots(1, 5);
  for (int i = 1; i <= 5; ++i) knots(i) = i - 1;
  NCollection_Array1<int> mults(1, 5);
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
    NCollection_Array1<gp_Pnt> poles(1, 3);
    poles(1) = corners[s]; poles(2) = middles[s]; poles(3) = corners[s + 1];
    NCollection_Array1<double> weights(1, 3);
    weights(1) = 1.0; weights(2) = kWeight; weights(3) = 1.0;
    NCollection_Array1<double> knots(1, 2);
    knots(1) = 0.0; knots(2) = 1.0;
    NCollection_Array1<int> mults(1, 2);
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
int filletTopRim(const TopoDS_Wire& profile, const char* label) {
  const TopoDS_Shape prism =
      BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(profile, true).Face(),
                            gp_Vec(0, 0, kHeight))
          .Shape();
  BRepFilletAPI_MakeFillet maker(prism);
  NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher> edges;
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
    return 2; // controlled failure
  }
  const TopoDS_Shape result = maker.Shape();

  BRepCheck_Analyzer analyzer(result);
  BRepAlgoAPI_Check interference(result, true, true);
  std::cout << label << ": IsDone=true faultyContours="
            << maker.NbFaultyContours()
            << " BRepCheck=" << (analyzer.IsValid() ? "valid" : "INVALID")
            << " selfInterference="
            << (interference.IsValid() ? "clean" : "FAULTY") << "\n";
  if (analyzer.IsValid() && interference.IsValid()) return 1;

  NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher> faces;
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

int main(int argc,char** argv) {
  if(argc==2) { std::ifstream f(argv[1]); if(!(f>>kRadius) || kRadius<=0 || kRadius>0.35) return 2; }
  const int circle = filletTopRim(circleProfile(), "circle rim");
  const int spline = filletTopRim(singleEdgeProfile(), "closed B-spline rim");
  const int periodic = filletTopRim(periodicProfile(), "periodic B-spline rim");
  const int four = filletTopRim(fourEdgeProfile(), "four-edge rim");
  if(circle==1 && four==1 && periodic==1 && (spline==1 || spline==2)) {
    std::cout << "TEST_DONE\n"; return 0;
  }
  return 1;
}
