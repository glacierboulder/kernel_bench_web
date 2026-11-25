#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepCheck_Analyzer.hxx>
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
#include <limits>
#include <stdexcept>

namespace
{
constexpr double Side = 10;
constexpr double Radius = 4.99;
constexpr double PositionTol = 1e-7;
constexpr double AreaTol = 1e-6;
constexpr double VolumeTol = 1e-4;
const double Pi = std::acos(-1.0);

void Require(bool ok, const char* reason)
{
  if (!ok)
    throw std::runtime_error(reason);
}

bool Near(double a, double b, double tolerance = PositionTol)
{
  return std::abs(a - b) <= tolerance;
}

TopoDS_Shape Read(const char* path)
{
  BRep_Builder builder;
  TopoDS_Shape shape;
  Require(BRepTools::Read(shape, path, builder) && !shape.IsNull(), "BREP read failed");
  return shape;
}

using Segment = std::array<gp_Pnt, 2>;

Segment Ends(const TopoDS_Edge& edge)
{
  Require(!BRep_Tool::Degenerated(edge) && BRepAdaptor_Curve(edge).GetType() == GeomAbs_Line,
          "expected non-degenerate straight edge");
  TopoDS_Vertex start, end;
  TopExp::Vertices(edge, start, end);
  Require(!start.IsNull() && !end.IsNull(), "edge endpoints unavailable");
  return {BRep_Tool::Pnt(start), BRep_Tool::Pnt(end)};
}

bool Matches(const Segment& edge, const gp_Pnt& a, const gp_Pnt& b)
{
  return (edge[0].Distance(a) <= PositionTol && edge[1].Distance(b) <= PositionTol)
      || (edge[0].Distance(b) <= PositionTol && edge[1].Distance(a) <= PositionTol);
}

TopoDS_Shape Native(double top, double bottom)
{
  const TopoDS_Shape box = BRepPrimAPI_MakeBox(Side, Side, Side).Shape();
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> edges;
  // Preserve the registered traversal order and the two original Add calls.
  for (TopExp_Explorer edge(box, TopAbs_EDGE); edge.More(); edge.Next())
    edges.Add(edge.Current());
  Require(edges.Extent() == 12, "registered box edge inventory");
  const auto high = TopoDS::Edge(edges(10));
  const auto low = TopoDS::Edge(edges(9));
  Require(Matches(Ends(high), gp_Pnt(0, 0, Side), gp_Pnt(Side, 0, Side))
          && Matches(Ends(low), gp_Pnt(0, 0, 0), gp_Pnt(Side, 0, 0)), "wrong registered edges");
  std::cout << "INPUT top=10 bottom=9\n";
  BRepFilletAPI_MakeFillet fillet(box);
  fillet.Add(top, high);
  fillet.Add(bottom, low);
  fillet.Build();
  Require(fillet.IsDone(), "registered two-edge fillet did not complete");
  return fillet.Shape();
}

bool Quarter(const BRepAdaptor_Surface& surface, double radius, bool upper)
{
  if (surface.GetType() != GeomAbs_Cylinder)
    return false;
  const auto cylinder = surface.Cylinder();
  const double sign = upper ? -1 : 1;
  const double originalZ = upper ? Side : 0;
  const double u0 = surface.FirstUParameter();
  const double u1 = surface.LastUParameter();
  const double v0 = surface.FirstVParameter();
  const double v1 = surface.LastVParameter();
  if (!Near(cylinder.Radius(), radius)
      || !Near(cylinder.Location().Y(), radius)
      || !Near(cylinder.Location().Z(), originalZ + sign * radius)
      || !Near(std::abs(cylinder.Axis().Direction().X()), 1)
      || !Near(u1 - u0, Pi / 2) || !Near(v1 - v0, Side))
    return false;
  const double mid = radius * (1 - 1 / std::sqrt(2.0));
  const std::array<std::array<double, 2>, 3> offsets{{{radius, 0}, {0, radius}, {mid, mid}}};
  for (double x : {0.0, Side})
    for (const auto& offset : offsets)
    {
      bool measured = false;
      const gp_Pnt expected(x, offset[0], originalZ + sign * offset[1]);
      for (double u : {u0, (u0 + u1) / 2, u1})
        for (double v : {v0, v1})
          measured |= expected.Distance(surface.Value(u, v)) <= PositionTol;
      if (!measured)
        return false;
    }
  return true;
}

struct Strip
{
  double low, high, area;
};

Strip Rectangle(const TopoDS_Face& face)
{
  std::array<Segment, 4> edges;
  std::size_t count = 0;
  double low = std::numeric_limits<double>::infinity();
  double high = -low;
  for (TopExp_Explorer edge(face, TopAbs_EDGE); edge.More(); edge.Next())
  {
    Require(count < edges.size(), "front has more than four edges");
    auto& segment = edges[count++];
    segment = Ends(TopoDS::Edge(edge.Current()));
    for (const gp_Pnt& endpoint : segment)
    {
      low = std::min(low, endpoint.Z());
      high = std::max(high, endpoint.Z());
    }
  }
  Require(count == 4 && high - low > PositionTol, "front has no rectangular boundary");
  const std::array<gp_Pnt, 4> corners{gp_Pnt(0, 0, low), gp_Pnt(Side, 0, low),
                                     gp_Pnt(Side, 0, high), gp_Pnt(0, 0, high)};
  for (std::size_t i = 0; i < corners.size(); ++i)
    Require(std::count_if(edges.begin(), edges.end(), [&](const Segment& edge) {
      return Matches(edge, corners[i], corners[(i+1) % corners.size()]);
    }) == 1, "front edge extents do not cover the rectangle");
  GProp_GProps area;
  BRepGProp::SurfaceProperties(face, area);
  Require(Near(area.Mass(), Side * (high - low), AreaTol), "front area and edges disagree");
  return {low, high, area.Mass()};
}

void Check(const char* role, const TopoDS_Shape& shape, double top, double bottom, bool frontExpected,
           bool widthExpected, bool centerExpected)
{
  Require(!shape.IsNull() && BRepCheck_Analyzer(shape).IsValid(), "invalid result");
  TopExp_Explorer solids(shape, TopAbs_SOLID);
  Require(solids.More(), "missing solid");
  solids.Next();
  Require(!solids.More(), "extra solid");
  int cylinders = 0;
  int lowMatches = 0;
  int highMatches = 0;
  TopoDS_Face front;
  for (TopExp_Explorer face(shape, TopAbs_FACE); face.More(); face.Next())
  {
    const auto current = TopoDS::Face(face.Current());
    const BRepAdaptor_Surface surface(current);
    if (surface.GetType() == GeomAbs_Cylinder)
    {
      ++cylinders;
      const bool lower = Quarter(surface, bottom, false);
      const bool upper = Quarter(surface, top, true);
      Require(lower != upper, "unmatched or ambiguous cylindrical face");
      lowMatches += lower;
      highMatches += upper;
      const auto cylinder = surface.Cylinder();
      std::cout << "CYLINDER " << role << ' ' << (lower ? "low" : "high") << ' '
                << cylinder.Radius() << ' ' << cylinder.Location().Y() << ' '
                << cylinder.Location().Z() << '\n';
    }
    else if (surface.GetType() == GeomAbs_Plane)
    {
      const gp_Pln plane = surface.Plane();
      if (Near(std::abs(plane.Axis().Direction().Y()), 1) && Near(plane.Location().Y(), 0))
      {
        Require(front.IsNull(), "duplicate front faces");
        front = current;
      }
    }
    else
      Require(false, "unexpected face type");
  }
  Require(cylinders == 2 && lowMatches == 1 && highMatches == 1, "two analytic quarter cylinders required");
  GProp_GProps mass;
  BRepGProp::VolumeProperties(shape, mass);
  const double volume = mass.Mass();
  Require(Near(volume, Side*Side*Side - Side * (1 - Pi/4) * (top*top+bottom*bottom), VolumeTol),
          "unexpected volume for actual radii");
  const bool exists = !front.IsNull();
  Require(exists == frontExpected, "wrong existence of front strip");
  if (!exists)
  {
    std::cout << "CONTROL " << role << " exists=0 width_ok=NA center_ok=NA endpoints_ok=NA"
              << " volume=" << volume << '\n';
    return;
  }

  const auto strip = Rectangle(front);
  Require(Near(strip.low, bottom) && Near(strip.high, Side - top), "front does not reach the actual tangent ends");
  const double width = strip.high - strip.low;
  const double center = (strip.low + strip.high) / 2;
  const bool widthOk = Near(width, Side - 2*Radius);
  const bool centerOk = Near(center, Side / 2);
  const bool endpointsOk = Near(strip.low, Radius) && Near(strip.high, Side - Radius);
  Require(widthOk == widthExpected && centerOk == centerExpected
          && endpointsOk == (widthExpected && centerExpected), "nominal strip verdict differs");
  std::cout << "CONTROL " << role << " exists=1 width_ok=" << widthOk
            << " center_ok=" << centerOk << " endpoints_ok=" << endpointsOk
            << " low=" << strip.low << " high=" << strip.high << " width=" << width
            << " center=" << center << " area=" << strip.area << " volume=" << volume << '\n';
}
}

int main(int argc, char** argv)
{
  if (argc != 7)
    return 2;
  try
  {
    std::cout << std::setprecision(17);
    std::ifstream config(argv[1]);
    double top, bottom;
    Require(bool(config >> top >> bottom) && Near(top, Radius) && Near(bottom, Radius),
            "use the registered gap radii");
    Check("native", Native(top, bottom), top, bottom, true, true, true);
    Check("healthy-1", Read(argv[2]), top, bottom, true, true, true);
    Check("healthy-2", Read(argv[3]), top, bottom, true, true, true);
    Check("missing", Read(argv[4]), 5, 5, false, false, false);
    Check("wide", Read(argv[5]), 4.98, 4.98, true, false, true);
    Check("shifted", Read(argv[6]), 4.994, 4.986, true, true, false);
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
