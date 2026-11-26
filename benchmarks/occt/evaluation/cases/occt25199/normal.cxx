#define HAVE_IOSTREAM
#define HAVE_FSTREAM
#define HAVE_IOMANIP
#define HAVE_LIMITS_H
#define CSFDB
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <ShapeAnalysis_ShapeTolerance.hxx>
#include <GProp_GProps.hxx>
#include <TopoDS.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <gp_Trsf.hxx>
#include <cmath>
#include <iostream>
#include <iomanip>
int main(int argc,char** argv) {
  if (argc!=2) return 2;
  try {
    TopoDS_Shape s;
    BRep_Builder reader;
    s=BRepPrimAPI_MakeBox(100,100,100).Shape();
    TopTools_IndexedMapOfShape in; TopExp::MapShapes(s,TopAbs_EDGE,in);
    BRepFilletAPI_MakeFillet op(s,ChFi3d_Rational);
    op.SetParams(.01,1.e-4,1.e-5,1.e-4,1.e-5,.001);
    op.SetContinuity(GeomAbs_C1,.01);
    op.Add(9.,TopoDS::Edge(in(1))); op.Build();
    if (!op.IsDone()) { std::cerr<<"fillet missing\n"; return 2; }
    const TopoDS_Shape result=op.Shape();
    GProp_GProps p; BRepGProp::SurfaceProperties(result,p);
    TopTools_IndexedMapOfShape faces,edges;
    TopExp::MapShapes(result,TopAbs_FACE,faces); TopExp::MapShapes(result,TopAbs_EDGE,edges);
    ShapeAnalysis_ShapeTolerance tol; tol.InitTolerance(); tol.AddTolerance(result);
    const double maximum=tol.GlobalTolerance(1);
    
    const bool valid=BRepCheck_Analyzer(result).IsValid();
    const bool ok=valid && maximum>=0. && maximum<=.001 && faces.Extent()==7
      && std::abs(p.Mass()-(60000-1800+450*acos(-1.)-162*(1-acos(-1.)/4)))<.2;
    std::cout<<std::setprecision(15)<<"max_tol_mm="<<maximum<<" area_mm2="<<p.Mass()
      <<" faces="<<faces.Extent()<<" valid="<<valid<<" verdict="<<(ok?"PASS":"FAIL")<<"\n";
    return ok?0:1;
  } catch(const Standard_Failure& e) { std::cerr<<e.GetMessageString()<<"\n"; return 2; }
}
