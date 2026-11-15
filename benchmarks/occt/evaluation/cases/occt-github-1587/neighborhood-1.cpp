#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepGProp_Domain.hxx>
#include <BRepGProp_Face.hxx>
#include <BRepGProp_Vinert.hxx>
#include <gp_Pln.hxx>
#include <cmath>
#include <cstdio>

int main() {
  const double width=2.5, depth=6, height=2, offset=0;
  const gp_Dir normal(0,0,1);
  const gp_Pln plane(gp_Pnt(0,0,offset),normal);
  BRepBuilderAPI_MakeFace make(gp_Pln(gp_Pnt(0,0,height+offset),normal),0,width,0,depth);
  if (!make.IsDone()) return 2;
  const TopoDS_Face face=make.Face();
  BRepGProp_Face surface(face);
  BRepGProp_Domain domain(face);
  BRepGProp_Vinert props(surface,domain,plane,gp_Pnt(0,0,0),1e-8);
  const gp_Mat inertia=props.MatrixOfInertia();
  const double mass=width*depth*height;
  const double expected[]={mass*(depth*depth+height*height)/12,
                           mass*(width*width+height*height)/12,
                           mass*(width*width+depth*depth)/12};
  bool pass=std::abs(props.Mass()-mass)<1e-9;
  for(int i=1;i<=3;++i) for(int j=i;j<=3;++j) {
    double value=inertia.Value(i,j), target=i==j?expected[i-1]:0;
    std::printf("I%d%d: actual=%.17g expected=%.17g\n",i,j,value,target);
    pass &= std::abs(value-target)<1e-9;
  }
  std::puts(pass?"verdict=pass":"verdict=fail");
  return pass?0:1;
}
