#define HAVE_IOSTREAM
#define HAVE_FSTREAM
#define HAVE_IOMANIP
#define HAVE_LIMITS_H
#define CSFDB
#include <BOPTools_DSFiller.hxx>
#include <BRepAlgoAPI_Section.hxx>
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
    BRep_Builder reader;
    TopoDS_Shape a,b;
    if (!BRepTools::Read(a,argv[1],reader) || !BRepTools::Read(b,argv[2],reader)) return 2;
    BOPTools_DSFiller filler;
    filler.SetShapes(a,b);
    if (!filler.IsDone()) return 2;
    filler.Perform();
    BRepAlgoAPI_Section op(a,b,filler);
    if (!op.IsDone()) return 2;
    const TopoDS_Shape result=op.Shape();
    TopTools_IndexedMapOfShape vertices,edges,wires,faces,compounds;
    TopExp::MapShapes(result,TopAbs_VERTEX,vertices);
    TopExp::MapShapes(result,TopAbs_EDGE,edges);
    TopExp::MapShapes(result,TopAbs_WIRE,wires);
    TopExp::MapShapes(result,TopAbs_FACE,faces);
    TopExp::MapShapes(result,TopAbs_COMPOUND,compounds);
    GProp_GProps props;
    BRepGProp::LinearProperties(result,props);
    bool valid=BRepCheck_Analyzer(result).IsValid();
    bool pass=valid && vertices.Extent()==4 && edges.Extent()==2 && wires.Extent()==0 &&
              faces.Extent()==0 && compounds.Extent()==1 && std::abs(props.Mass()-2.94086)<0.0001;
    std::cout<<std::setprecision(14)<<"vertices="<<vertices.Extent()<<" edges="<<edges.Extent()
             <<" wires="<<wires.Extent()<<" faces="<<faces.Extent()<<" compounds="<<compounds.Extent()
             <<" length="<<props.Mass()<<" valid="<<valid<<" verdict="<<(pass?"PASS":"FAIL")<<"\n";
    return pass ? 0 : 1;
}
