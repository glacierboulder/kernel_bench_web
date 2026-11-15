
#include <Geom_Ellipse.hxx>
#include <Geom_OffsetCurve.hxx>
#include <cmath>
#include <cstdio>
int main() {
  const double major=2, minor=1.5, offset=.25;
  const occ::handle<Geom_Curve> basis=new Geom_Ellipse(gp_Ax2(),major,minor);
  const Geom_OffsetCurve curve(basis,offset,gp_Dir(0,0,1));
  const double expected=-major-offset*(major/minor)*(major/minor);
  const double actual=curve.EvalD3(0).D2.X(), lower=curve.EvalD2(0).D2.X();
  const bool pass=std::abs(actual-expected)<1e-12 && std::abs(lower-expected)<1e-12;
  std::printf("EvalD3 D2.X=%.17g EvalD2 D2.X=%.17g expected=%.17g\n",actual,lower,expected);
  std::puts(pass?"verdict=pass":"verdict=fail");
  return pass?0:1;
}
