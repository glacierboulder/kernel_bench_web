#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Cylinder.hxx>
#include <gp_Pln.hxx>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace
{
constexpr double Side = 10;
constexpr double Radius = 1;
constexpr double Tol = 1e-7;
const double Pi = std::acos(-1.0);

void Require(bool condition, const char* reason)
{
  if (!condition)
    throw std::runtime_error(reason);
}

bool Near(double a, double b)
{
  return std::abs(a - b) <= Tol;
}

TopoDS_Shape Read(const char* path)
{
  BRep_Builder builder;
  TopoDS_Shape shape;
  Require(BRepTools::Read(shape, path, builder) && !shape.IsNull(), "BREP read failed");
  return shape;
}

void CheckEdge(const char* path, double corner)
{
  const TopoDS_Edge e = TopoDS::Edge(Read(path));
  Require(BRepAdaptor_Curve(e).GetType() == GeomAbs_Line, "expected straight input edge");
  const TopoDS_Vertex a = TopExp::FirstVertex(e);
  const TopoDS_Vertex b = TopExp::LastVertex(e);
  Require(!a.IsNull() && !b.IsNull(), "input edge has missing endpoint");
  const gp_Pnt first = BRep_Tool::Pnt(a);
  const gp_Pnt last = BRep_Tool::Pnt(b);
  Require(Near(first.X(), corner) && Near(first.Y(), corner)
          && Near(last.X(), corner) && Near(last.Y(), corner)
          && ((Near(first.Z(), 0) && Near(last.Z(), Side))
              || (Near(first.Z(), Side) && Near(last.Z(), 0))), "wrong input edge endpoints");
}

bool HasQuarter(const BRepAdaptor_Surface& surface, double corner)
{
  const double sign = corner == 0 ? 1 : -1;
  const double center = corner + sign * Radius;
  const gp_Cylinder cylinder = surface.Cylinder();
  const double u0 = surface.FirstUParameter();
  const double u1 = surface.LastUParameter();
  const double v0 = surface.FirstVParameter();
  const double v1 = surface.LastVParameter();
  if (!Near(cylinder.Location().X(), center) || !Near(cylinder.Location().Y(), center)
      || !Near(std::abs(cylinder.Axis().Direction().Z()), 1)
      || !Near(cylinder.Radius(), Radius) || !Near(u1 - u0, Pi / 2) || !Near(v1 - v0, Side))
    return false;
  const double diagonal = Radius * (1 - 1 / std::sqrt(2.0));
  const std::array<std::array<double, 2>, 3> offsets{{{0, Radius}, {Radius, 0}, {diagonal, diagonal}}};
  for (const double z : {0.0, Side})
    for (const auto& offset : offsets)
    {
      const gp_Pnt point(corner + sign * offset[0], corner + sign * offset[1], z);
      bool found = false;
      for (const double u : {u0, (u0 + u1) / 2, u1})
        for (const double v : {v0, v1})
          found |= point.Distance(surface.Value(u, v)) <= Tol;
      if (!found)
        return false;
    }
  return true;
}

bool Material(const gp_Pnt& point, double corner)
{
  if (point.X() < 0 || point.X() > Side || point.Y() < 0 || point.Y() > Side
      || point.Z() < 0 || point.Z() > Side)
    return false;
  const double u = std::abs(point.X() - corner);
  const double v = std::abs(point.Y() - corner);
  return u >= Radius || v >= Radius || std::hypot(Radius-u, Radius-v) < Radius;
}

void Grade(const char* role, const TopoDS_Shape& shape)
{
  Require(BRepCheck_Analyzer(shape).IsValid(), "invalid solid");
  TopExp_Explorer solids(shape, TopAbs_SOLID);
  Require(solids.More(), "missing solid");
  BRepClass3d_SolidClassifier classifier(solids.Current());
  solids.Next();
  Require(!solids.More(), "extra solid");
  std::array<int, 6> planes{};
  int cylinderCount = 0;
  bool target = false;
  bool opposite = false;
  for (TopExp_Explorer face(shape, TopAbs_FACE); face.More(); face.Next())
  {
    const BRepAdaptor_Surface surface(TopoDS::Face(face.Current()));
    if (surface.GetType() == GeomAbs_Cylinder)
    {
      ++cylinderCount;
      target = HasQuarter(surface, 0);
      opposite = HasQuarter(surface, Side);
      std::cout << "AXIS " << role << ' ' << surface.Cylinder().Location().X()
                << ' ' << surface.Cylinder().Location().Y() << '\n';
      continue;
    }
    Require(surface.GetType() == GeomAbs_Plane, "unexpected surface");
    const gp_Pln plane = surface.Plane();
    int axis = 1;
    while (axis <= 3 && !Near(std::abs(plane.Axis().Direction().Coord(axis)), 1))
      ++axis;
    Require(axis <= 3, "oblique box plane");
    const int side = Near(plane.Location().Coord(axis), 0) ? 0 : 1;
    Require(Near(plane.Location().Coord(axis), side * Side), "misplaced box plane");
    ++planes[2 * (axis - 1) + side];
  }
  Require(cylinderCount == 1 && (target || opposite) && target != opposite
          && planes == std::array<int, 6>{1, 1, 1, 1, 1, 1}, "unexpected fillet boundaries");
  GProp_GProps area, volume;
  BRepGProp::SurfaceProperties(shape, area);
  BRepGProp::VolumeProperties(shape, volume);
  const double loss = 1 - Pi / 4;
  Require(std::abs(area.Mass() - (600 - 22 * loss)) < 0.02
          && std::abs(volume.Mass() - (1000 - 10 * loss)) < 1e-5, "inconsistent bulk geometry");

  int wrongTarget = 0;
  int wrongOpposite = 0;
  int count = 0;
  auto witness = [&](const gp_Pnt& point)
  {
    classifier.Perform(point, Tol);
    const auto state = classifier.State();
    Require(state == TopAbs_IN || state == TopAbs_OUT, "undefined material witness");
    const bool inside = state == TopAbs_IN;
    wrongTarget += inside != Material(point, 0);
    wrongOpposite += inside != Material(point, Side);
    ++count;
    std::cout << "MATERIAL " << role << ' ' << point.X() << ' ' << point.Y()
              << ' ' << point.Z() << ' ' << inside << '\n';
  };
  for (double z : {2.0, 5.0, 8.0})
    for (double x : {0.0, Side})
      for (double y : {0.0, Side})
        for (double inset : {0.1, 0.5})
          witness(gp_Pnt(x == 0 ? inset : Side - inset, y == 0 ? inset : Side - inset, z));
  witness(gp_Pnt(5, 5, 5));
  witness(gp_Pnt(-2, 5, 5));
  Require((target && wrongTarget == 0 && wrongOpposite == 6)
          || (opposite && wrongTarget == 6 && wrongOpposite == 0), "material placement mismatch");
  std::cout << "CONTROL " << role << " target=" << target << " opposite=" << opposite
            << " witnesses=" << count << " wrong_target=" << wrongTarget
            << " wrong_opposite=" << wrongOpposite << " area=" << area.Mass()
            << " volume=" << volume.Mass() << '\n';
}
}

int main(int argc, char** argv)
{
  if (argc != 7)
    return 2;
  try
  {
    std::cout << std::setprecision(17);
    CheckEdge(argv[1], 0);
    CheckEdge(argv[2], Side);
    std::cout << "INPUT target=1 opposite=7\n";
    constexpr std::array<const char*, 4> roles{"native", "healthy-1", "healthy-2", "opposite"};
    for (std::size_t i = 0; i < roles.size(); ++i)
      Grade(roles[i], Read(argv[i + 3]));
    return 0;
  }
  catch (const Standard_Failure& error)
  {
    std::cerr << error.GetMessageString() << '\n';
  }
  catch (const std::exception& error)
  {
    std::cerr << error.what() << '\n';
  }
  return 1;
}
