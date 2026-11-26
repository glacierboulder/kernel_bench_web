#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopoDS.hxx>
#include <TopExp_Explorer.hxx>
#include <iomanip>
#include <iostream>

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  TopoDS_Shape shape;
  BRep_Builder reader;
  if (!BRepTools::Read(shape, argv[1], reader)) return 2;
  TopExp_Explorer ex(shape,TopAbs_EDGE);
  if (!ex.More()) return 2;
  const TopoDS_Edge edge=TopoDS::Edge(ex.Current());
  GProp_GProps linear;
  BRepGProp::LinearProperties(edge,linear);
  std::cout << std::setprecision(14);
  for (double tol : {1.e-4, 5.e-5*linear.Mass(), 1.e-5, 1.e-6}) {
    BRepFilletAPI_MakeFillet fillet(shape,ChFi3d_Rational);
    fillet.SetParams(.01, tol, 1.e-5, 1.e-4, 1.e-5, 1.e-3);
    fillet.SetContinuity(GeomAbs_C1,.01);
    fillet.Add(.01,edge);
    fillet.Build();
    std::cout << "edge_mm=" << linear.Mass() << " tesp=" << tol
              << " approx3d=0.0001 done=" << fillet.IsDone()
              << " stripe_status=" << fillet.StripeStatus(1);
    if (fillet.IsDone()) {
      GProp_GProps surface;
      BRepGProp::SurfaceProperties(fillet.Shape(),surface);
      std::cout << " area_mm2=" << surface.Mass();
    }
    std::cout << "\n";
  }
}
