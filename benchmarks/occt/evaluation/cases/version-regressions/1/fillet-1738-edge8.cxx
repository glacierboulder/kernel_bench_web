#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
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
#include <TopoDS_Edge.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Circ.hxx>
#include <gp_Cylinder.hxx>
#include <gp_Pln.hxx>
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace
{
constexpr double Radius = 0.8;
constexpr double GeometryTol = 1e-5;
constexpr double VolumeTol = 1e-4;
constexpr double AxisY = -30 + Radius;
constexpr double AxisZ = Radius;
const double Pi = std::acos(-1.);
using Ends = std::array<gp_Pnt, 2>;

bool Near(double a, double b) { return std::abs(a - b) <= GeometryTol; }

TopoDS_Shape Read(const char* path)
{
  TopoDS_Shape s;
  BRep_Builder builder;
  if (!BRepTools::Read(s, path, builder) || s.IsNull()) throw std::runtime_error("BREP read failed");
  return s;
}

Ends EndPoints(const TopoDS_Edge& e)
{
  TopoDS_Vertex a, b;
  TopExp::Vertices(e, a, b);
  if (a.IsNull() || b.IsNull()) throw std::runtime_error("edge endpoints unavailable");
  return {BRep_Tool::Pnt(a), BRep_Tool::Pnt(b)};
}

bool Matches(const Ends& ends, const gp_Pnt& a, const gp_Pnt& b)
{
  return (ends[0].Distance(a) <= GeometryTol && ends[1].Distance(b) <= GeometryTol)
      || (ends[0].Distance(b) <= GeometryTol && ends[1].Distance(a) <= GeometryTol);
}

int Count(const TopoDS_Shape& shape, TopAbs_ShapeEnum type)
{
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> shapes;
  TopExp::MapShapes(shape, type, shapes);
  return shapes.Extent();
}

double Volume(const TopoDS_Shape& shape)
{
  GProp_GProps props;
  BRepGProp::VolumeProperties(shape, props);
  return props.Mass();
}

TopoDS_Edge VerifyInput(const TopoDS_Shape& input, double targetVolume)
{
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> edges;
  TopExp::MapShapes(input, TopAbs_EDGE, edges);
  const gp_Pnt start(-30,-30,0), end(30,-30,0);
  int matched = 0, index = 0;
  for (int i = 1; i <= edges.Extent(); ++i)
  {
    const auto edge = TopoDS::Edge(edges(i));
    if (BRepAdaptor_Curve(edge).GetType() == GeomAbs_Line && Matches(EndPoints(edge), start, end))
    {
      ++matched;
      index = i;
    }
  }
  if (matched != 1 || index != 8) throw std::runtime_error("unique geometric edge 8 unavailable");
  int adjacent = 0, floor = 0, wall = 0;
  for (TopExp_Explorer faces(input, TopAbs_FACE); faces.More(); faces.Next())
  {
    const auto face = TopoDS::Face(faces.Current());
    for (TopExp_Explorer e(face, TopAbs_EDGE); e.More(); e.Next())
    {
      if (!e.Current().IsSame(edges(index))) continue;
      ++adjacent;
      const BRepAdaptor_Surface surface(face);
      if (surface.GetType() != GeomAbs_Plane) continue;
      const auto plane = surface.Plane();
      const auto n = plane.Axis().Direction();
      floor += Near(std::abs(n.Z()), 1) && plane.Distance(start) <= GeometryTol;
      wall += Near(std::abs(n.Y()), 1) && plane.Distance(start) <= GeometryTol;
    }
  }
  const double volume = Volume(input);
  std::cout << "INPUT index=8 span=60 adjacent=" << adjacent << " floor=" << floor
            << " wall=" << wall << " volume=" << volume << '\n';
  if (adjacent != 2 || floor != 1 || wall != 1 || Count(input, TopAbs_SOLID) != 1
      || !BRepCheck_Analyzer(input).IsValid() || std::abs(volume - targetVolume) > VolumeTol)
    throw std::runtime_error("input does not match the analytic fixture");
  return TopoDS::Edge(edges(index));
}

bool TrimMatches(const TopoDS_Face& face, double angle, double span)
{
  if (!Near(angle, Pi / 2) || !Near(span, 60) || Count(face, TopAbs_WIRE) != 1) return false;
  int sideWall = 0, sideFloor = 0, firstCap = 0, lastCap = 0, edges = 0;
  for (TopExp_Explorer e(face, TopAbs_EDGE); e.More(); e.Next())
  {
    ++edges;
    const auto edge = TopoDS::Edge(e.Current());
    const BRepAdaptor_Curve curve(edge);
    const auto ends = EndPoints(edge);
    if (curve.GetType() == GeomAbs_Line)
    {
      sideWall += Matches(ends, gp_Pnt(-30,-30,Radius), gp_Pnt(30,-30,Radius));
      sideFloor += Matches(ends, gp_Pnt(-30,AxisY,0), gp_Pnt(30,AxisY,0));
    }
    if (curve.GetType() == GeomAbs_Circle)
    {
      const auto circle = curve.Circle();
      const auto center = circle.Location();
      if (!Near(std::abs(circle.Axis().Direction().X()), 1) || !Near(center.Y(), AxisY)
          || !Near(center.Z(), AxisZ) || !Near(circle.Radius(), Radius)
          || !Near(curve.LastParameter() - curve.FirstParameter(), Pi / 2)) continue;
      const double x = center.X();
      if (!Matches(ends, gp_Pnt(x,-30,Radius), gp_Pnt(x,AxisY,0))) continue;
      firstCap += Near(x, -30);
      lastCap += Near(x, 30);
    }
  }
  std::cout << "BOUNDARY edges=" << edges << " wall=" << sideWall << " floor=" << sideFloor
            << " x_min=" << firstCap << " x_max=" << lastCap << '\n';
  return edges == 4 && sideWall == 1 && sideFloor == 1 && firstCap == 1 && lastCap == 1;
}

struct Cylinders
{
  int radiusMatches = 0, positionMatches = 0, trimMatches = 0;
};

Cylinders InspectSurface(const TopoDS_Shape& shape)
{
  Cylinders result;
  for (TopExp_Explorer fs(shape, TopAbs_FACE); fs.More(); fs.Next())
  {
    const auto face = TopoDS::Face(fs.Current());
    const BRepAdaptor_Surface surface(face);
    if (surface.GetType() != GeomAbs_Cylinder) continue;
    const auto cylinder = surface.Cylinder();
    if (!Near(cylinder.Radius(), Radius)) continue;
    ++result.radiusMatches;
    const auto center = cylinder.Location();
    const auto direction = cylinder.Axis().Direction();
    const double angle = surface.LastUParameter() - surface.FirstUParameter();
    const double span = surface.LastVParameter() - surface.FirstVParameter();
    const bool atTarget = Near(std::abs(direction.X()), 1) && Near(center.Y(), AxisY) && Near(center.Z(), AxisZ);
    result.positionMatches += atTarget;
    if (atTarget) result.trimMatches += TrimMatches(face, angle, span);
    std::cout << "CYLINDER y=" << center.Y() << " z=" << center.Z() << " x_axis=" << direction.X()
              << " radius=" << cylinder.Radius() << " angle=" << angle << " span=" << span << '\n';
  }
  return result;
}

TopAbs_State State(BRepClass3d_SolidClassifier& classifier, const gp_Pnt& point)
{
  classifier.Perform(point, 1e-7);
  return classifier.State();
}

struct Witness
{
  gp_Pnt point;
  TopAbs_State state;
};

std::array<int, 3> InspectMaterial(const TopoDS_Shape& input, const TopoDS_Shape& actual)
{
  BRepClass3d_SolidClassifier initial(input), observed(actual);
  int removed = 0, preserved = 0, remote = 0;
  for (double x : {-24., -12., 0., 12., 24.})
  {
    const double cut = (Radius + .04) / std::sqrt(2.);
    const double keep = (Radius - .04) / std::sqrt(2.);
    const gp_Pnt cutPoint(x, AxisY - cut, AxisZ - cut);
    const gp_Pnt keepPoint(x, AxisY - keep, AxisZ - keep);
    if (State(initial, cutPoint) != TopAbs_IN || State(initial, keepPoint) != TopAbs_IN)
      throw std::runtime_error("input does not contain the pre-fillet material");
    removed += State(observed, cutPoint) == TopAbs_OUT;
    preserved += State(observed, keepPoint) == TopAbs_IN;
  }
  const std::array<Witness, 6> distant{{
    {gp_Pnt(0,-20,50), TopAbs_IN}, {gp_Pnt(0,-5,106), TopAbs_IN},
    {gp_Pnt(0,-22,105), TopAbs_OUT}, {gp_Pnt(31,-10,50), TopAbs_OUT},
    {gp_Pnt(27,-5,112), TopAbs_IN}, {gp_Pnt(27,-5,116), TopAbs_OUT}
  }};
  for (const auto& w : distant)
  {
    if (State(initial, w.point) != w.state) throw std::runtime_error("invalid distant material witness");
    remote += State(observed, w.point) == w.state;
  }
  return {removed, preserved, remote};
}

bool Score(const char* role, const TopoDS_Shape& input, const TopoDS_Shape& output,
           double originalVolume, double expectedRemoval)
{
  std::cout << "CASE " << role << '\n';
  const auto cylinders = InspectSurface(output);
  const bool valid = BRepCheck_Analyzer(output).IsValid();
  const int solids = Count(output, TopAbs_SOLID);
  const auto material = InspectMaterial(input, output);
  const double actualRemoval = originalVolume - Volume(output);
  std::cout << "OUTPUT valid=" << valid << " solids=" << solids << " radius_matches=" << cylinders.radiusMatches
            << " target_matches=" << cylinders.positionMatches << " trim_matches=" << cylinders.trimMatches
            << " removed_witnesses=" << material[0] << " kept_witnesses=" << material[1]
            << " remote_witnesses=" << material[2] << " removal=" << actualRemoval << '\n';
  const bool pass = valid && solids == 1 && cylinders.radiusMatches == 1
                 && cylinders.positionMatches == 1 && cylinders.trimMatches == 1
                 && material == std::array<int, 3>{5, 5, 6}
                 && std::abs(actualRemoval - expectedRemoval) <= VolumeTol;
  std::cout << "VERDICT " << role << ' ' << (pass ? "PASS" : "FAIL") << '\n';
  return pass;
}
}

int main(int argc, char** argv)
{
  if (argc != 4) return 2;
  try
  {
    std::cout << std::setprecision(17);
    const auto input = Read(argv[1]);
    const double originalVolume = 60 * 30 * 100 + 15 * Pi * 30 * 30 / 2;
    const double expectedRemoval = 60 * Radius * Radius * (1 - Pi / 4);
    const auto target = VerifyInput(input, originalVolume);
    const std::filesystem::path liveFile("/workspace/gh1738-edge8-live.brep");
    if (std::filesystem::exists(liveFile))
      throw std::runtime_error("live output path must be new");

    // Match the archived GH-1738 parameters, operating only on the qualified edge 8.
    BRepFilletAPI_MakeFillet fillet(input);
    fillet.SetParams(1e-2, 1e-4, 1e-5, 1e-4, 1e-5, 1e-3);
    fillet.SetContinuity(GeomAbs_C1, 1e-2);
    fillet.Add(Radius, target);
    fillet.Build();
    if (!fillet.IsDone() || fillet.Shape().IsNull())
    {
      std::cout << "EDGE8_BUILD_FAILED\n";
      return 1;
    }
    if (!BRepTools::Write(fillet.Shape(), liveFile.c_str()))
      throw std::runtime_error("live BREP write failed");
    std::cout << "LIVE_BREP edge=8 bytes=" << std::filesystem::file_size(liveFile) << '\n';

    // All three cases use the same geometry decision on a re-read BREP.
    const bool live = Score("live", input, Read(liveFile.c_str()), originalVolume, expectedRemoval);
    const bool frozen = Score("frozen", input, Read(argv[2]), originalVolume, expectedRemoval);
    const bool wrong = Score("wrong-edge", input, Read(argv[3]), originalVolume, expectedRemoval);
    if (!live || !frozen || wrong) return 1;
    std::cout << "TEST_DONE\n";
    return 0;
  }
  catch (const Standard_Failure& error) { std::cerr << error.what() << '\n'; }
  catch (const std::exception& error) { std::cerr << error.what() << '\n'; }
  return 2;
}
