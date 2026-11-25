#include <BRepAdaptor_Surface.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
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
#include <TopoDS_Face.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Cylinder.hxx>
#include <gp_Pln.hxx>
#include <array>
#include <cmath>
#include <fstream>
#include <string>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace
{
constexpr double Side = 20;
constexpr double Radius = 1;
constexpr double SpatialTolerance = 1e-7;
constexpr double VolumeTolerance = 1e-5;
const double Pi = std::acos(-1.0);

void Require(bool theCondition, const char* theMessage)
{
  if (!theCondition)
    throw std::runtime_error(theMessage);
}

bool Near(double theLeft, double theRight, double theTolerance = SpatialTolerance)
{
  return std::abs(theLeft - theRight) <= theTolerance;
}

TopoDS_Shape Read(const char* theFile)
{
  BRep_Builder aBuilder;
  TopoDS_Shape aShape;
  Require(BRepTools::Read(aShape, theFile, aBuilder) && !aShape.IsNull(), "failed BREP read");
  return aShape;
}

TopoDS_Shape Native()
{
  const TopoDS_Shape aBox = BRepPrimAPI_MakeBox(Side, Side, Side).Shape();
  NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> anEdges;
  TopExp::MapShapes(aBox, TopAbs_EDGE, anEdges);
  Require(anEdges.Extent() == 12, "box edge topology");
  const TopoDS_Edge anEdge = TopoDS::Edge(anEdges(1));
  const gp_Pnt aFirst = BRep_Tool::Pnt(TopExp::FirstVertex(anEdge));
  const gp_Pnt aLast = BRep_Tool::Pnt(TopExp::LastVertex(anEdge));
  Require(Near(aFirst.X(), 0) && Near(aFirst.Y(), 0) && Near(aLast.X(), 0) && Near(aLast.Y(), 0)
            && ((Near(aFirst.Z(), 0) && Near(aLast.Z(), Side))
                || (Near(aLast.Z(), 0) && Near(aFirst.Z(), Side))), "registered edge 1 geometry changed");
  BRepFilletAPI_MakeFillet anOperation(aBox);
  anOperation.Add(Radius, anEdge);
  anOperation.Build();
  Require(anOperation.IsDone(), "box fillet did not complete");
  return anOperation.Shape();
}

bool HasQuarter(const BRepAdaptor_Surface& theSurface, double theCorner)
{
  const gp_Cylinder aCylinder = theSurface.Cylinder();
  const double aSense = theCorner == 0 ? 1 : -1;
  const double aCenter = theCorner + aSense * Radius;
  const double aLow = theSurface.FirstUParameter();
  const double aHigh = theSurface.LastUParameter();
  const double aBottom = theSurface.FirstVParameter();
  const double aTop = theSurface.LastVParameter();
  Require(aBottom < aTop && aLow < aHigh, "invalid cylinder limits");
  if (!Near(aCylinder.Location().X(), aCenter) || !Near(aCylinder.Location().Y(), aCenter)
      || !Near(aCylinder.Radius(), Radius) || !Near(std::abs(aCylinder.Axis().Direction().Z()), 1)
      || !Near(aHigh - aLow, Pi / 2) || !Near(aTop - aBottom, Side))
    return false;
  const double aDiagonal = Radius * (1 - 1 / std::sqrt(2.0));
  for (double aZ : {0.0, Side})
  {
    for (const auto& anOffset : {std::array<double, 2>{0, Radius}, {Radius, 0}, {aDiagonal, aDiagonal}})
    {
      const gp_Pnt aPoint(theCorner + aSense * anOffset[0], theCorner + aSense * anOffset[1], aZ);
      bool aFound = false;
      for (double aU : {aLow, (aLow + aHigh) / 2, aHigh})
        for (double aV : {aBottom, aTop})
          aFound |= aPoint.Distance(theSurface.Value(aU, aV)) <= SpatialTolerance;
      if (!aFound)
        return false;
    }
  }
  return true;
}

bool Material(const gp_Pnt& thePoint, double theCorner)
{
  if (thePoint.X() < 0 || thePoint.X() > Side
      || thePoint.Y() < 0 || thePoint.Y() > Side || thePoint.Z() < 0 || thePoint.Z() > Side)
    return false;
  const double aU = std::abs(theCorner - thePoint.X());
  const double aV = std::abs(theCorner - thePoint.Y());
  return aU >= Radius || aV >= Radius || std::hypot(Radius - aU, Radius - aV) < Radius;
}

void Check(const char* theRole, const TopoDS_Shape& theShape, bool theOpposite)
{
  Require(BRepCheck_Analyzer(theShape).IsValid(), "invalid output");
  TopExp_Explorer aSolid(theShape, TopAbs_SOLID);
  Require(aSolid.More(), "output has no solid");
  BRepClass3d_SolidClassifier aClassifier(aSolid.Current());
  aSolid.Next();
  Require(!aSolid.More(), "output has multiple solids");
  std::array<int, 6> aPlanes{};
  int aCylinders = 0;
  bool atTarget = false;
  bool atOpposite = false;
  for (TopExp_Explorer aFace(theShape, TopAbs_FACE); aFace.More(); aFace.Next())
  {
    BRepAdaptor_Surface aSurface(TopoDS::Face(aFace.Current()));
    if (aSurface.GetType() == GeomAbs_Cylinder)
    {
      ++aCylinders;
      atTarget = HasQuarter(aSurface, 0);
      atOpposite = HasQuarter(aSurface, Side);
      std::cout << "AXIS " << theRole << ' ' << aSurface.Cylinder().Location().X()
                << ' ' << aSurface.Cylinder().Location().Y() << '\n';
      continue;
    }
    Require(aSurface.GetType() == GeomAbs_Plane, "unexpected face type");
    const gp_Pln aPlane = aSurface.Plane();
    bool aExpected = false;
    for (int i = 1; i <= 3; ++i)
    {
      if (!Near(std::abs(aPlane.Axis().Direction().Coord(i)), 1))
        continue;
      for (int j = 0; j <= 1; ++j)
      {
        if (Near(aPlane.Location().Coord(i), j * Side))
        {
          ++aPlanes[(i - 1) * 2 + j];
          aExpected = true;
        }
      }
    }
    Require(aExpected, "unexpected supporting plane");
  }
  Require(aCylinders == 1 && aPlanes == std::array<int, 6>{1, 1, 1, 1, 1, 1}, "unexpected faces");
  GProp_GProps aProperties;
  BRepGProp::VolumeProperties(theShape, aProperties);
  const double aReference = Side * Side * Side - Side * Radius * Radius * (1 - Pi / 4);
  Require(Near(aProperties.Mass(), aReference, VolumeTolerance), "volume differs from analytic fillet");
  int aTargetWrong = 0;
  int anOppositeWrong = 0;
  int aWitnessCount = 0;
  auto inspect = [&](const gp_Pnt& thePoint)
  {
    aClassifier.Perform(thePoint, SpatialTolerance);
    const auto aState = aClassifier.State();
    Require(aState == TopAbs_IN || aState == TopAbs_OUT, "material witness on unknown boundary");
    const bool isInside = aState == TopAbs_IN;
    aTargetWrong += isInside != Material(thePoint, 0);
    anOppositeWrong += isInside != Material(thePoint, Side);
    ++aWitnessCount;
    std::cout << "WITNESS " << theRole << ' ' << thePoint.X() << ' ' << thePoint.Y()
              << ' ' << thePoint.Z() << ' ' << isInside << '\n';
  };
  for (double aZ : {2.0, 10.0, 18.0})
    for (double anX : {0.0, Side})
      for (double aY : {0.0, Side})
        for (double anInset : {0.1, 0.5})
          inspect(gp_Pnt(anX == 0 ? anInset : Side - anInset,
                         aY == 0 ? anInset : Side - anInset, aZ));
  inspect(gp_Pnt(10, 10, 10));
  inspect(gp_Pnt(-2, 10, 10));
  std::cout << "CONTROL " << theRole << " target=" << atTarget << " opposite=" << atOpposite
            << " witnesses=" << aWitnessCount << " wrong_target=" << aTargetWrong
            << " wrong_opposite=" << anOppositeWrong << " volume=" << aProperties.Mass() << '\n';
  Require(atTarget != theOpposite && atOpposite == theOpposite
            && aTargetWrong == (theOpposite ? 6 : 0)
            && anOppositeWrong == (theOpposite ? 0 : 6), "target/negative geometry mismatch");
}
}

int main(int argc, char** argv)
{
  if (argc != 6)
    return 2;
  try
  {
    std::cout << std::setprecision(17);
    Require(BRepCheck_Analyzer(Read(argv[1])).IsValid(), "registered input BREP is invalid");
    std::ifstream aMode(argv[2]);
    std::string aName;
    Require(bool(aMode >> aName) && aName == "box", "registered mode is not box");
    constexpr std::array<const char*, 3> Roles{"healthy-1", "healthy-2", "opposite"};
    Check("native", Native(), false);
    for (std::size_t i = 0; i < Roles.size(); ++i)
      Check(Roles[i], Read(argv[i + 3]), i == 2);
    std::cout << "TEST_DONE\n";
    return 0;
  }
  catch (const Standard_Failure& theError)
  {
    std::cerr << "OCCT exception: " << theError.what() << '\n';
  }
  catch (const std::exception& theError)
  {
    std::cerr << theError.what() << '\n';
  }
  return 1;
}
