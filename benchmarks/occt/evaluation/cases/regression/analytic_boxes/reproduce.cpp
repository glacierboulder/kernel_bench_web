#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepAlgoAPI_Common.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <GProp_GProps.hxx>
#include <gp_Pnt.hxx>
#include <cmath>
#include <iostream>
int main() {
  for (double scale : {0.1, 1.0, 10.0}) {
    auto a=BRepPrimAPI_MakeBox(2*scale,2*scale,2*scale).Shape();
    auto b=BRepPrimAPI_MakeBox(gp_Pnt(scale,0,0),2*scale,2*scale,2*scale).Shape();
    BRepAlgoAPI_Fuse f(a,b); BRepAlgoAPI_Cut c(a,b); BRepAlgoAPI_Common i(a,b);
    if(!f.IsDone()||!c.IsDone()||!i.IsDone())return 1;
    TopoDS_Shape shapes[]={f.Shape(),c.Shape(),i.Shape()}; double expected[]={12,4,4};
    for(int j=0;j<3;j++) {
      if(shapes[j].IsNull()||!BRepCheck_Analyzer(shapes[j]).IsValid())return 2;
      GProp_GProps p;BRepGProp::VolumeProperties(shapes[j],p);
      if(std::abs(p.Mass()-expected[j]*scale*scale*scale)>1e-7*std::max(1.0,scale*scale*scale))return 3;
    }
  }
  std::cout<<"TEST_DONE analytic Boolean volumes and shape validity at 3 scales\n";
}
