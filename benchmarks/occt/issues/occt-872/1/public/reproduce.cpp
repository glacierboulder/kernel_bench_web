#include <BRepBuilderAPI_GTransform.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <Standard_Failure.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <gp_Ax2.hxx>
#include <gp_GTrsf.hxx>
#include <gp_Pnt.hxx>
#include <gp_Vec.hxx>
#include <fstream>
#include <iostream>

int main(int argc, char** argv)
{
  if (argc != 2) return 64;
  TopoDS_Shape shape;
  BRep_Builder builder;
  std::ifstream input(argv[1]);
  BRepTools::Read(shape, input, builder);
  if (shape.IsNull()) return 65;
  TopExp_Explorer faces(shape, TopAbs_FACE);
  if (!faces.More()) return 66;
  const gp_Ax2 axis(gp_Pnt(800, 625, 183), gp_Vec(0, 1, 0));
  gp_GTrsf transform;
  transform.SetAffinity(axis, 0.75000000000002087);
  try
  {
    BRepBuilderAPI_GTransform result(TopoDS::Face(faces.Current()), transform);
    if (result.IsDone()) std::cout << "TEST_DONE issue=872\n";
    return result.IsDone() ? 0 : 2;
  }
  catch (const Standard_Failure& failure)
  {
    std::cerr << failure.GetMessageString() << "\n";
    return 3;
  }
}
