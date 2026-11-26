#define HAVE_IOSTREAM
#define HAVE_FSTREAM
#define HAVE_IOMANIP
#define HAVE_LIMITS_H
#define CSFDB
#include <BOPTools_DSFiller.hxx>
#include <BRepAlgoAPI_Section.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopExp.hxx>
#include <gp_Pln.hxx>
#include <cmath>
#include <iostream>
#include <iomanip>
#include <string>
#include <utility>

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    std::string variant("normal");
    const bool normal = variant == "normal";
    TopoDS_Shape a, b;
    if (normal) {
        gp_Pln xy(gp_Ax3(gp_Pnt(0,0,0), gp_Dir(0,0,1), gp_Dir(1,0,0)));
        gp_Pln xz(gp_Ax3(gp_Pnt(0,0,0), gp_Dir(0,1,0), gp_Dir(1,0,0)));
        a = BRepBuilderAPI_MakeFace(xy,-2,1,-1,1).Shape();
        b = BRepBuilderAPI_MakeFace(xz,-5,5,-1,1).Shape();
    } else {
        BRep_Builder reader;
        if (!BRepTools::Read(a, argv[1], reader) || !BRepTools::Read(b, argv[2], reader)) return 2;
        if (variant == "swapped") std::swap(a,b);
        else if (variant == "translated") {
            gp_Trsf t; t.SetTranslation(gp_Vec(17,-11,3));
            a = BRepBuilderAPI_Transform(a,t).Shape();
            b = BRepBuilderAPI_Transform(b,t).Shape();
        } else if (variant != "original") return 2;
    }
    BOPTools_DSFiller filler;
    filler.SetShapes(a,b);
    if (!filler.IsDone()) return 2;
    filler.Perform();
    BRepAlgoAPI_Section section(a,b,filler);
    if (!section.IsDone()) return 2;
    const TopoDS_Shape result=section.Shape();
    GProp_GProps props;
    BRepGProp::LinearProperties(result,props);
    const double length=props.Mass();
    bool valid=BRepCheck_Analyzer(result).IsValid();
    bool ok = valid && abs(length-(normal ? 3.0 : 2.94086))<=0.0001;
    const int expected[]={normal ? 2 : 4, normal ? 1 : 2, 0, 0, 1};
    const TopAbs_ShapeEnum types[]={TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE,TopAbs_FACE,TopAbs_COMPOUND};
    const char* names[]={"vertices","edges","wires","faces","compounds"};
    std::cout << "variant=" << variant;
    for (int i=0;i<5;++i) {
        TopTools_IndexedMapOfShape map; TopExp::MapShapes(result,types[i],map);
        std::cout<<" "<<names[i]<<"="<<map.Extent(); ok=ok && map.Extent()==expected[i];
    }
    std::cout<<std::setprecision(14)<<" length="<<length<<" valid="<<valid<<" verdict="<<(ok?"PASS":"FAIL")<<"\n";
    return ok?0:1;
}
