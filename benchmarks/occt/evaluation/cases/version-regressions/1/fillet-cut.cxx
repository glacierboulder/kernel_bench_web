#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <NCollection_IndexedMap.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Cylinder.hxx>
#include <gp_Pln.hxx>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
constexpr double Tol = 1e-7;
constexpr double SurfaceTol = 1e-5;
constexpr double VolumeTol = 0.01;
constexpr double Radius = 1.299;
constexpr double Pi = 3.14159265358979323846;
using ShapeMap = NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher>;

struct EdgeReference
{
  int index;
  double y;
  double z;
  double endX;
  double zSign;
};

constexpr EdgeReference Target{6, 5, 2.5, 4.50368903944272, 1};
constexpr EdgeReference Alternate{11, 0, 4, 3.2, -1};

void Require(bool ok, const char* message)
{
  if (!ok)
    throw std::runtime_error(message);
}

bool Near(double a, double b, double tolerance = Tol)
{
  return std::abs(a - b) <= tolerance;
}

TopoDS_Shape Read(const char* file)
{
  BRep_Builder builder;
  TopoDS_Shape shape;
  Require(BRepTools::Read(shape, file, builder) && !shape.IsNull(), "BREP read failure");
  return shape;
}

double Volume(const TopoDS_Shape& shape)
{
  GProp_GProps props;
  BRepGProp::VolumeProperties(shape, props);
  Require(std::isfinite(props.Mass()), "non-finite volume");
  return props.Mass();
}

void Valid(const TopoDS_Shape& shape, int count)
{
  Require(!shape.IsNull() && BRepCheck_Analyzer(shape).IsValid(), "invalid geometric output");
  int found = 0;
  for (TopExp_Explorer solid(shape, TopAbs_SOLID); solid.More(); solid.Next())
    ++found;
  Require(found == count, "unexpected solid count");
}

bool Inside(const TopoDS_Shape& shape, const gp_Pnt& point)
{
  bool ambiguous = false;
  for (TopExp_Explorer solid(shape, TopAbs_SOLID); solid.More(); solid.Next())
  {
    BRepClass3d_SolidClassifier judge(solid.Current());
    judge.Perform(point, Tol);
    if (judge.State() == TopAbs_IN)
      return true;
    ambiguous |= judge.State() != TopAbs_OUT;
  }
  Require(!ambiguous, "indeterminate material witness");
  return false;
}

bool IsSegment(const TopoDS_Edge& edge, const gp_Pnt& start, const gp_Pnt& end)
{
  const TopoDS_Vertex first = TopExp::FirstVertex(edge);
  const TopoDS_Vertex last = TopExp::LastVertex(edge);
  if (first.IsNull() || last.IsNull() || BRep_Tool::Degenerated(edge)
      || BRepAdaptor_Curve(edge).GetType() != GeomAbs_Line)
    return false;
  const gp_Pnt p = BRep_Tool::Pnt(first);
  const gp_Pnt q = BRep_Tool::Pnt(last);
  return (p.Distance(start) <= Tol && q.Distance(end) <= Tol)
      || (p.Distance(end) <= Tol && q.Distance(start) <= Tol);
}

void CheckEdge(const TopoDS_Shape& shape, const ShapeMap& edges, const EdgeReference& ref)
{
  Require(edges.Extent() >= ref.index, "input edge index missing");
  const TopoDS_Edge edge = TopoDS::Edge(edges(ref.index));
  Require(IsSegment(edge, gp_Pnt(0, ref.y, ref.z), gp_Pnt(ref.endX, ref.y, ref.z)),
          "input edge endpoints or curve type changed");
  int faces = 0;
  int yPlanes = 0;
  int zPlanes = 0;
  for (TopExp_Explorer face(shape, TopAbs_FACE); face.More(); face.Next())
    for (TopExp_Explorer member(face.Current(), TopAbs_EDGE); member.More(); member.Next())
    {
      if (!member.Current().IsSame(edge))
        continue;
      const BRepAdaptor_Surface support(TopoDS::Face(face.Current()));
      Require(support.GetType() == GeomAbs_Plane, "junction support is not planar");
      const gp_Pln plane = support.Plane();
      ++faces;
      yPlanes += Near(std::abs(plane.Axis().Direction().Y()), 1) && Near(plane.Location().Y(), ref.y);
      zPlanes += Near(std::abs(plane.Axis().Direction().Z()), 1) && Near(plane.Location().Z(), ref.z);
      break;
    }
  Require(faces == 2 && yPlanes == 1 && zPlanes == 1, "junction has different incident planes");
}

bool IsBlend(const BRepAdaptor_Surface& surface, const EdgeReference& ref)
{
  if (surface.GetType() != GeomAbs_Cylinder)
    return false;
  const gp_Cylinder cylinder = surface.Cylinder();
  const double dx = cylinder.Axis().Direction().X();
  if (!Near(std::abs(dx), 1, SurfaceTol) || !Near(cylinder.Radius(), Radius, SurfaceTol)
      || !Near(cylinder.Location().Y(), ref.y + Radius, SurfaceTol)
      || !Near(cylinder.Location().Z(), ref.z + ref.zSign * Radius, SurfaceTol)
      || !Near(surface.LastUParameter() - surface.FirstUParameter(), Pi / 2, SurfaceTol))
    return false;
  const double x0 = cylinder.Location().X() + dx * surface.FirstVParameter();
  const double x1 = cylinder.Location().X() + dx * surface.LastVParameter();
  return std::min(x0, x1) <= 0.6 + SurfaceTol && std::max(x0, x1) >= 2.5 - SurfaceTol;
}

struct Witness
{
  std::string name;
  char kind;
  gp_Pnt point;
  std::array<bool, 3> expected;
};

std::vector<Witness> ReadWitnesses(const char* path)
{
  std::ifstream stream(path);
  std::vector<Witness> result;
  std::set<std::string> names;
  std::string name;
  while (stream >> name)
  {
    char kind;
    double x, y, z;
    int original, target, alternate;
    Require(bool(stream >> kind >> x >> y >> z >> original >> target >> alternate)
            && (kind == 'S' || kind == 'M') && names.insert(name).second
            && std::isfinite(x) && std::isfinite(y) && std::isfinite(z)
            && (original == 0 || original == 1) && (target == 0 || target == 1)
            && (alternate == 0 || alternate == 1), "invalid witness row");
    result.push_back({name, kind, gp_Pnt(x, y, z), {bool(original), bool(target), bool(alternate)}});
  }
  Require(stream.eof() && result.size() == 107, "incomplete witness file");
  return result;
}

struct FilletMeasurements
{
  std::array<int, 3> errors{};
  std::vector<bool> material;
  int targetFaces = 0;
  int alternateFaces = 0;
};

FilletMeasurements Fillet(const TopoDS_Shape& shape, const std::vector<Witness>& witnesses)
{
  Valid(shape, 1);
  FilletMeasurements m;
  BRep_Builder builder;
  TopoDS_Compound skin;
  builder.MakeCompound(skin);
  for (TopExp_Explorer face(shape, TopAbs_FACE); face.More(); face.Next())
  {
    builder.Add(skin, face.Current());
    const BRepAdaptor_Surface surface(TopoDS::Face(face.Current()));
    m.targetFaces += IsBlend(surface, Target);
    m.alternateFaces += IsBlend(surface, Alternate);
  }
  for (const auto& w : witnesses)
  {
    bool actual;
    if (w.kind == 'S')
    {
      BRepExtrema_DistShapeShape distance(BRepBuilderAPI_MakeVertex(w.point).Vertex(), skin);
      Require(distance.IsDone() && std::isfinite(distance.Value()) && distance.Value() >= 0,
              "trimmed boundary distance unavailable");
      actual = distance.Value() <= SurfaceTol;
    }
    else
    {
      actual = Inside(shape, w.point);
      m.material.push_back(actual);
    }
    for (std::size_t i = 0; i < m.errors.size(); ++i)
      m.errors[i] += actual != w.expected[i];
  }
  Require(m.material.size() == 89, "material witness count");
  return m;
}

using Interval = std::array<double, 2>;

bool BoxBoundary(const TopoDS_Shape& shape, const Interval& z)
{
  const std::array<Interval, 3> bounds{Interval{0, 10}, Interval{0, 10}, z};
  std::set<std::pair<int, int>> found;
  for (TopExp_Explorer face(shape, TopAbs_FACE); face.More(); face.Next())
  {
    const BRepAdaptor_Surface surf(TopoDS::Face(face.Current()));
    if (surf.GetType() != GeomAbs_Plane)
      return false;
    const gp_Pln plane = surf.Plane();
    int axis = 1;
    while (axis <= 3 && !Near(std::abs(plane.Axis().Direction().Coord(axis)), 1))
      ++axis;
    if (axis > 3)
      return false;
    const auto& line = bounds[axis - 1];
    const int side = Near(plane.Location().Coord(axis), line[0]) ? 0 : 1;
    if (!Near(plane.Location().Coord(axis), line[side]) || !found.insert({axis, side}).second)
      return false;
    const int u = axis % 3 + 1;
    const int v = (axis + 1) % 3 + 1;
    std::array<gp_Pnt, 4> corners;
    for (int i = 0; i < 4; ++i)
    {
      corners[i].SetCoord(axis, line[side]);
      corners[i].SetCoord(u, bounds[u - 1][i == 1 || i == 2]);
      corners[i].SetCoord(v, bounds[v - 1][i >= 2]);
    }
    std::set<int> segments;
    for (TopExp_Explorer element(face.Current(), TopAbs_EDGE); element.More(); element.Next())
    {
      const TopoDS_Edge edge = TopoDS::Edge(element.Current());
      int i = 0;
      while (i < 4 && !IsSegment(edge, corners[i], corners[(i + 1) % 4]))
        ++i;
      if (i == 4 || !segments.insert(i).second)
        return false;
    }
    if (segments.size() != 4)
      return false;
  }
  return found.size() == 6;
}

TopoDS_Shape Cut(const TopoDS_Shape& left, const TopoDS_Shape& right)
{
  BRepAlgoAPI_Cut op(left, right);
  Require(op.IsDone() && !op.Shape().IsNull(), "Cut did not complete");
  return op.Shape();
}

bool InSlab(const gp_Pnt& p, const Interval& z)
{
  return 0 < p.X() && p.X() < 10 && 0 < p.Y() && p.Y() < 10 && z[0] < p.Z() && p.Z() < z[1];
}

void Check(const char* role, const TopoDS_Shape& fillet, const TopoDS_Shape& remainder,
           const TopoDS_Shape& frozenRemoved, const std::vector<Witness>& witnesses,
           bool wrongEdge, bool wrongCut)
{
  const auto m = Fillet(fillet, witnesses);
  Require(m.targetFaces == int(!wrongEdge) && m.alternateFaces == int(wrongEdge)
          && m.errors[wrongEdge ? 2 : 1] == 0 && m.errors[1] == (wrongEdge ? 24 : 0),
          "fillet localization verdict");
  Valid(remainder, 2);
  const TopoDS_Shape removed = Cut(fillet, remainder);
  Valid(removed, 1);
  const double removedMass = Volume(removed);
  const double balance = Volume(fillet) - Volume(remainder) - removedMass;
  Require(Near(removedMass, 100, VolumeTol) && Near(balance, 0, VolumeTol), "mass balance");
  const Interval wanted{1, 2};
  const Interval actual = wrongCut ? Interval{0.25, 1.25} : wanted;
  Require(BoxBoundary(removed, actual) && BoxBoundary(removed, wanted) == !wrongCut,
          "actual removed box support planes or four-edge face boundaries");
  if (!frozenRemoved.IsNull())
  {
    Valid(frozenRemoved, 1);
    Require(BoxBoundary(frozenRemoved, actual) && Near(Volume(frozenRemoved), removedMass, VolumeTol),
            "frozen removal does not match the actual removed box");
  }

  std::size_t materialIndex = 0;
  int cutErrors = 0;
  int removalErrors = 0;
  for (const auto& w : witnesses)
  {
    if (w.kind != 'M')
      continue;
    const bool before = m.material[materialIndex++];
    const bool kept = Inside(remainder, w.point);
    const bool gone = Inside(removed, w.point);
    Require(kept == (before && !InSlab(w.point, actual))
            && gone == (before && InSlab(w.point, actual)), "inconsistent kept or removed material");
    if (!frozenRemoved.IsNull())
      Require(gone == Inside(frozenRemoved, w.point), "frozen removal material mismatch");
    const bool expectedGone = before && InSlab(w.point, wanted);
    cutErrors += kept != (before && !expectedGone);
    removalErrors += gone != expectedGone;
  }
  Require(cutErrors == (wrongCut ? 37 : 0) && removalErrors == cutErrors,
          "wrong-layer material witness count");
  std::cout << "CONTROL " << role << " fillet_errors=" << m.errors[1]
            << " target_faces=" << m.targetFaces << " alternate_faces=" << m.alternateFaces
            << " cut_errors=" << cutErrors << " removed_errors=" << removalErrors
            << " z_low=" << actual[0] << " z_high=" << actual[1]
            << " removed_volume=" << removedMass << " balance=" << balance << '\n';
}
}

int main(int argc, char** argv)
{
  if (argc != 16)
    return 2;
  try
  {
    std::cout << std::setprecision(17);
    std::ifstream config(argv[2]);
    std::string mode, role;
    double radius;
    int first, second;
    Require(bool(config >> mode >> role >> radius >> first >> second)
            && mode == "1701" && role == "smaller" && Near(radius, Radius)
            && first == Target.index && second == 0, "use the registered 1701-smaller parameters");
    const auto witnesses = ReadWitnesses(argv[3]);
    const TopoDS_Shape input = Read(argv[1]);
    ShapeMap edges;
    TopExp::MapShapes(input, TopAbs_EDGE, edges);
    CheckEdge(input, edges, Target);
    CheckEdge(input, edges, Alternate);
    const auto baseline = Fillet(input, witnesses);
    Require(baseline.errors[0] == 0 && baseline.targetFaces == 0 && baseline.alternateFaces == 0,
            "material reference is not applicable to the frozen input");
    std::cout << "INPUT edge=6 alternate=11 witnesses=" << witnesses.size() << '\n';

    BRepFilletAPI_MakeFillet op(input);
    op.Add(radius, TopoDS::Edge(edges(first)));
    op.Build();
    Require(op.IsDone(), "native fillet did not complete");
    const TopoDS_Shape fillet = op.Shape();
    Check("native", fillet, Cut(fillet, BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 1), 10, 10, 1).Shape()),
          TopoDS_Shape(), witnesses, false, false);
    constexpr std::array<const char*, 4> roles{"healthy-1", "healthy-2", "wrong-edge", "wrong-cut"};
    for (std::size_t i = 0; i < roles.size(); ++i)
      Check(roles[i], Read(argv[4 + 3*i]), Read(argv[5 + 3*i]), Read(argv[6 + 3*i]),
            witnesses, i == 2, i == 3);
    std::cout << "TEST_DONE\n";
    return 0;
  }
  catch (const Standard_Failure& error)
  {
    std::cerr << error.what() << '\n';
  }
  catch (const std::exception& error)
  {
    std::cerr << error.what() << '\n';
  }
  return 1;
}
