// Geometry reader from the frozen 544 control. Emits geometry in world coordinates.
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepAlgoAPI_Check.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Vertex.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <gp_Pln.hxx>
#include <iostream>
#include <iomanip>
#include <cmath>
#include <string>
#include <stdexcept>
using Map=NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher>;
using std::string;
void xyz(const gp_XYZ& p){std::cout<<" "<<p.X()<<" "<<p.Y()<<" "<<p.Z();}
TopoDS_Shape read(const string& p){
 BRep_Builder b;TopoDS_Shape s;if(!BRepTools::Read(s,p.c_str(),b)||s.IsNull())throw std::runtime_error(p);return s;
}
Map topology(const TopoDS_Shape& s,TopAbs_ShapeEnum kind){Map m;TopExp::MapShapes(s,kind,m);return m;}
void describe(const TopoDS_Shape& s){
 auto faces=topology(s,TopAbs_FACE),edges=topology(s,TopAbs_EDGE),vertices=topology(s,TopAbs_VERTEX),solids=topology(s,TopAbs_SOLID);
 if(solids.Extent()!=1)throw std::runtime_error("single solid required");
 GProp_GProps v,a;BRepGProp::VolumeProperties(s,v,1.e-10);BRepGProp::SurfaceProperties(s,a,1.e-10);
 BRepCheck_Analyzer valid(s);BRepAlgoAPI_Check self(s);
 std::cout<<"SOLID "<<solids.Extent()<<" "<<faces.Extent()<<" "<<edges.Extent()<<" "<<vertices.Extent()<<" "<<valid.IsValid()<<" "<<self.IsValid()<<" "<<v.Mass()<<" "<<a.Mass();
 xyz(v.CentreOfMass().XYZ());std::cout<<"\n";
 for(int i=1;i<=faces.Extent();i++){
   auto f=TopoDS::Face(faces(i));BRepAdaptor_Surface surf(f);
   auto es=topology(f,TopAbs_EDGE),vs=topology(f,TopAbs_VERTEX);int lines=0;
   for(int j=1;j<=es.Extent();++j)lines+=BRepAdaptor_Curve(TopoDS::Edge(es(j))).GetType()==GeomAbs_Line;
   GProp_GProps prop;BRepGProp::SurfaceProperties(f,prop,1.e-10);
   std::cout<<"FACE "<<i<<" "<<int(surf.GetType())<<" "<<int(f.Orientation())<<" "<<prop.Mass()<<" "<<topology(f,TopAbs_WIRE).Extent()<<" "<<es.Extent()<<" "<<lines;
   xyz(prop.CentreOfMass().XYZ());std::cout<<"\n";
   if(surf.GetType()==GeomAbs_Plane){
     auto p=surf.Plane();std::cout<<"PLANE "<<i;xyz(p.Location().XYZ());xyz(p.Axis().Direction().XYZ());std::cout<<"\n";
   }
   for(int j=1;j<=vs.Extent();j++){std::cout<<"VERTEX "<<i;xyz(BRep_Tool::Pnt(TopoDS::Vertex(vs(j))).XYZ());std::cout<<"\n";}
   for(int j=1;j<=es.Extent();j++){
      auto edge=TopoDS::Edge(es(j)); BRepAdaptor_Curve c(edge);
      std::cout<<"SEG "<<i<<" "<<int(c.GetType());xyz(c.Value(c.FirstParameter()).XYZ());xyz(c.Value(c.LastParameter()).XYZ());std::cout<<"\n";
   }
 }
 BRepClass3d_SolidClassifier classifier(solids(1));
 auto classify=[&](double x,double y,double z){
   classifier.Perform(gp_Pnt(x,y,z),1.e-7);std::cout<<"MATERIAL "<<x<<" "<<y<<" "<<z<<" "<<int(classifier.State())<<"\n";
 };
   for(double x:{-.25,.25,3.5,4.75,5.25,9.75,10.25,11.25})for(double y:{-.25,2.5,6.,8.25})for(double z:{-.25,1.,5.,6.25})classify(x,y,z);
}
