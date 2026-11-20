#pragma once
#include <BRepAdaptor_Surface.hxx>
#include <BRepAlgoAPI_Common.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass_FaceClassifier.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Iterator.hxx>
#include <gp_Pln.hxx>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace slice_v2 {
struct Case { gp_Trsf move; double z; const char* gold; };
inline Case makeCase(bool healthy) {
  gp_Trsf move;
  if (!healthy) move.SetTranslation(gp_Vec(17,-13,0));
  return {move,healthy?.001:0.,healthy?"plus-gold.txt":"zero-gold.txt"};
}
inline bool check(const Case& c, TopoDS_Shape result) {
  while (!result.IsNull() && result.ShapeType()==TopAbs_COMPOUND) {
    TopoDS_Iterator it(result);
    if (!it.More()) { std::cout<<"empty result\n"; return false; }
    result=it.Value();
    it.Next();
    if (it.More()) {std::cout<<"extra components\n"; return false;}
  }
  if(result.IsNull() || result.ShapeType()!=TopAbs_FACE) {std::cout<<"missing face\n"; return false;}
  const auto face=TopoDS::Face(result);
  BRepAdaptor_Surface support(face);
  if(support.GetType()!=GeomAbs_Plane) return false;
  const auto plane=support.Plane();
  const auto origin=gp_Pnt(0,0,c.z).Transformed(c.move);
  const auto normal=gp_Dir(0,0,1).Transformed(c.move);
  const double distance=plane.Distance(origin), alignment=std::abs(plane.Axis().Direction().Dot(normal));
  std::ifstream gold(c.gold);
  double area,drift,z;
  if(!(gold>>area>>drift>>z) || z!=c.z || area<=0 || drift<0 || drift>=area*2.5e-5)
    throw std::runtime_error("invalid gold header");
  int n=0,wrong=0,expected;
  double x,y;
  while(gold>>x>>y>>expected) {
    if (expected!=0 && expected!=1) throw std::runtime_error("invalid witness class");
    BRepClass_FaceClassifier classify(face,gp_Pnt(x,y,z).Transformed(c.move),1e-6);
    if(classify.State()!=(expected?TopAbs_IN:TopAbs_OUT)) ++wrong;
    ++n;
  }
  if(!gold.eof() || n!=642) throw std::runtime_error("invalid witness file");
  GProp_GProps props;
  BRepGProp::SurfaceProperties(face,props,1e-8);
  const bool valid=BRepCheck_Analyzer(face).IsValid();
  std::cout<<std::setprecision(16)<<"area="<<props.Mass()<<" gold="<<area<<" drift="<<drift
           <<" normal_distance="<<distance<<" alignment="<<alignment<<" witnesses="<<n
           <<" wrong="<<wrong<<" valid="<<valid<<'\n';
  return valid && alignment>=1.-1e-12 && distance<=1e-6 && wrong==0 &&
         std::abs(props.Mass()-area)+2*drift<=area*1e-4;
}
inline int run(bool healthy, bool save=false) {
  const auto c=makeCase(healthy);
  std::ifstream file("fuselage-derived.brep");
  std::string header;
  std::getline(file,header);
  TopoDS_Shape solid;
  BRepTools::Read(solid,file,BRep_Builder());
  if(solid.IsNull()) throw std::runtime_error("missing fuselage");
  const gp_Pln p(gp_Ax3(gp_Pnt(0,0,c.z),gp_Dir(0,0,1),gp_Dir(1,0,0)));
  TopLoc_Location move(c.move);
  BRepAlgoAPI_Common op(BRepBuilderAPI_MakeFace(p).Face().Moved(move),solid.Moved(move));
  if(!op.IsDone() || op.HasErrors() || op.Shape().IsNull()) return 3;
  if(save && !BRepTools::Write(op.Shape(),"section.brep")) return 4;
  const bool ok=check(c,op.Shape());
  std::cout<<"warnings="<<op.HasWarnings()<<'\n';
  if(ok && !op.HasWarnings()) {std::cout<<"TEST_DONE\n"; return 0;}
  return 1;
}
}
