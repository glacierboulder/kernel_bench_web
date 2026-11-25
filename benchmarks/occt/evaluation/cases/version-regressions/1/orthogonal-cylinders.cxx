// Separate analytic control. Only these generated inputs are eligible.
#include <BRepAdaptor_Surface.hxx>
#include <BRepAlgoAPI_Common.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <gp_Cylinder.hxx>
#include <gp_Lin.hxx>
#include <gp_Pln.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

static const double radius=80.0, halfHeight=100.0;
struct Cylinder {
  TopoDS_Shape shape;
  gp_Dir axis;
  double measuredRadius=0;
};

static bool qualify(Cylinder& c, const gp_Dir& target, int id) {
  int sides=0;
  std::vector<double> caps;
  std::vector<gp_Pln> planes;
  gp_Pnt origin(0,0,0);
  double lineDistance=-1;
  for (TopExp_Explorer faces(c.shape,TopAbs_FACE); faces.More(); faces.Next()) {
    BRepAdaptor_Surface face(TopoDS::Face(faces.Current()));
    if (face.GetType()==GeomAbs_Cylinder) {
      const gp_Cylinder surf=face.Cylinder();
      c.axis=surf.Axis().Direction(); c.measuredRadius=surf.Radius();
      lineDistance=gp_Lin(surf.Axis()).Distance(origin);
      ++sides;
    } else if (face.GetType()==GeomAbs_Plane) {
      planes.push_back(face.Plane());
    } else return false;
  }
  for (const auto& plane: planes) {
    if (std::abs(plane.Axis().Direction().Dot(c.axis))!=1.0) return false;
    caps.push_back(gp_Vec(origin,plane.Location()).Dot(gp_Vec(c.axis)));
  }
  std::sort(caps.begin(),caps.end());
  if (caps.size()!=2 || sides!=1) return false;
  const double mid=(caps[0]+caps[1])/2;
  const double clearance=std::min(-caps[0],caps[1])-radius;
  std::cout<<"CYL "<<id<<" "<<c.axis.X()<<" "<<c.axis.Y()<<" "<<c.axis.Z()<<" "
           <<c.measuredRadius<<" "<<lineDistance<<" "<<mid<<" "<<caps[0]<<" "<<caps[1]<<" "<<clearance<<"\n";
  return c.axis.Dot(target)==1.0 && c.measuredRadius==radius && lineDistance==0.0 &&
      mid==0.0 && caps[0]==-halfHeight && caps[1]==halfHeight && clearance>0.0;
}

static bool measure(const TopoDS_Shape& s,double expected,const char* label) {
  TopTools_IndexedMapOfShape solids;
  TopExp::MapShapes(s,TopAbs_SOLID,solids);
  GProp_GProps props;
  BRepGProp::VolumeProperties(s,props,1.e-9);
  const bool valid=BRepCheck_Analyzer(s).IsValid();
  std::cout<<"SHAPE "<<label<<" "<<solids.Extent()<<" "<<valid<<" "<<props.Mass()<<" "<<expected<<"\n";
  return solids.Extent()==1 && valid && std::abs(props.Mass()-expected)<=expected*2.e-6;
}
int main(int argc,char** argv) {
  if (argc!=3) return 2;
  std::cout<<std::setprecision(17);
  const std::array<gp_Dir,3> axes={{gp_Dir(1,0,0),gp_Dir(0,0,1),gp_Dir(0,-1,0)}};
  std::array<Cylinder,3> cylinders;
  for(int i=0;i<3;++i) {
    const gp_Pnt base(-halfHeight*axes[i].X(),-halfHeight*axes[i].Y(),-halfHeight*axes[i].Z());
    cylinders[i].shape=BRepPrimAPI_MakeCylinder(gp_Ax2(base,axes[i]),radius,2*halfHeight).Shape();
    if(!qualify(cylinders[i],axes[i],i)) return 3;
  }
  for(int i=0;i<3;++i) for(int j=i+1;j<3;++j) {
    const double dot=cylinders[i].axis.Dot(cylinders[j].axis);
    std::cout<<"DOT "<<i<<" "<<j<<" "<<dot<<"\n";
    if(dot!=0) return 3;
  }
  std::cout<<"ELIGIBLE generated-r80-orthogonal\n";
  BRepAlgoAPI_Common first(cylinders[0].shape,cylinders[1].shape);
  if(!first.IsDone()) return 4;
  const double two = 16.0/3.0*std::pow(radius,3);
  const double three = 8.0*(2.0-std::sqrt(2.0))*std::pow(radius,3);
  if (!measure(first.Shape(),two,"first")) return 1;
  BRepAlgoAPI_Common second(first.Shape(),cylinders[2].shape);
  if (!second.IsDone() || !measure(second.Shape(),three,"native")) return 1;
  BRep_Builder builder;
  TopoDS_Shape healthy, dropped;
  if (!BRepTools::Read(healthy,argv[1],builder) || !BRepTools::Read(dropped,argv[2],builder)) return 3;
  if (!measure(healthy,three,"healthy") || !measure(dropped,two,"dropped_first_result")
      || measure(dropped,three,"missing_third")) return 1;
  std::cout << "healthy pass\nnegative missing_third\nTEST_DONE\n";
  return 0;
}
