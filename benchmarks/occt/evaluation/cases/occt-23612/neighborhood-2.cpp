
#include <BRepPrimAPI_MakeTorus.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <cmath>
#include <cstdio>
int main() {
  const double pi=std::acos(-1.);
  const double major=10, minor=2, v0=.5*pi, v1=1.5*pi, sweep=.5*pi;
  BRepPrimAPI_MakeTorus torus(gp_Ax2(gp_Pnt(0,0,0),gp_Dir(0,0,1)),major,minor,v0,v1,sweep);
  const TopoDS_Shape shape=torus.Shape();
  const bool valid=BRepCheck_Analyzer(shape).IsValid();
  int lateral=0;
  bool range=true;
  for (TopExp_Explorer it(shape,TopAbs_FACE);it.More();it.Next()) {
    BRepAdaptor_Surface surface(TopoDS::Face(it.Current()));
    if (surface.GetType()!=GeomAbs_Torus) continue;
    ++lateral;
    range &= std::abs(surface.LastUParameter()-surface.FirstUParameter()-sweep)<1e-10;
    range &= std::abs(surface.LastVParameter()-surface.FirstVParameter()-(v1-v0))<1e-10;
  }
  std::printf("valid=%d lateral=%d range=%d\n",valid,lateral,range);
  const bool pass=valid && range && lateral==1;
  std::puts(pass?"verdict=pass":"verdict=fail");
  return pass?0:1;
}
