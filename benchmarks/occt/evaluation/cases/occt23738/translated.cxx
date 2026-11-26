#define HAVE_IOSTREAM
#define HAVE_IOMANIP
#define HAVE_LIMITS_H
#define HAVE_FSTREAM
#define CSFDB
#include <BOPTools_DSFiller.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
#include <utility>

int main(int argc, char** argv) {
    if (argc!=3) return 2;
    const std::string variant="translated";
    const bool normal=variant=="normal";
    TopoDS_Shape a,b;
    if (normal) {
        a=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0,0,-2),gp_Dir(0,0,1),gp_Dir(1,0,0)),1,4).Shape();
        b=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(-2,0,0),gp_Dir(1,0,0),gp_Dir(0,1,0)),1,4).Shape();
        gp_Trsf t; t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,1,0)),13*std::acos(-1)/180);
        a=BRepBuilderAPI_Transform(a,t).Shape(); b=BRepBuilderAPI_Transform(b,t).Shape();
    } else {
        BRep_Builder reader;
        if (!BRepTools::Read(a,argv[1],reader)||!BRepTools::Read(b,argv[2],reader)) return 2;
        if (variant=="swapped") std::swap(a,b);
        else if (variant=="translated") {
            gp_Trsf t; t.SetTranslation(gp_Vec(17,-11,3));
            a=BRepBuilderAPI_Transform(a,t).Shape(); b=BRepBuilderAPI_Transform(b,t).Shape();
        } else if (variant!="original") return 2;
    }
    BOPTools_DSFiller filler; filler.SetShapes(a,b);
    if (!filler.IsDone()) return 2;
    filler.Perform();
    BRepAlgoAPI_Fuse op(a,b,filler);
    if (!op.IsDone()) {std::cout<<"variant="<<variant<<" done=0 verdict=FAIL\n";return 1;}
    const TopoDS_Shape result=op.Shape();
    const TopAbs_ShapeEnum kinds[]={TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE,TopAbs_FACE,TopAbs_SHELL,TopAbs_SOLID,TopAbs_COMPOUND};
    const char* labels[]={"vertices","edges","wires","faces","shells","solids","compounds"};
    const int expected[]={8,12,8,6,1,0,1};
    bool valid=BRepCheck_Analyzer(result).IsValid(), ok=valid;
    std::cout<<"variant="<<variant;
    for (int i=0;i<7;++i) {
        TopTools_IndexedMapOfShape map;TopExp::MapShapes(result,kinds[i],map);
        std::cout<<" "<<labels[i]<<"="<<map.Extent();
        ok=ok && (normal ? i!=5 || map.Extent()==1 : map.Extent()==expected[i]);
    }
    GProp_GProps prop;
    if (normal) BRepGProp::VolumeProperties(result,prop); else BRepGProp::SurfaceProperties(result,prop);
    const double target=normal? 8*std::acos(-1.0)-16.0/3.0 : 225009;
    ok=ok && std::abs(prop.Mass()-target)<=(normal ? .001 : 1);
    std::cout<<std::setprecision(14)<<(normal?" volume=":" area=")<<prop.Mass()<<" valid="<<valid
             <<" verdict="<<(ok?"PASS":"FAIL")<<"\n";
    return ok?0:1;
}
