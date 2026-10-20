#include <BRepAdaptor_CompCurve.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <GC_MakeSegment.hxx>
#include <GeomFill_CorrectedFrenet.hxx>
#include <ShapeExtend_WireData.hxx>
#include <gp_Pnt.hxx>
#include <iostream>

int main()
{
  const gp_Pnt points[] = {gp_Pnt(-1, -1, 0), gp_Pnt(0, -2, 0),
                           gp_Pnt(0, -2, -1), gp_Pnt(0, -1, -1)};
  ShapeExtend_WireData wire;
  for (int i = 1; i < 4; ++i)
    wire.Add(BRepBuilderAPI_MakeEdge(GC_MakeSegment(points[i - 1], points[i]).Value()).Edge());
  BRepAdaptor_CompCurve curve(wire.WireAPIMake());
  GeomFill_CorrectedFrenet law;
  law.SetCurve(curve.ShallowCopy());
  std::cout << "TEST_DONE issue=370\n";
  return 0;
}
