#include <gp_Ax1.hxx>
#include <BRepAlgoAPI_Common.hxx>
#include <BRep_Builder.hxx>
#include <BRepTools.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopLoc_Location.hxx>
#include <gp_Trsf.hxx>
#include <fstream>
#include <iostream>
#include <cmath>

TopoDS_Shape read(const char* path)
{
  std::ifstream stream(path);
  std::string header;
  std::getline(stream, header);
  TopoDS_Shape shape;
  BRepTools::Read(shape, stream, BRep_Builder());
  return shape;
}

int main()
{
  auto a = read("bug25237_b26.brep");
  auto b = read("bug25237_b5.brep");
  if (a.IsNull() || b.IsNull()) return 2;
  int failures = 0;
  for (int scenario = 3; scenario < 4; ++scenario)
  {
    gp_Trsf tr;
    if (scenario == 1) tr.SetTranslation(gp_Vec(17, -13, 9));
    if (scenario == 2) tr.SetRotation(gp_Ax1(gp_Pnt(), gp_Dir(0,0,1)), 37 * std::acos(-1.) / 180);
    if (scenario == 3) tr.SetTranslation(gp_Vec(0, 10, 0));
    for (int swap = 0; swap < 2; ++swap)
    {
      auto x = scenario == 3 ? a : a.Moved(TopLoc_Location(tr));
      auto y = b.Moved(TopLoc_Location(tr));
      BRepAlgoAPI_Common common(swap ? y : x, swap ? x : y);
      if (!common.IsDone() || common.HasErrors() || common.Shape().IsNull()) return 3;
      GProp_GProps props;
      BRepGProp::LinearProperties(common.Shape(), props);
      int edges = 0;
      for (TopExp_Explorer it(common.Shape(), TopAbs_EDGE); it.More(); it.Next()) ++edges;
      const double expected = scenario == 3 ? 0. : 9.8729 * (4.53785605518526 - 4.52772714604059);
      bool pass = edges == (scenario == 3 ? 0 : 1) && std::abs(props.Mass() - expected) < 1e-6;
      std::cout << scenario << " swap=" << swap << " edges=" << edges
                << " length=" << props.Mass() << " pass=" << pass << std::endl;
      failures += !pass;
    }
  }
  return failures > 0;
}
