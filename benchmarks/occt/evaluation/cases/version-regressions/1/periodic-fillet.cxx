#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeCone.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
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
#include <gp_Circ.hxx>
#include <gp_Torus.hxx>
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace
{
constexpr double FilletRadius = 4;
constexpr double Height = 50;
constexpr double SpatialTol = 1e-4;
constexpr double AngularTol = 1e-8;
const double Pi = std::acos(-1.0);

void Require(bool ok, const char* why)
{
  if (!ok) throw std::runtime_error(why);
}

bool Near(double a, double b, double tolerance = SpatialTol)
{
  return std::abs(a-b) <= tolerance;
}

struct Reference
{
  double base, slope, cap;
  double centerZ() const { return cap == 0 ? FilletRadius : Height-FilletRadius; }
  double lateral(double z) const { return base-slope*z; }
  double major() const { return lateral(centerZ())-FilletRadius*std::hypot(1.0,slope); }
  double tangencyZ() const { return centerZ()+FilletRadius*slope/std::hypot(1.0,slope); }
  double arc() const { return Pi/2+(cap == 0 ? 1 : -1)*std::atan(slope); }
  double section(double z) const
  {
    if (cap == 0 ? z >= tangencyZ() : z <= tangencyZ()) return lateral(z);
    const double t=z-centerZ();
    return major()+std::sqrt(std::max(0.0, FilletRadius*FilletRadius-t*t));
  }
  double volume() const
  {
    auto rounded = [&](double z) {
      const double t = z-centerZ(), m = major(), r = FilletRadius;
      return (m*m+r*r)*t-t*t*t/3+m*(t*std::sqrt(std::max(0.0,r*r-t*t))+r*r*std::asin(t/r));
    };
    auto original = [&](double z) {
      return base*base*z-base*slope*z*z+slope*slope*z*z*z/3;
    };
    const double join=tangencyZ();
    return Pi*(cap == 0 ? rounded(join)-rounded(0)+original(Height)-original(join)
                        : original(join)-original(0)+rounded(Height)-rounded(join));
  }
};

bool Circle(const BRepAdaptor_Curve& curve, double z, double radius)
{
  if (curve.GetType()!=GeomAbs_Circle) return false;
  const gp_Circ circle=curve.Circle();
  return circle.Location().Distance(gp_Pnt(0,0,z))<=SpatialTol
      && Near(std::abs(circle.Axis().Direction().Z()),1,AngularTol)
      && Near(circle.Radius(),radius)
      && Near(curve.LastParameter()-curve.FirstParameter(),2*Pi,AngularTol);
}

TopoDS_Shape Read(const char* path)
{
  TopoDS_Shape shape;
  BRep_Builder builder;
  Require(BRepTools::Read(shape,path,builder)&&!shape.IsNull(),"BREP read");
  return shape;
}

struct Measurements
{
  int solids=0, tori=0, splines=0, badMaterial=0;
  bool valid=false, axis=false, arc=false, boundaries=false;
  double z=0, major=0, volume=0;
};

Measurements Inspect(const TopoDS_Shape& result,const Reference& ref)
{
  Measurements m;
  m.valid=!result.IsNull() && BRepCheck_Analyzer(result).IsValid();
  for (TopExp_Explorer solid(result,TopAbs_SOLID);solid.More();solid.Next()) ++m.solids;
  GProp_GProps props;
  BRepGProp::VolumeProperties(result,props);
  m.volume=props.Mass();
  for (TopExp_Explorer face(result,TopAbs_FACE);face.More();face.Next())
  {
    const auto f=TopoDS::Face(face.Current());
    const BRepAdaptor_Surface surface(f);
    m.splines+=surface.GetType()==GeomAbs_BSplineSurface;
    if (surface.GetType()!=GeomAbs_Torus) continue;
    ++m.tori;
    const auto torus=surface.Torus();
    m.z=torus.Location().Z();
    m.major=torus.MajorRadius();
    m.axis=torus.Location().Distance(gp_Pnt(0,0,ref.centerZ()))<=SpatialTol
        && Near(std::abs(torus.Axis().Direction().Z()),1,AngularTol)
        && Near(m.major,ref.major()) && Near(torus.MinorRadius(),FilletRadius);
    m.arc=Near(surface.LastUParameter()-surface.FirstUParameter(),2*Pi,AngularTol)
        && Near(surface.LastVParameter()-surface.FirstVParameter(),ref.arc(),AngularTol);
    int seams=0, cap=0, lateral=0, others=0;
    for (TopExp_Explorer e(f,TopAbs_EDGE);e.More();e.Next())
    {
      const auto edge=TopoDS::Edge(e.Current());
      if (BRep_Tool::IsClosed(edge,f)) { ++seams; continue; }
      const BRepAdaptor_Curve curve(edge);
      const bool onCap=Circle(curve,ref.cap,ref.major());
      const bool onSide=Circle(curve,ref.tangencyZ(),ref.lateral(ref.tangencyZ()));
      cap+=onCap;
      lateral+=onSide;
      others+=!onCap&&!onSide;
    }
    m.boundaries=seams==2&&cap==1&&lateral==1&&others==0;
  }
  BRepClass3d_SolidClassifier classifier(result);
  for (double z : {0.125,1.0,2.0,3.5,4.25,6.0,25.0,44.0,46.1,47.0,48.5,49.875})
    for (double theta : {0.0,Pi/4,Pi,3*Pi/2})
      for (double delta : {-0.025,0.025})
      {
        const double rho=ref.section(z)+delta;
        classifier.Perform(gp_Pnt(rho*std::cos(theta),rho*std::sin(theta),z),1e-7);
        m.badMaterial+=classifier.State()!=(delta<0 ? TopAbs_IN : TopAbs_OUT);
      }
  return m;
}

void Nominal(const char* label, const char* role, const TopoDS_Shape& shape, const Reference& reference)
{
  const auto m=Inspect(shape,reference);
  Require(m.valid&&m.solids==1&&m.tori==1&&m.splines==0&&m.axis&&m.arc&&m.boundaries
       &&m.badMaterial==0&&Near(m.volume,reference.volume()),"actual fillet misses the analytic end geometry");
  std::cout<<"CONTROL "<<label<<' '<<role<<" healthy=1 material=96 center_z="<<m.z
           <<" major="<<m.major<<" volume="<<m.volume<<'\n';
}
}

int main(int argc,char**argv)
{
  if (argc!=5) return 2;
  try
  {
    std::cout<<std::setprecision(17);
    const std::array<TopoDS_Shape,2> inputs{BRepPrimAPI_MakeCylinder(20,50).Shape(),
                                           BRepPrimAPI_MakeCone(25,12,50).Shape()};
    for (std::size_t i=0;i<inputs.size();++i)
    {
      const auto& input=inputs[i];
      NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher> edges;
      TopExp::MapShapes(input,TopAbs_EDGE,edges);
      std::array<bool,2> seen{};
      for (int e=1;e<=edges.Extent();++e)
      {
        const auto edge=TopoDS::Edge(edges(e));
        const BRepAdaptor_Curve circle(edge);
        if (circle.GetType()!=GeomAbs_Circle) continue;
        const bool top=circle.Circle().Location().Z()>25;
        const Reference ref{i==0?20.0:25.0,i==0?0.0:0.26,top?50.0:0.0};
        const char* label=i==0 ? (top?"cylinder-top":"cylinder-bottom") : (top?"cone-top":"cone-bottom");
        Require(!seen[top]&&Circle(circle,ref.cap,ref.lateral(ref.cap)),"registered circular input edge");
        seen[top]=true;
        BRepFilletAPI_MakeFillet fillet(input,ChFi3d_Rational);
        fillet.Add(FilletRadius,edge);
        fillet.Build();
        Require(fillet.IsDone(),"registered fillet failed");
        Nominal(label,"native",fillet.Shape(),ref);
        const auto archived=Read(argv[1+2*i+!top]);
        Nominal(label,"frozen",archived,ref);
        const auto wrong=Inspect(Read(argv[1+2*i+top]),ref);
        Require(wrong.valid&&wrong.solids==1&&wrong.tori==1&&wrong.splines==0
             &&!wrong.axis&&!wrong.boundaries&&wrong.badMaterial>0
             &&Near(wrong.z,Height-ref.centerZ()),"existing other-cap result did not test end location");
        std::cout<<"CONTROL "<<label<<" opposite rejected=1 center_z="<<wrong.z
                 <<" material_errors="<<wrong.badMaterial<<" volume="<<wrong.volume<<'\n';
      }
      Require(seen[0]&&seen[1],"both registered circular ends");
    }
    std::cout<<"TEST_DONE\n";
    return 0;
  }
  catch(const Standard_Failure& error){std::cerr<<error.what()<<'\n';}
  catch(const std::exception& error){std::cerr<<error.what()<<'\n';}
  return 1;
}
