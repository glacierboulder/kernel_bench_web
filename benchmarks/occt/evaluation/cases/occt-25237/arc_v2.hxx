// Oracle geometry comes from the precise input circle, independent of the Common result.
#pragma once
#include <BRepAdaptor_Curve.hxx>
#include <BRepAlgoAPI_Common.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Iterator.hxx>
#include <gp_Circ.hxx>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace arc_v2 {
inline TopoDS_Shape readFixture(const char* path) {
  std::ifstream in(path);
  std::string header;
  std::getline(in, header);
  TopoDS_Shape s;
  BRepTools::Read(s, in, BRep_Builder());
  if (s.IsNull()) throw std::runtime_error(path);
  return s;
}

struct Case { TopoDS_Shape first, second; gp_Circ support; double lo, hi; };

inline Case makeCase(bool healthy) {
  auto first = readFixture("bug25237_b26.brep");
  BRepAdaptor_Curve ref(TopoDS::Edge(first));
  auto circle = ref.Circle();
  const double lo = ref.FirstParameter(), hi = ref.LastParameter(), span = hi-lo;
  if (healthy) {
    const double a = lo + span * .25, b = lo + span * .75;
    return {BRepBuilderAPI_MakeEdge(circle,lo,b).Edge(),
            BRepBuilderAPI_MakeEdge(circle,a,hi).Edge(),circle,a,b};
  }
  gp_Trsf t;
  t.SetRotation(gp_Ax1(gp_Pnt(10,2,-1),gp_Dir(1,2,3)),31*std::acos(-1.)/180.);
  TopLoc_Location move(t);
  return {first.Moved(move), readFixture("bug25237_b5.brep").Moved(move),
          circle.Transformed(t),lo,hi};
}

// Common can wrap its edge in nested compounds. Reject extra free vertices or other geometry.
inline TopoDS_Shape onlyEdge(TopoDS_Shape shape) {
  while (!shape.IsNull() && shape.ShapeType()==TopAbs_COMPOUND) {
    TopoDS_Iterator it(shape);
    if (!it.More()) return {};
    shape=it.Value();
    it.Next();
    if (it.More()) return {};
  }
  return (!shape.IsNull() && shape.ShapeType()==TopAbs_EDGE) ? shape : TopoDS_Shape{};
}

inline bool check(const Case& c, const TopoDS_Shape& result) {
  const auto single = onlyEdge(result);
  if (single.IsNull()) { std::cout<<"missing or extra components\n"; return false; }
  const auto exact = BRepBuilderAPI_MakeEdge(c.support,c.lo,c.hi).Edge();
  BRepAdaptor_Curve target(exact), actual(TopoDS::Edge(single));
  const double lo=actual.FirstParameter(), hi=actual.LastParameter();
  const auto start=target.Value(c.lo), end=target.Value(c.hi), x=actual.Value(lo), y=actual.Value(hi);
  const double endpoint=std::min(std::max(start.Distance(x),end.Distance(y)),
                                 std::max(start.Distance(y),end.Distance(x)));
  const auto frame=c.support.Position();
  const double tau=2*std::acos(-1.);
  double error=0.;
  for (int i=0;i<=64;++i) {
    gp_Vec p(c.support.Location(),actual.Value(lo+(hi-lo)*i/64.));
    const double u=p.Dot(gp_Vec(frame.XDirection())), v=p.Dot(gp_Vec(frame.YDirection()));
    double angle=std::atan2(v,u);
    angle+=tau*std::round(((c.lo+c.hi)/2-angle)/tau);
    error=std::max({error,std::abs(p.Dot(gp_Vec(frame.Direction()))),
                    std::abs(std::hypot(u,v)-c.support.Radius()),
                    c.support.Radius()*std::max({0.,c.lo-angle,angle-c.hi})});
  }
  GProp_GProps props;
  BRepGProp::LinearProperties(single,props);
  const double length=c.support.Radius()*(c.hi-c.lo);
  const bool valid=BRepCheck_Analyzer(single).IsValid();
  std::cout<<std::setprecision(16)<<"length="<<props.Mass()<<" expected="<<length
           <<" endpoint="<<endpoint<<" support="<<error<<" valid="<<valid<<'\n';
  return valid && std::abs(props.Mass()-length)<1e-6 && endpoint<=1.6e-5 && error<=1.6e-5;
}
inline int run(bool healthy, bool save=false) {
  const auto c=makeCase(healthy);
  bool pass=true;
  for(int swap=0;swap<2;++swap) {
    BRepAlgoAPI_Common op(swap?c.second:c.first,swap?c.first:c.second);
    if (!op.IsDone() || op.HasErrors() || op.Shape().IsNull()) return 3;
    if (save && !BRepTools::Write(op.Shape(),swap?"reverse.brep":"forward.brep")) return 4;
    std::cout<<"swap="<<swap<<" ";
    if (!check(c,op.Shape())) pass=false;
  }
  if (pass) std::cout<<"TEST_DONE\n";
  return pass?0:1;
}
}
