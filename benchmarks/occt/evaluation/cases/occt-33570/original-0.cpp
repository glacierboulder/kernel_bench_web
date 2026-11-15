#include <BRepAlgoAPI_Cut.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <cmath>
#include <cstdio>

int main() {
  const gp_Pnt p1(0,5.5,18), p2(0,4.5,14);
  const double r1=4, r2=1;
  auto a=BRepPrimAPI_MakeSphere(p1,r1).Shape();
  auto b=BRepPrimAPI_MakeSphere(p2,r2).Shape();
  BRepAlgoAPI_Cut cut(a,b);
  if (!cut.IsDone()) return 2;
  bool pass=BRepCheck_Analyzer(cut.Shape()).IsValid();
  const double d=p1.Distance(p2), pi=std::acos(-1.);
  const double sum=r1+r2, gap=r1-r2;
  const double lens=d>=sum?0:pi*(sum-d)*(sum-d)*(d*d+2*d*sum-3*gap*gap)/(12*d);
  const double expected=4*pi*r1*r1*r1/3-lens;
  GProp_GProps props;
  BRepGProp::VolumeProperties(cut.Shape(),props);
  std::printf("volume actual=%.15g expected=%.15g\n",props.Mass(),expected);
  pass &= std::abs(props.Mass()-expected)<1e-5;
  int topology[]={4,7,2,2};
  TopAbs_ShapeEnum types[]={TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE,TopAbs_FACE};
  for(int i=0;i<4;++i) {
    NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher> map;
    TopExp::MapShapes(cut.Shape(),types[i],map);
    std::printf("type=%d actual=%d expected=%d\n",types[i],map.Extent(),topology[i]);
    pass &= map.Extent()==topology[i];
  }
  std::puts(pass?"verdict=pass":"verdict=fail");
  return pass?0:1;
}

