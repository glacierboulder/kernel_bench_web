#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepOffsetAPI_MakeOffset.hxx>
#include <GeomAbs_JoinType.hxx>
#include <Standard_Failure.hxx>
#include <TopoDS_Wire.hxx>
#include <gp_Ax2.hxx>
#include <gp_Circ.hxx>
#include <gp_Dir.hxx>
#include <gp_Pnt.hxx>
#include <cmath>
#include <iostream>

int main()
{
  const double pi = std::acos(-1.0);
  const gp_Circ circle(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 1.0);
  const TopoDS_Wire wire = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circle));
  try
  {
    BRepOffsetAPI_MakeOffset operation(wire, GeomAbs_Arc);
    operation.Perform(std::tan(-pi / 180.0) * 3.0);
    if (operation.IsDone()) std::cout << "TEST_DONE issue=1452\n";
    return operation.IsDone() ? 0 : 2;
  }
  catch (const Standard_Failure& failure)
  {
    std::cerr << failure.GetMessageString() << "\n";
    return 3;
  }
}
