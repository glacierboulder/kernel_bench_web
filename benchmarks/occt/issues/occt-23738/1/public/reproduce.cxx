#define HAVE_IOSTREAM
#define HAVE_FSTREAM
#define HAVE_LIMITS_H
#define HAVE_IOMANIP
#define CSFDB
#include <BOPTools_DSFiller.hxx>
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
int main(int argc, char** argv) {
    if (argc!=3) return 2;
    TopoDS_Shape a,b;
    BRep_Builder reader;
    if (!BRepTools::Read(a,argv[1],reader)||!BRepTools::Read(b,argv[2],reader)) return 2;
    BOPTools_DSFiller filler;
    filler.SetShapes(a,b);
    if (!filler.IsDone()) return 2;
    filler.Perform();
    BRepAlgoAPI_Fuse op(a,b,filler);
    if (!op.IsDone()) return 2;
    const TopoDS_Shape result=op.Shape();
    const TopAbs_ShapeEnum kinds[]={TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE,TopAbs_FACE,TopAbs_SHELL,TopAbs_SOLID,TopAbs_COMPOUND};
    const char* labels[]={"vertices","edges","wires","faces","shells","solids","compounds"};
    const int expected[]={8,12,8,6,1,0,1};
    bool valid=BRepCheck_Analyzer(result).IsValid(), ok=valid;
    for (int i=0;i<7;++i) {
        TopTools_IndexedMapOfShape map; TopExp::MapShapes(result,kinds[i],map);
        ok=ok && map.Extent()==expected[i]; std::cout<<labels[i]<<"="<<map.Extent()<<" ";
    }
    GProp_GProps prop; BRepGProp::SurfaceProperties(result,prop);
    ok=ok && std::abs(prop.Mass()-225009)<1;
    std::cout<<std::setprecision(14)<<"area="<<prop.Mass()<<" valid="<<valid<<" verdict="<<(ok?"PASS":"FAIL")<<"\n";
    return ok?0:1;
}
