
#include <ShapeAnalysis_Surface.hxx>
#include <Geom_BSplineSurface.hxx>
#include <NCollection_Array1.hxx>
#include <NCollection_Array2.hxx>
#include <Precision.hxx>
#include <cmath>
#include <cstdio>
int main() {
  const double hintU=.375, hintV=.25, scale=1, displacement=0;
  NCollection_Array2<gp_Pnt> poles(1,2,1,2);
  poles.SetValue(1,1,gp_Pnt(displacement,0,0));
  poles.SetValue(2,1,gp_Pnt(displacement,0,0));
  poles.SetValue(1,2,gp_Pnt(displacement+scale,0,scale));
  poles.SetValue(2,2,gp_Pnt(displacement,scale,scale));
  NCollection_Array1<double> knots(1,2);
  knots.SetValue(1,0);
  knots.SetValue(2,1);
  NCollection_Array1<int> multiplicities(1,2);
  multiplicities.Init(2);
  const occ::handle<Geom_BSplineSurface> surface=new Geom_BSplineSurface(
      poles,knots,knots,multiplicities,multiplicities,1,1);
  ShapeAnalysis_Surface analysis(surface);
  const gp_Pnt2d hint(hintU,hintV);
  const gp_Pnt point=surface->EvalD0(hintU,hintV);
  const gp_Pnt2d result=analysis.NextValueOfUV(hint,point,Precision::Confusion());
  const double residual=point.Distance(surface->EvalD0(result.X(),result.Y()));
  const bool pass=result.Distance(hint)<1e-12 && residual<Precision::Confusion();
  std::printf("UV=(%.17g,%.17g) expected=(%.17g,%.17g) residual=%.17g\n",
              result.X(),result.Y(),hintU,hintV,residual);
  std::puts(pass?"verdict=pass":"verdict=fail");
  return pass?0:1;
}
