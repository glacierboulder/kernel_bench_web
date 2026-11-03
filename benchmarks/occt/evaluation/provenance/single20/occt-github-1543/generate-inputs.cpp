#include <BRepTools.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <string>
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
  if (argc != 2) return 2;
  const std::string folder = argv[1];
  TopoDS_Shape cylinder = BRepPrimAPI_MakeCylinder(R, 30.0).Shape();
  if (!BRepCheck_Analyzer(cylinder).IsValid()) return 3;
  BRepTools::Write(cylinder, (folder + "/cylinder.brep").c_str());
  const double offsets[] = {16.2, 16.6, 16.0};
  const char* names[] = {"tool-original.brep", "tool-offset.brep", "tool-health.brep"};
  for (int i = 0; i < 3; ++i) {
    TopoDS_Shape swept = tool(offsets[i], 1);
    if (!BRepCheck_Analyzer(swept).IsValid()) return 4;
    BRepTools::Write(swept, (folder + "/" + names[i]).c_str());
    std::printf("INPUT_VALID dz=%.1f volume=%.12g\n", offsets[i], volume(swept));
  }
  return 0;
}
