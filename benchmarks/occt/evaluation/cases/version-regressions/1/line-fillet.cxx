#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepExtrema_DistShapeShape.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
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
#include <stdexcept>
#include <string>

namespace
{
constexpr double RodRadius = 1.6;
constexpr double PlateHalf = 1.25;
constexpr double Radius = 1.3;
constexpr double HalfY = 42.4781811688397;
constexpr double IdentityTolerance = 1e-7;
constexpr double SurfaceTolerance = 1e-5;
constexpr double WitnessOffset = 0.01;
constexpr std::array<double, 7> Sections{-42, -25, 0, 25, 42, -45, 45};
using ShapeMap = NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher>;

void Require(bool ok, const char* message)
{
  if (!ok)
    throw std::runtime_error(message);
}

bool Near(double a, double b, double tolerance = IdentityTolerance)
{
  return std::abs(a - b) <= tolerance;
}

double BlendX()
{
  return -std::sqrt(std::pow(RodRadius + Radius, 2) - std::pow(PlateHalf + Radius, 2));
}

double BlendSweep()
{
  return std::atan2(-BlendX(), PlateHalf + Radius);
}

TopoDS_Shape Read(const char* path)
{
  BRep_Builder builder;
  TopoDS_Shape shape;
  Require(BRepTools::Read(shape, path, builder) && !shape.IsNull(), "BREP read failed");
  return shape;
}

bool HasSupport(const BRepAdaptor_Surface& support, int side, GeomAbs_SurfaceType type)
{
  if (support.GetType() != type)
    return false;
  if (type == GeomAbs_Plane)
  {
    const gp_Pln plane = support.Plane();
    return Near(plane.Location().Z(), side * PlateHalf)
        && Near(std::abs(plane.Axis().Direction().Z()), 1);
  }
  const gp_Cylinder rod = support.Cylinder();
  return Near(rod.Radius(), RodRadius) && Near(rod.Location().X(), 0)
      && Near(rod.Location().Z(), 0) && Near(std::abs(rod.Axis().Direction().Y()), 1);
}

int Junction(const TopoDS_Shape& shape, const ShapeMap& edges, int side)
{
  const double x = -std::sqrt(RodRadius * RodRadius - PlateHalf * PlateHalf);
  const gp_Pnt start(x, -HalfY, side * PlateHalf);
  const gp_Pnt end(x, HalfY, side * PlateHalf);
  int match = 0;
  for (int i = 1; i <= edges.Extent(); ++i)
  {
    const TopoDS_Edge edge = TopoDS::Edge(edges(i));
    const TopoDS_Vertex a = TopExp::FirstVertex(edge);
    const TopoDS_Vertex b = TopExp::LastVertex(edge);
    if (a.IsNull() || b.IsNull() || BRep_Tool::Degenerated(edge)
        || BRepAdaptor_Curve(edge).GetType() != GeomAbs_Line)
      continue;
    const gp_Pnt p = BRep_Tool::Pnt(a);
    const gp_Pnt q = BRep_Tool::Pnt(b);
    if (!((p.Distance(start) <= IdentityTolerance && q.Distance(end) <= IdentityTolerance)
          || (q.Distance(start) <= IdentityTolerance && p.Distance(end) <= IdentityTolerance)))
      continue;

    int faces = 0;
    int planes = 0;
    int cylinders = 0;
    for (TopExp_Explorer face(shape, TopAbs_FACE); face.More(); face.Next())
    {
      for (TopExp_Explorer member(face.Current(), TopAbs_EDGE); member.More(); member.Next())
      {
        if (!member.Current().IsSame(edge))
          continue;
        const BRepAdaptor_Surface support(TopoDS::Face(face.Current()));
        ++faces;
        planes += HasSupport(support, side, GeomAbs_Plane);
        cylinders += HasSupport(support, side, GeomAbs_Cylinder);
        break;
      }
    }
    Require(faces == 2 && planes == 1 && cylinders == 1 && match == 0,
            "junction is not unique on the analytic plane and rod");
    match = i;
  }
  return match;
}

gp_Pnt OnBlend(int side, double y, double fraction, double normalOffset = 0)
{
  const double theta = BlendSweep() * fraction;
  return gp_Pnt(BlendX() + (Radius + normalOffset) * std::sin(theta), y,
                side * (PlateHalf + Radius - (Radius + normalOffset) * std::cos(theta)));
}

bool IsInside(BRepClass3d_SolidClassifier& classifier, const gp_Pnt& point)
{
  classifier.Perform(point, IdentityTolerance);
  const auto state = classifier.State();
  Require(state == TopAbs_IN || state == TopAbs_OUT, "indeterminate material witness");
  return state == TopAbs_IN;
}

struct SideResult
{
  double minDistance = 1e9;
  double maxDistance = 0;
  int onSkin = 0;
  int fillCount = 0;
  int elsewhereWrong = 0;
  int filletFaces = 0;
  int sharpEdge = 0;
};

void Check(const char* role, const TopoDS_Shape& shape, int modifiedSide)
{
  Require(!shape.IsNull() && BRepCheck_Analyzer(shape).IsValid(), "invalid result");
  TopExp_Explorer solids(shape, TopAbs_SOLID);
  Require(solids.More(), "no solid");
  BRepClass3d_SolidClassifier classifier(solids.Current());
  solids.Next();
  Require(!solids.More(), "extra solid");

  BRep_Builder builder;
  TopoDS_Compound skin;
  builder.MakeCompound(skin);
  int faces = 0;
  std::array<SideResult, 2> sides{};
  for (TopExp_Explorer face(shape, TopAbs_FACE); face.More(); face.Next())
  {
    builder.Add(skin, face.Current());
    ++faces;
    const BRepAdaptor_Surface surf(TopoDS::Face(face.Current()));
    if (surf.GetType() != GeomAbs_Cylinder || !Near(surf.Cylinder().Radius(), Radius, SurfaceTolerance))
      continue;
    const gp_Cylinder fillet = surf.Cylinder();
    const double dy = fillet.Axis().Direction().Y();
    const double y0 = fillet.Location().Y() + dy * surf.FirstVParameter();
    const double y1 = fillet.Location().Y() + dy * surf.LastVParameter();
    const int side = fillet.Location().Z() < 0 ? -1 : 1;
    Require(Near(fillet.Location().X(), BlendX(), SurfaceTolerance)
            && Near(fillet.Location().Z(), side * (PlateHalf + Radius), SurfaceTolerance)
            && Near(std::abs(dy), 1, SurfaceTolerance)
            && Near(std::min(y0, y1), -HalfY, SurfaceTolerance)
            && Near(std::max(y0, y1), HalfY, SurfaceTolerance)
            && Near(surf.LastUParameter() - surf.FirstUParameter(), BlendSweep(), SurfaceTolerance),
            "unexpected fillet cylinder location or extent");
    ++sides[side > 0].filletFaces;
    std::cout << "AXIS " << role << ' ' << side << ' ' << fillet.Location().X() << ' '
              << fillet.Location().Z() << ' ' << std::min(y0, y1) << ' ' << std::max(y0, y1)
              << ' ' << surf.LastUParameter() - surf.FirstUParameter() << '\n';
  }

  ShapeMap edges;
  TopExp::MapShapes(shape, TopAbs_EDGE, edges);
  for (int side : {-1, 1})
  {
    auto& result = sides[side > 0];
    result.sharpEdge = Junction(shape, edges, side);
    for (const double y : Sections)
    {
      const bool interior = std::abs(y) < HalfY;
      if (interior)
      {
        for (const double fraction : {0.25, 0.5, 0.75})
        {
          BRepExtrema_DistShapeShape distance(BRepBuilderAPI_MakeVertex(OnBlend(side, y, fraction)).Vertex(), skin);
          Require(distance.IsDone() && std::isfinite(distance.Value()) && distance.Value() >= 0,
                  "distance to the trimmed boundary unavailable");
          result.minDistance = std::min(result.minDistance, distance.Value());
          result.maxDistance = std::max(result.maxDistance, distance.Value());
          result.onSkin += distance.Value() <= SurfaceTolerance;
        }
      }
      const bool fill = IsInside(classifier, OnBlend(side, y, 0.5, WitnessOffset));
      const bool outside = IsInside(classifier, OnBlend(side, y, 0.5, -WitnessOffset));
      result.fillCount += interior && fill;
      result.elsewhereWrong += outside + (!interior && fill);
      std::cout << "MATERIAL " << role << ' ' << side << ' ' << y
                << " fill=" << fill << " void=" << outside << '\n';
    }
    std::cout << "SIDE " << role << ' ' << side << " on_skin=" << result.onSkin
              << " min=" << result.minDistance << " max=" << result.maxDistance
              << " fill_count=" << result.fillCount << " elsewhere_wrong=" << result.elsewhereWrong
              << " fillet_faces=" << result.filletFaces << " sharp_edge=" << result.sharpEdge << '\n';
    const bool changed = side == modifiedSide;
    Require(result.onSkin == (changed ? 15 : 0) && result.fillCount == (changed ? 5 : 0)
            && result.elsewhereWrong == 0 && result.filletFaces == int(changed)
            && bool(result.sharpEdge) != changed, "material or straight junction at the wrong side");
  }

  const std::array<gp_Pnt, 8> remote{
      gp_Pnt(-10, 0, 0), gp_Pnt(-10, 0, 2), gp_Pnt(-10, 0, -2), gp_Pnt(0, 0, 0),
      gp_Pnt(4, 0, 0), gp_Pnt(0, 45, 0), gp_Pnt(0, -45, 0), gp_Pnt(0, 52, 0)};
  const std::array<bool, 8> expected{true, false, false, true, false, true, true, false};
  for (std::size_t i = 0; i < remote.size(); ++i)
    Require(IsInside(classifier, remote[i]) == expected[i], "unrelated material changed");
  GProp_GProps props;
  BRepGProp::VolumeProperties(shape, props);
  Require(std::isfinite(props.Mass()) && props.Mass() > 0, "invalid volume");
  const int wrongAgainstTarget = 5 - sides[0].fillCount + sides[1].fillCount;
  std::cout << "CONTROL " << role << " changed_side=" << modifiedSide
            << " wrong_target=" << wrongAgainstTarget << " fixed=8 faces=" << faces
            << " volume=" << props.Mass() << '\n';
}
}

int main(int argc, char** argv)
{
  if (argc != 6)
    return 2;
  std::cout << std::setprecision(17);
  try
  {
    std::ifstream config(argv[2]);
    std::string mode, role;
    double radius;
    int first, second;
    Require(bool(config >> mode >> role >> radius >> first >> second) && mode == "1702"
            && role == "line" && Near(radius, Radius) && first == 11 && second == 0,
            "the registered line configuration changed");
    const TopoDS_Shape input = Read(argv[1]);
    ShapeMap edges;
    TopExp::MapShapes(input, TopAbs_EDGE, edges);
    Require(Junction(input, edges, -1) == first && Junction(input, edges, 1) == 41,
            "registered and alternate edge identities changed");
    Check("input", input, 0);
    BRepFilletAPI_MakeFillet op(input);
    op.Add(radius, TopoDS::Edge(edges(first)));
    op.Build();
    Require(op.IsDone(), "native single-edge fillet failed");
    Check("native", op.Shape(), -1);
    Check("healthy-1", Read(argv[3]), -1);
    Check("healthy-2", Read(argv[4]), -1);
    Check("wrong-edge", Read(argv[5]), 1);
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
