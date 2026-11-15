
#include <Geom_Plane.hxx>
#include <Geom_OffsetSurface.hxx>
#include <gp_Ax3.hxx>
#include <gp_Vec.hxx>
#include <cstdio>

int main() {
  const bool reverseU=false, reverseV=true;
  const double distance=.25;
  const gp_Dir orientation(1,2,3);
  const occ::handle<Geom_Plane> plane=new Geom_Plane(gp_Ax3(gp_Pnt(1,2,3),orientation));
  if (reverseU) plane->UReverse();
  if (reverseV) plane->VReverse();
  const double u=.375,v=-.625;
  const auto [point,du,dv]=plane->EvalD1(u,v);
  const gp_Pnt expected=point.Translated(distance*du.Crossed(dv).Normalized());
  const Geom_OffsetSurface offset(plane,distance);
  const occ::handle<Geom_Surface> equivalent=offset.Surface();
  const double nativeError=offset.EvalD0(u,v).Distance(expected);
  const double equivalentError=equivalent.IsNull() ? -1 : equivalent->EvalD0(u,v).Distance(expected);
  const bool pass=nativeError<1e-12 && equivalentError>=0 && equivalentError<1e-12;
  std::printf("native error=%.17g equivalent error=%.17g\n",nativeError,equivalentError);
  std::puts(pass?"verdict=pass":"verdict=fail");
  return pass?0:1;
}
