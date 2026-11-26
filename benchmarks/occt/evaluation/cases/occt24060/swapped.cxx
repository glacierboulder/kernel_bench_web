#define HAVE_IOSTREAM
#define HAVE_FSTREAM
#define HAVE_LIMITS_H
#define HAVE_IOMANIP
#define CSFDB
#include <BOPAlgo_Builder.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakePolygon.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <iomanip>
#include <iostream>
#include <string>
int main(int argc,char** argv) {
  const double x=0.0;
  BRepBuilderAPI_MakePolygon q;
  q.Add(gp_Pnt(x,0,0)); q.Add(gp_Pnt(x,0,1)); q.Add(gp_Pnt(x+1,0,1)); q.Add(gp_Pnt(x+1,0,0)); q.Close();
  TopoDS_Shape face=BRepBuilderAPI_MakeFace(q.Wire()).Shape();
  gp_Pnt pt=gp_Pnt(x,0,1);
  TopoDS_Shape vertex=BRepBuilderAPI_MakeVertex(pt).Shape();
  BOPAlgo_Builder builder;
  builder.AddArgument(vertex); builder.AddArgument(face);
  builder.Perform();
  TopoDS_Shape result=builder.Shape();
  if (builder.ErrorStatus() || result.IsNull()) { std::cout<<"error="<<builder.ErrorStatus()<<" verdict=FAIL\n";return 1; }
  TopTools_IndexedMapOfShape vertices,edges,faces;
  TopExp::MapShapes(result,TopAbs_VERTEX,vertices); TopExp::MapShapes(result,TopAbs_EDGE,edges); TopExp::MapShapes(result,TopAbs_FACE,faces);
  int coincident=0;
  for (int i=1;i<=vertices.Extent();i++)
    if (BRep_Tool::Pnt(TopoDS::Vertex(vertices(i))).Distance(pt)<1.e-8) ++coincident;
  GProp_GProps surf;
  BRepGProp::SurfaceProperties(result,surf);
  bool valid=BRepCheck_Analyzer(result).IsValid();
  bool good=vertices.Extent()==4 && edges.Extent()==4 && faces.Extent()==1 && coincident==1 && std::abs(surf.Mass()-1.)<1.e-7 && valid;
  std::cout<<std::setprecision(15)<<"vertices="<<vertices.Extent()<<" coincident="<<coincident<<" edges="<<edges.Extent()<<" faces="<<faces.Extent()<<" area="<<surf.Mass()<<" valid="<<valid<<" verdict="<<(good?"PASS":"FAIL")<<"\n";
  return good?0:1;
}
