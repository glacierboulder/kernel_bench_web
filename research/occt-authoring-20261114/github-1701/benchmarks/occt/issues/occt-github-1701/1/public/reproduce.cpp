#include <BRep_Builder.hxx>
#include <BRepTools.hxx>
#include <BRep_Tool.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BOPAlgo_ArgumentAnalyzer.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepBndLib.hxx>
#include <BRepGProp.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <GProp_GProps.hxx>
#include <Bnd_Box.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopExp_Explorer.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>
using ShapeMap=NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher>;
double volume(const TopoDS_Shape& s) {
 GProp_GProps p; BRepGProp::VolumeProperties(s,p); return p.Mass();
}
double top(const TopoDS_Shape& s) {
 Bnd_Box box; BRepBndLib::AddOptimal(s,box,false,false); return box.CornerMax().Z();
}
void selectCorner(const TopoDS_Shape& s,const ShapeMap& edges,int& a,int& b) {
 double z=-1e100;
 for(TopExp_Explorer v(s,TopAbs_VERTEX);v.More();v.Next()) z=std::max(z,BRep_Tool::Pnt(TopoDS::Vertex(v.Current())).Z());
 gp_Pnt high;
 for(int i=1;i<=edges.Extent();++i) {
  auto e=TopoDS::Edge(edges(i)); auto p=BRep_Tool::Pnt(TopExp::FirstVertex(e)),q=BRep_Tool::Pnt(TopExp::LastVertex(e));
  if(std::abs(p.Z()-z)<1e-7&&std::abs(q.Z()-z)<1e-7&&BRepAdaptor_Curve(e).GetType()==GeomAbs_Circle) {a=i;high=p.Y()>q.Y()?p:q;}
 }
 if(!a) throw std::runtime_error("missing top arc");
 for(int i=1;i<=edges.Extent();++i) {
  auto e=TopoDS::Edge(edges(i)); auto p=BRep_Tool::Pnt(TopExp::FirstVertex(e)),q=BRep_Tool::Pnt(TopExp::LastVertex(e));
  if(std::abs(p.Z()-z)<1e-7&&std::abs(q.Z()-z)<1e-7&&BRepAdaptor_Curve(e).GetType()==GeomAbs_Line&&(p.Distance(high)<1e-7||q.Distance(high)<1e-7)) b=i;
 }
 if(!b) throw std::runtime_error("missing top line");
}
int main(int argc,char** argv) {
 if(argc!=3) return 2;
 std::ifstream args(argv[2]); std::string mode,role; double radius; int a,b;
 if(!(args>>mode>>role>>radius>>a>>b)) return 2;
 TopoDS_Shape s; BRep_Builder builder;
 if(!BRepTools::Read(s,argv[1],builder)||s.IsNull()||!BRepCheck_Analyzer(s).IsValid()) return 3;
 ShapeMap edges; TopExp::MapShapes(s,TopAbs_EDGE,edges);
 if(mode=="1639") selectCorner(s,edges,a,b);
 if(a<1||a>edges.Extent()||b<0||b>edges.Extent()) return 4;
 BRepFilletAPI_MakeFillet maker(s);
 if(mode=="1738") {maker.SetParams(1e-2,1e-4,1e-5,1e-4,1e-5,1e-3);maker.SetContinuity(GeomAbs_C1,1e-2);}
 maker.Add(radius,TopoDS::Edge(edges(a)));if(b)maker.Add(radius,TopoDS::Edge(edges(b)));
 std::cout<<std::setprecision(12)<<"edges="<<a<<","<<b<<" radius="<<radius<<std::endl;
 maker.Build(); std::cout<<"done="<<maker.IsDone()<<std::endl; if(!maker.IsDone()) {
  if(role=="original"&&(mode=="1701"||mode=="1702")) {std::cout<<"TEST_DONE\n";return 0;}
  return 6;
 }
 auto t=maker.Shape(); if(t.IsNull()) return 5;
 double tol=0; for(TopExp_Explorer v(t,TopAbs_VERTEX);v.More();v.Next()) tol=std::max(tol,BRep_Tool::Tolerance(TopoDS::Vertex(v.Current())));
 std::cout<<"valid="<<BRepCheck_Analyzer(t).IsValid()<<" tol="<<tol<<" volume="<<volume(t)<<" rise="<<top(t)-top(s)<<std::endl;
 bool pass=BRepCheck_Analyzer(t).IsValid();
 if(mode=="1639") pass=pass&&std::abs(volume(t)-29799.867536)<0.01&&std::abs(top(t)-top(s))<1e-5;
 if(mode=="1738"||mode=="1702") {BOPAlgo_ArgumentAnalyzer check;check.SetShape1(t);check.SelfInterMode()=true;check.SmallEdgeMode()=true;check.Perform();if(mode=="1738") pass=pass&&check.GetCheckResult().IsEmpty()&&tol<0.01; std::cout<<"faults="<<check.GetCheckResult().Size()<<std::endl;}
 if(mode=="1701") {BRepAlgoAPI_Cut cut(t,BRepPrimAPI_MakeBox(gp_Pnt(0,0,1),10,10,1).Shape()); pass=pass&&tol<0.01&&cut.IsDone()&&!cut.Shape().IsNull()&&BRepCheck_Analyzer(cut.Shape()).IsValid()&&std::abs(volume(t)-volume(cut.Shape())-100)<0.01; if(cut.IsDone()&&!cut.Shape().IsNull()) std::cout<<"cut_valid="<<BRepCheck_Analyzer(cut.Shape()).IsValid()<<" removed="<<volume(t)-volume(cut.Shape())<<std::endl;}
 if(!pass)return 1;
 std::cout<<"TEST_DONE\n";
}
