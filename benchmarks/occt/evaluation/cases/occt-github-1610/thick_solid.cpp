#include <cstdio>
#include <cmath>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepOffsetAPI_ThruSections.hxx>
#include <BRepOffset_MakeOffset.hxx>
#include <BRepOffset_Error.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepBuilderAPI_MakePolygon.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <Geom_Circle.hxx>
#include <Geom_Ellipse.hxx>
#include <Geom_BSplineCurve.hxx>
#include <Geom_TrimmedCurve.hxx>
#include <GeomAPI_PointsToBSpline.hxx>
#include <gp_Ax2.hxx>
#include <gp_Circ.hxx>
#include <gp_Elips.hxx>
#include <gp_Pnt.hxx>
#include <NCollection_Array1.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Shape.hxx>
#include <TopoDS_Wire.hxx>
#include <TopExp_Explorer.hxx>
#include <NCollection_List.hxx>
static TopoDS_Wire MakeCircularWire(const gp_Pnt& theCenter,
                                    const gp_Dir& theNormal,
                                    double        theRadius)
{
  gp_Ax2  anAxis(theCenter, theNormal);
  gp_Circ aCirc(anAxis, theRadius);

  BRepBuilderAPI_MakeEdge anEdgeMaker(aCirc);
  if (!anEdgeMaker.IsDone())
  {
    return TopoDS_Wire();
  }

  BRepBuilderAPI_MakeWire aWireMaker(anEdgeMaker.Edge());
  if (!aWireMaker.IsDone())
  {
    return TopoDS_Wire();
  }

  return aWireMaker.Wire();
}
static TopoDS_Wire MakePolygonalWire(const gp_Pnt& theCenter,
                                     const gp_Dir& theNormal,
                                     double        theRadius,
                                     int           theNbSides)
{
  gp_Ax2 anAxis(theCenter, theNormal);
  gp_Dir aXDir = anAxis.XDirection();
  gp_Dir aYDir = anAxis.YDirection();

  BRepBuilderAPI_MakePolygon aPolygon;

  for (int i = 0; i <= theNbSides; ++i)
  {
    double anAngle = 2.0 * M_PI * i / theNbSides;
    gp_Pnt aPnt    = theCenter.Translated(gp_Vec(aXDir) * theRadius * cos(anAngle)
                                       + gp_Vec(aYDir) * theRadius * sin(anAngle));
    aPolygon.Add(aPnt);
  }

  aPolygon.Close();

  if (!aPolygon.IsDone())
  {
    return TopoDS_Wire();
  }

  return aPolygon.Wire();
}
int main()
{
  gp_Pnt aCircleCenter(0, 0, 0);
  gp_Dir aNormal(0, 0, 1);

  TopoDS_Wire aCircleWire = MakeCircularWire(aCircleCenter, aNormal, 50.0);
  if (aCircleWire.IsNull()) return 2;

  gp_Pnt      anOctCenter(0, 0, 100);
  TopoDS_Wire anOctWire = MakePolygonalWire(anOctCenter, aNormal, 55.0, 8);
  if (anOctWire.IsNull()) return 2;

  BRepOffsetAPI_ThruSections aLoftMaker(true, false);
  aLoftMaker.AddWire(aCircleWire);
  aLoftMaker.AddWire(anOctWire);
  aLoftMaker.Build();

  if (!aLoftMaker.IsDone()) return 3;

  TopoDS_Shape aLoftShape = aLoftMaker.Shape();

  NCollection_List<TopoDS_Shape> aFacesToRemove;
  BRepOffsetAPI_MakeThickSolid   aThickMaker;

  aThickMaker.MakeThickSolidByJoin(aLoftShape,
                                   aFacesToRemove,
                                   2.0,
                                   1.0e-3,
                                   BRepOffset_Skin,
                                   false,
                                   false,
                                   GeomAbs_Intersection);
  aThickMaker.Build();

  // Octagon is closer to a circle, corners are less sharp
  std::printf("done=%d\n", aThickMaker.IsDone()); return aThickMaker.IsDone() ? 0 : 4;
}
