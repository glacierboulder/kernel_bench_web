#define HAVE_IOSTREAM
#define HAVE_FSTREAM
#define HAVE_IOMANIP
#define HAVE_LIMITS_H
#define CSFDB
#include <BRepAlgoAPI_Section.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopoDS_Iterator.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <gp_Pln.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
int main(int argc,char** argv) {
  if (argc!=2) return 2;
  TopoDS_Shape a,b;
    a=BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0,0,0),gp_Dir(0,0,1)),-4,4,-4,4).Shape();
    b=BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0,0,0),gp_Dir(1,0,0)),-3,3,-3,3).Shape();
  BRepAlgoAPI_Section cut(a,b,Standard_False);
  cut.Approximation(Standard_True);
  cut.ComputePCurveOn1(Standard_True); cut.ComputePCurveOn2(Standard_True);
  cut.Build();
  if(!cut.IsDone()||cut.Shape().IsNull())return 2;
  TopTools_IndexedMapOfShape e,v; TopExp::MapShapes(cut.Shape(),TopAbs_EDGE,e);TopExp::MapShapes(cut.Shape(),TopAbs_VERTEX,v);
  GProp_GProps p;BRepGProp::LinearProperties(cut.Shape(),p);
  bool valid=BRepCheck_Analyzer(cut.Shape()).IsValid();
  bool ok=valid && e.Extent()==1 && v.Extent()==2 && std::abs(p.Mass()-6) <= 1e-06;
  std::cout<<std::setprecision(14)<<"edges="<<e.Extent()<<" vertices="<<v.Extent()<<" length_mm="<<p.Mass()<<" valid="<<valid<<" verdict="<<(ok?"PASS":"FAIL")<<"\n";return ok?0:1;
}
