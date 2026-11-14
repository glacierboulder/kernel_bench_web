#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <Standard_Failure.hxx>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

bool check(double a, double b, const std::string& output) {
  const auto box = BRepPrimAPI_MakeBox(10,10,10).Shape();
  NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher> edges;
  for (TopExp_Explorer e(box,TopAbs_EDGE); e.More(); e.Next()) edges.Add(e.Current());
  BRepFilletAPI_MakeFillet fillet(box);
  fillet.Add(a,TopoDS::Edge(edges(10)));
  fillet.Add(b,TopoDS::Edge(edges(9)));
  fillet.Build();
  std::cout << a << "," << b << " done=" << fillet.IsDone();
  if (!fillet.IsDone()) { std::cout << std::endl; return false; }
  const auto result = fillet.Shape();
  GProp_GProps props;
  BRepGProp::VolumeProperties(result, props);
  int solids=0, cylinders=0, remaining=0;
  for (TopExp_Explorer e(result,TopAbs_SOLID); e.More(); e.Next()) ++solids;
  for (TopExp_Explorer e(result,TopAbs_FACE); e.More(); e.Next()) {
    BRepAdaptor_Surface surface(TopoDS::Face(e.Current()));
    if(surface.GetType()==GeomAbs_Cylinder) ++cylinders;
    if(surface.GetType()==GeomAbs_Plane) {
      auto plane=surface.Plane();
      if(std::abs(plane.Axis().Direction().Y())>1-1e-8 && std::abs(plane.Location().Y())<1e-8) ++remaining;
    }
  }
  const double expected=1000-10*(1-std::acos(-1.)/4)*(a*a+b*b);
  const bool valid=BRepCheck_Analyzer(result).IsValid();
  const bool pass=valid && solids==1 && cylinders==2 &&
    remaining==(a+b<10 ? 1:0) && std::abs(props.Mass()-expected)<1e-4;
  std::cout << " valid=" << valid << " solids=" << solids << " cylinders=" << cylinders
            << " remaining=" << remaining << " volume=" << props.Mass()
            << " expected=" << expected << " pass=" << pass << std::endl;
  if(!output.empty()) BRepTools::Write(result,output.c_str(),false,false,TopTools_FormatVersion_VERSION_1);
  return pass;
}

int main(int argc,char** argv) {
  std::cout << std::setprecision(12);
  try {
    if(argc==2) {
      std::ifstream input(argv[1]); double a,b;
      if(!(input>>a>>b)) return 2;
      if(!check(a,b,"")) return 1;
      std::cout<<"TEST_DONE\n";
      return 0;
    }
    const std::string prefix=argc==3 && std::string(argv[1])=="--dump"?argv[2]:"";
    const double radii[][2]={{5,5},{4,6},{6,4},{4.99,4.99}};
    for(int i=0;i<4;++i) check(radii[i][0],radii[i][1],prefix.empty()?"":prefix+"-"+std::to_string(i)+".brep");
  } catch(const Standard_Failure& e) {
    std::cerr<<e.what()<<std::endl;
    return 2;
  }
}
