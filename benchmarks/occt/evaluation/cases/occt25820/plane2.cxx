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
TopoDS_Face loadFace(const char* name,int index) {
  TopoDS_Shape s; BRep_Builder builder;
  if (!BRepTools::Read(s,name,builder)) throw "read error";
  TopTools_IndexedMapOfShape faces;TopExp::MapShapes(s,TopAbs_FACE,faces);
  return TopoDS::Face(faces(index));
}
int main(int argc,char** argv) {
  if(argc!=3)return 2;
  TopoDS_Face a=loadFace(argv[1],4);
  TopoDS_Face b=loadFace(argv[2],4);
  BRepAlgoAPI_Section op(a,b,false);op.Approximation(true);op.Build();
  if(!op.IsDone()||op.Shape().IsNull()){std::cout<<"done=0\n";return 1;}
  TopoDS_Shape result=op.Shape();
  TopTools_IndexedMapOfShape edges,vertices;
  TopExp::MapShapes(result,TopAbs_EDGE,edges);TopExp::MapShapes(result,TopAbs_VERTEX,vertices);
  GProp_GProps length;BRepGProp::LinearProperties(result,length);
  const bool valid=BRepCheck_Analyzer(result).IsValid();
  const bool good=valid && edges.Extent()==1 && vertices.Extent()==2 && std::abs(length.Mass()-2.5348669440044e-5)<1.e-8;
  std::cout<<std::setprecision(14)<<"edges="<<edges.Extent()<<" vertices="<<vertices.Extent()<<" length="<<length.Mass()<<" valid="<<valid<<" verdict="<<(good?"PASS":"FAIL")<<"\n";
  return good?0:1;
}
