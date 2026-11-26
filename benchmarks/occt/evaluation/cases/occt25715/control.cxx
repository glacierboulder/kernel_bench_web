#include <BOPAlgo_BOP.hxx>
#include <BOPAlgo_PaveFiller.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <NCollection_IncAllocator.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <gp_Ax1.hxx>
#include <gp_Trsf.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>

static TopoDS_Shape move(const TopoDS_Shape& s,const gp_Trsf& t) {
    BRepBuilderAPI_Transform tr(t); tr.Perform(s); return tr.Shape();
}
static TopoDS_Shape rot(const TopoDS_Shape& s,double x,double y,double z,double a) {
    gp_Trsf t; t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(x,y,z)),a*(M_PI/180)); return move(s,t);
}
static TopoDS_Shape trans(const TopoDS_Shape& s,double x,double y,double z) {
    gp_Trsf t; t.SetTranslation(gp_Vec(x,y,z)); return move(s,t);
}
int main(int argc,char** argv) {
    const std::string mode="control";
    TopoDS_Shape a=BRepPrimAPI_MakeCylinder(0.069,0.6).Shape();
    TopoDS_Shape b=BRepPrimAPI_MakeCylinder(0.024,0.4).Shape();
    a=rot(a,0,0,1,90);
    b=rot(b,0,1,0,90);
    b=rot(b,1,0,0,-45);
    b=trans(b,-0.2,0,0.48);
    if (mode=="translated") {a=trans(a,2,3,1);b=trans(b,2,3,1);}
    if (mode=="rotated") {a=rot(a,0,0,1,20);b=rot(b,0,0,1,20);}
    if (mode=="control") b=trans(b,0,0,2);
    BOPCol_ListOfShape args; args.Append(a); args.Append(b);
    Handle(NCollection_BaseAllocator) mem=new NCollection_IncAllocator;
    BOPAlgo_PaveFiller pf(mem); pf.SetArguments(args); pf.SetFuzzyValue(0);
    pf.SetRunParallel(false); pf.Perform();
    if (pf.ErrorStatus()) {std::cerr<<"filler="<<pf.ErrorStatus()<<std::endl; return 2;}
    BOPAlgo_BOP cut(mem); cut.AddArgument(a); cut.AddTool(b); cut.SetOperation(BOPAlgo_CUT);
    cut.SetRunParallel(false); cut.PerformWithFiller(pf);
    if (cut.ErrorStatus()||cut.Shape().IsNull()) {std::cerr<<"cut="<<cut.ErrorStatus()<<std::endl;return 2;}
    TopoDS_Shape r=cut.Shape(); int total=0;
    int triggered[]={4,6,6,4,1,1,0,1}, separated[]={2,3,3,3,1,1,0,1};
    const int* expected = mode=="control"?separated:triggered;
    bool ok=true;
    TopAbs_ShapeEnum types[]={TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE,TopAbs_FACE,TopAbs_SHELL,TopAbs_SOLID,TopAbs_COMPSOLID,TopAbs_COMPOUND};
    std::cout<<"mode="<<mode<<" counts=";
    for (int i=0;i<8;++i) {
        TopTools_IndexedMapOfShape m; TopExp::MapShapes(r,types[i],m);
        ok=ok && m.Extent()==expected[i];
        total+=m.Extent(); std::cout<<m.Extent()<<",";
    }
    GProp_GProps vp; BRepGProp::VolumeProperties(r,vp);
    bool valid=BRepCheck_Analyzer(r).IsValid();
    ok=ok && valid && std::abs(vp.Mass()-(mode=="control"?0.0089742735742446:0.0087283))<0.000002;
    std::cout<<total<<" valid="<<valid<<" volume="<<std::setprecision(15)<<vp.Mass()<<" verdict="<<(ok?"PASS":"FAIL")<<std::endl;
    return ok?0:1;
}
