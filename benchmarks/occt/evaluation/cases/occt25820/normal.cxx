#define HAVE_IOSTREAM
#define HAVE_FSTREAM
#define HAVE_LIMITS_H
#define HAVE_IOMANIP
#define CSFDB
#include <cmath>
#include <BRepAlgoAPI_Section.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <IntTools_FaceFace.hxx>
#include <IntTools_Curve.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <gp_Pln.hxx>
#include <iomanip>
#include <cstdlib>
#include <iostream>
#include <string>
int main(int argc,char** argv) {
  gp_Pln p(gp_Pnt(0,0,0),gp_Dir(0,0,1));
  gp_Pln q(gp_Pnt(0,0,0),gp_Dir(0,1,0));
  TopoDS_Face a=BRepBuilderAPI_MakeFace(p,-2,2,-2,2).Face();
  TopoDS_Face b=BRepBuilderAPI_MakeFace(q,-3,3,-3,3).Face();
  BRepAlgoAPI_Section op(a,b,false);op.Approximation(true);op.Build();
  if(!op.IsDone()||op.Shape().IsNull()){std::cout<<"done=0\n";return 1;}
  TopoDS_Shape result=op.Shape();
  TopTools_IndexedMapOfShape edges,vertices;
  TopExp::MapShapes(result,TopAbs_EDGE,edges);TopExp::MapShapes(result,TopAbs_VERTEX,vertices);
  GProp_GProps length;BRepGProp::LinearProperties(result,length);
  const bool valid=BRepCheck_Analyzer(result).IsValid();
  const bool good=valid && edges.Extent()==1 && vertices.Extent()==2 && std::abs(length.Mass()-4.)<1.e-8;
  std::cout<<std::setprecision(14)<<"edges="<<edges.Extent()<<" vertices="<<vertices.Extent()<<" length="<<length.Mass()<<" valid="<<valid<<" verdict="<<(good?"PASS":"FAIL")<<"\n";
  return good?0:1;
}
