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
    const std::string mode(argv[1]), dir(argv[2]);
    TopoDS_Shape a, b;
    BRep_Builder builder;
    if (mode == "control") {
        a = BRepPrimAPI_MakeBox(10, 10, 10).Shape();
        b = BRepPrimAPI_MakeBox(gp_Pnt(5,-1,-1), gp_Pnt(12,11,11)).Shape();
    } else {
        if (!BRepTools::Read(a, (dir+"/OCC497e.brep").c_str(), builder) ||
            !BRepTools::Read(b, (dir+"/OCC497f.brep").c_str(), builder)) return 2;
        gp_Trsf t;
        if (mode == "translated") t.SetTranslation(gp_Vec(1, 3, -2));
        else if (mode == "rotated")
            t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)), 0.13);
        else if (mode != "original" && mode != "tool_box" && mode != "object_box") return 2;
        if (mode == "translated" || mode == "rotated") {
            a = BRepBuilderAPI_Transform(a,t,false).Shape();
            b = BRepBuilderAPI_Transform(b,t,false).Shape();
        }
        if (mode == "tool_box" || mode == "object_box") {
            TopoDS_Compound c;
            builder.MakeCompound(c);
            const TopoDS_Shape extra = BRepPrimAPI_MakeBox(gp_Pnt(1000,1000,1000), 2, 3, 4).Shape();
            builder.Add(c,mode == "tool_box" ? b : a);
            builder.Add(c,extra);
            if (mode == "tool_box") b=c; else a=c;
        }
    }
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
    const bool control = mode == "control";
    const bool valid = BRepCheck_Analyzer(result).IsValid();
    const int edges=count(result, TopAbs_EDGE), faces=count(result, TopAbs_FACE), solids=count(result, TopAbs_SOLID);
    const double expected = control ? 400.0 : mode == "object_box" ? 2523.48 : 2471.48;
    const bool ok = std::isfinite(props.Mass()) && std::abs(props.Mass()-expected) < (control?1.e-6:0.1)
                    && (!control || (valid && faces==6 && solids==1));
    std::cout << std::setprecision(15) << "mode=" << mode << " area=" << props.Mass()
              << " expected=" << expected << " vertices=" << count(result, TopAbs_VERTEX)
              << " edges=" << edges << " faces=" << faces << " solids=" << solids
              << " valid=" << valid << " verdict=" << (ok?"PASS":"FAIL") << std::endl;
    return ok ? 0 : 1;
}
