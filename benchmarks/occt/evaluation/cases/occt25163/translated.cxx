#define HAVE_IOSTREAM
#define HAVE_FSTREAM
#define HAVE_LIMITS_H
#define HAVE_IOMANIP
#define CSFDB
#include <BRepAlgoAPI_Common.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <gp_Pln.hxx>
#include <gp_Trsf.hxx>
#include <gp_Vec.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
int main(int argc,char** argv) {
  if(argc<2)return 2;
  TopoDS_Shape a,b;
  {
    BRep_Builder reader;
    TopoDS_Shape input;
    if(!BRepTools::Read(input,argv[1],reader))return 2;
    TopTools_IndexedMapOfShape faces;
    TopExp::MapShapes(input,TopAbs_FACE,faces);
    if(faces.Extent()!=2)return 2;
    a=faces(1); b=faces(2);
    gp_Trsf t;t.SetTranslation(gp_Vec(2,0,0));TopLoc_Location loc(t);a=a.Moved(loc);b=b.Moved(loc);
  }
  BRepAlgoAPI_Common op(a,b);
  if(!op.IsDone()||op.Shape().IsNull()) {std::cout<<"empty=1 verdict=FAIL\n"; return 1;}
  TopoDS_Shape r=op.Shape();
  TopTools_IndexedMapOfShape faces,edges,vertices,shells;
  TopExp::MapShapes(r,TopAbs_FACE,faces); TopExp::MapShapes(r,TopAbs_EDGE,edges);
  TopExp::MapShapes(r,TopAbs_VERTEX,vertices); TopExp::MapShapes(r,TopAbs_SHELL,shells);
  GProp_GProps area; BRepGProp::SurfaceProperties(r,area);
  const bool valid=BRepCheck_Analyzer(r).IsValid();
  const bool good=vertices.Extent()==4 && edges.Extent()==4 && faces.Extent()==1 && valid && std::abs(area.Mass()-3417.71)<.1;
  std::cout<<std::setprecision(14)<<"vertices="<<vertices.Extent()<<" edges="<<edges.Extent()<<" faces="<<faces.Extent()<<" shells="<<shells.Extent()<<" area="<<area.Mass()<<" valid="<<valid<<" verdict="<<(good?"PASS":"FAIL")<<"\n";
  return good?0:1;
}
