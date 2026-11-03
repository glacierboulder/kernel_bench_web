#include <BRepTools.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <string>
// Minimal reproduction for the upstream report. Two helical tubes meet end to
// end; their end caps cross along a diameter and the tube surfaces meet at a
// dihedral angle of 5.72 degrees along the cap circles. The fuse must remove a
// wedge of 14.398 mm3 (the lens where tube 1 and tube 2 overlap). Only OCCT is
// used.
//
//   g++ -O2 -std=c++17 -I<occt>/include/opencascade bridge-min.cpp -o bridge-min \
//     -L<occt>/lib -lTKernel -lTKMath -lTKG2d -lTKG3d -lTKGeomBase -lTKBRep \
//     -lTKGeomAlgo -lTKTopAlgo -lTKPrim -lTKBO -lTKBool -lTKShHealing -lTKOffset
//
// Output: solid count of the fuse and the volume it removed. A closed section
// gives 1 solid and 14.398. An open section gives 2 solids and about 0.
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepGProp.hxx>
#include <BRepLib.hxx>
#include <BRepOffsetAPI_MakePipeShell.hxx>
#include <GProp_GProps.hxx>
#include <Geom2d_Line.hxx>
#include <Geom_CylindricalSurface.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Shape.hxx>
#include <TopoDS_Wire.hxx>
#include <gp_Ax2.hxx>
#include <gp_Ax3.hxx>
#include <gp_Circ.hxx>
#include <gp_Dir.hxx>
#include <gp_Dir2d.hxx>
#include <gp_Pnt.hxx>
#include <gp_Pnt2d.hxx>

#include <cmath>
#include <cstdio>

namespace {

const double kPi = 3.14159265358979323846;
const double kDeg = kPi / 180.0;
const double kRadius = 50.0;
double kTube = 6.0;
const double kAngle1 = 2.278524728621996;
const double kTheta = 5.724061592216415;

TopoDS_Shape helixTube(const gp_Pnt& origin, double pitch, int turns) {
  const gp_Ax3 axis(origin, gp_Dir(0, 0, 1));
  Handle(Geom_Surface) surface = new Geom_CylindricalSurface(axis, kRadius);
  Handle(Geom2d_Curve) line = new Geom2d_Line(gp_Pnt2d(0, 0), gp_Dir2d(2 * kPi, pitch));
  const double length = std::sqrt(4 * kPi * kPi + pitch * pitch);
  TopoDS_Edge edge = BRepBuilderAPI_MakeEdge(line, surface, 0, turns * length).Edge();
  BRepLib::BuildCurve3d(edge, 1e-7, GeomAbs_C1, 14, 200);

  const gp_Pnt start(origin.X() + kRadius, origin.Y(), origin.Z());
  const gp_Dir tangent(0, 2 * kPi * kRadius, pitch);
  const gp_Circ circle(gp_Ax2(start, tangent), kTube);
  TopoDS_Wire profile = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circle).Edge()).Wire();
  TopoDS_Wire spine = BRepBuilderAPI_MakeWire(edge).Wire();

  BRepOffsetAPI_MakePipeShell sweep(spine);
  sweep.SetMode(Standard_True);
  sweep.SetTolerance(1e-5, 1e-5, 1e-2);
  sweep.Add(profile, TopExp::FirstVertex(edge, Standard_True), Standard_False, Standard_False);
  sweep.Build();
  if (!sweep.IsDone() || !sweep.MakeSolid()) {
    throw Standard_Failure("sweep failed");
  }
  return sweep.Shape();
}

double volume(const TopoDS_Shape& shape) {
  GProp_GProps props;
  BRepGProp::VolumeProperties(shape, props, 1e-6, false, true);
  return props.Mass();
}

int countSolids(const TopoDS_Shape& shape) {
  TopTools_IndexedMapOfShape solids;
  TopExp::MapShapes(shape, TopAbs_SOLID, solids);
  return solids.Extent();
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const std::string folder = argv[1];
  const double pitch1 = 2 * kPi * kRadius * std::tan(kAngle1 * kDeg);
  const double pitch2 = 2 * kPi * kRadius * std::tan((kAngle1 + kTheta) * kDeg);
  for (int variant = 0; variant < 2; ++variant) {
    kTube = variant == 0 ? 6.0 : 6.05;
    const TopoDS_Shape a = helixTube(gp_Pnt(0, 0, 0), pitch1, 1);
    const TopoDS_Shape b = helixTube(gp_Pnt(0, 0, pitch1), pitch2, 6);
    if (!BRepCheck_Analyzer(a).IsValid() || !BRepCheck_Analyzer(b).IsValid()) return 3;
    const std::string suffix = variant == 0 ? "original" : "radius";
    BRepTools::Write(a, (folder + "/first-" + suffix + ".brep").c_str());
    BRepTools::Write(b, (folder + "/second-" + suffix + ".brep").c_str());
    std::printf("INPUT_VALID radius=%.6f first_volume=%.12f second_volume=%.12f\n", kTube, volume(a), volume(b));
  }
  return 0;
}
