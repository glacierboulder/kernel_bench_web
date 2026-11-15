
#include <Geom2d_Circle.hxx>
#include <Geom2d_OffsetCurve.hxx>
#include <Geom2d_TrimmedCurve.hxx>
#include <cmath>
#include <cstdio>
int main() {
  const double shift=0, radius=5, offset=1;
  const double first=shift+0.25, last=shift+1.75;
  const occ::handle<Geom2d_Curve> circle=new Geom2d_Circle(gp_Ax2d(),radius);
  const occ::handle<Geom2d_Curve> trim=new Geom2d_TrimmedCurve(circle,first,last,true,false);
  const Geom2d_OffsetCurve curve(trim,offset);
  const double low=curve.FirstParameter(), high=curve.LastParameter();
  bool pass=std::abs(low-first)<1e-12 && std::abs(high-last)<1e-12;
  for(int i=0;i<=12;++i) {
    const double u=first+i*(last-first)/12;
    const gp_Pnt2d expected((radius+offset)*std::cos(u),(radius+offset)*std::sin(u));
    pass &= curve.EvalD0(u).Distance(expected)<1e-11;
  }
  std::printf("domain=[%.17g,%.17g] expected=[%.17g,%.17g]\n",low,high,first,last);
  std::puts(pass?"verdict=pass":"verdict=fail");
  return pass?0:1;
}
