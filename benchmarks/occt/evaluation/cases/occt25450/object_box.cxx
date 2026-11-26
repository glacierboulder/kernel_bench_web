#include <BRep_Builder.hxx>
#include <BRepTools.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <gp_Trsf.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS_Compound.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BOPAlgo_PaveFiller.hxx>
#include <NCollection_IncAllocator.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>

static int count(const TopoDS_Shape& s, TopAbs_ShapeEnum kind) {
    TopTools_IndexedMapOfShape all;
    TopExp::MapShapes(s, kind, all);
    return all.Extent();
}

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    const std::string mode("object_box");
    TopoDS_Shape a, b;
    BRep_Builder builder;
        if (!BRepTools::Read(a, argv[1], builder) ||
            !BRepTools::Read(b, argv[2], builder)) return 2;
    TopoDS_Compound c; builder.MakeCompound(c); builder.Add(c,a);
    builder.Add(c,BRepPrimAPI_MakeBox(gp_Pnt(1000,1000,1000),2,3,4).Shape());
    a=c;
    BOPCol_ListOfShape args;
    args.Append(a);
    args.Append(b);
    Handle(NCollection_BaseAllocator) mem = new NCollection_IncAllocator;
    BOPAlgo_PaveFiller pf(mem);
    pf.SetArguments(args);
    pf.Perform();
    if (pf.ErrorStatus()) return 2;
    BRepAlgoAPI_Cut op(a,b,pf);
    if (!op.IsDone() || op.Shape().IsNull()) return 2;
    const TopoDS_Shape result = op.Shape();
    GProp_GProps props;
    BRepGProp::SurfaceProperties(result, props);
    const bool control = false;
    const bool valid = BRepCheck_Analyzer(result).IsValid();
    const int edges=count(result, TopAbs_EDGE), faces=count(result, TopAbs_FACE), solids=count(result, TopAbs_SOLID);
    const double expected = 2523.48;
    const bool ok = std::isfinite(props.Mass()) && std::abs(props.Mass()-expected) < (control?1.e-6:0.1)
                   ;
    std::cout << std::setprecision(15) << "mode=" << mode << " area=" << props.Mass()
              << " expected=" << expected << " vertices=" << count(result, TopAbs_VERTEX)
              << " edges=" << edges << " faces=" << faces << " solids=" << solids
              << " valid=" << valid << " verdict=" << (ok?"PASS":"FAIL") << std::endl;
    return ok ? 0 : 1;
}
