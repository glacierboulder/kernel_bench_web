// Geometry measured by the kernel. The expected values live separately in replay.py.
#include <BRepAlgoAPI_Common.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepAlgoAPI_Section.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <gp_Pln.hxx>
#include <algorithm>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

static void metric(const char* name, double value) {
  std::cout << name << " " << value << "\n";
}
static TopoDS_Shape box(double x, double length = 10.) {
  return BRepPrimAPI_MakeBox(gp_Pnt(x, 0, 0), length, 10, 10).Shape();
}
static void properties(const TopoDS_Shape& shape) {
  if (shape.IsNull()) throw std::runtime_error("null shape");
  TopTools_IndexedMapOfShape solids;
  TopExp::MapShapes(shape, TopAbs_SOLID, solids);
  GProp_GProps prop;
  BRepGProp::VolumeProperties(shape, prop);
  metric("valid", BRepCheck_Analyzer(shape).IsValid());
  metric("solids", solids.Extent());
  metric("volume", prop.Mass());
  if (solids.Extent()) metric("cx", prop.CentreOfMass().X());
}
static void throughHole(const std::string& id, bool fault) {
  const TopoDS_Shape base = box(0);
  const gp_Ax2 axis(gp_Pnt(5,5,-1), gp_Dir(0,0,1));
  TopoDS_Shape out = BRepAlgoAPI_Cut(base, BRepPrimAPI_MakeCylinder(axis,2,12).Shape()).Shape();
  if (id == "brep-roundtrip") {
    BRepTools::Write(out, "shape.brep");
    if (fault) BRepTools::Write(base, "shape.brep");
    BRep_Builder builder;
    out.Nullify();
    if (!BRepTools::Read(out, "shape.brep", builder)) throw std::runtime_error("BREP read failed");
  } else if (fault) {
    // Same removed volume, same topology and x-centroid; hole moved along y.
    const gp_Ax2 moved(gp_Pnt(5,7,-1), gp_Dir(0,0,1));
    out = BRepAlgoAPI_Cut(base,BRepPrimAPI_MakeCylinder(moved,2,12).Shape()).Shape();
  }
  properties(out);
  BRepClass3d_SolidClassifier hole(out, gp_Pnt(5,4,5), 1.e-7);
  BRepClass3d_SolidClassifier wall(out, gp_Pnt(5,7.5,5), 1.e-7);
  metric("hole_out", hole.State() == TopAbs_OUT);
  metric("wall_in", wall.State() == TopAbs_IN);
}
static void section(bool fault) {
  const TopoDS_Shape sphere = BRepPrimAPI_MakeSphere(5.).Shape();
  // The displaced plane yields an equally valid, closed, but incorrect circle.
  BRepAlgoAPI_Section cut(sphere, gp_Pln(gp_Pnt(0,0,fault ? 3. : 0.),gp_Dir(0,0,1)));
  if (!cut.IsDone()) throw std::runtime_error("section failed");
  const TopoDS_Shape shape = cut.Shape();
  GProp_GProps prop;
  BRepGProp::LinearProperties(shape, prop);
  metric("length", prop.Mass());
  metric("valid", BRepCheck_Analyzer(shape).IsValid());
  const gp_Pnt anchors[] = {gp_Pnt(5,0,0),gp_Pnt(-5,0,0),gp_Pnt(0,5,0),gp_Pnt(0,-5,0)};
  double worst = 0.;
  for (const auto& point : anchors) {
    BRepExtrema_DistShapeShape dist(BRepBuilderAPI_MakeVertex(point).Shape(),shape);
    if (!dist.IsDone()) throw std::runtime_error("witness distance unavailable");
    worst = std::max(worst, dist.Value());
  }
  metric("witness_distance", worst);
}
int main(int argc, char** argv) {
  if (argc != 3) return 2;
  const std::string id = argv[1];
  const bool fault = std::string(argv[2]) == "negative";
  std::cout << std::setprecision(17);
  try {
    if (id == "box-common") {
      const TopoDS_Shape a = box(0), b = box(fault ? -5. : 5.);
      properties(BRepAlgoAPI_Common(a,b).Shape());
      GProp_GProps swapped;
      BRepGProp::VolumeProperties(BRepAlgoAPI_Common(b,a).Shape(),swapped);
      metric("swapped_volume", swapped.Mass());
      metric("swapped_cx", swapped.CentreOfMass().X());
    } else if (id == "disjoint") {
      properties(BRepAlgoAPI_Common(box(0),box(fault ? 9. : 12.)).Shape());
    } else if (id == "cut-fuse") {
      const TopoDS_Shape a = box(0), b = box(5);
      properties(BRepAlgoAPI_Cut(a,b).Shape());
      const TopoDS_Shape fused = fault ? a : BRepAlgoAPI_Fuse(a,b).Shape();
      GProp_GProps prop;
      BRepGProp::VolumeProperties(fused,prop);
      metric("fused_volume",prop.Mass());
      metric("fused_valid", BRepCheck_Analyzer(fused).IsValid());
    } else if (id == "plane-sphere") section(fault);
    else if (id == "hole-classification" || id == "brep-roundtrip") throughHole(id,fault);
    else return 2;
    return 0;
  } catch (const Standard_Failure& err) {
    std::cerr << err.GetMessageString() << "\n";
  } catch (const std::exception& err) {
    std::cerr << err.what() << "\n";
  }
  return 1;
}
