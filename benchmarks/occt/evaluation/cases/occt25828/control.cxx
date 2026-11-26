#include <BRep_Builder.hxx>
#include <BRepTools.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <gp_Trsf.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <BRepAlgoAPI_Section.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <TopoDS_Compound.hxx>
#include <gp_Pln.hxx>
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
    if (argc != 1) return 2;
    const std::string mode("control");
    TopoDS_Shape a, b;
    BRep_Builder builder;
        TopoDS_Compound distinct;
        builder.MakeCompound(distinct);
        for (int x = 2; x <= 5; x += 3) {
            const gp_Pln vertical(gp_Ax3(gp_Pnt(x,0,0), gp_Dir(1,0,0), gp_Dir(0,1,0)));
            builder.Add(distinct, BRepBuilderAPI_MakeFace(vertical, 0, 10, -1, 1).Face());
        }
        a = distinct;
        const gp_Pln flat(gp_Ax3(gp_Pnt(0,0,0), gp_Dir(0,0,1), gp_Dir(1,0,0)));
        b = BRepBuilderAPI_MakeFace(flat, -1, 7, -1, 11).Face();
    BRepAlgoAPI_Section op(a,b,false);
    op.Approximation(true);
    op.ComputePCurveOn1(true);
    op.ComputePCurveOn2(true);
    op.SetFuzzyValue(0);
    op.SetRunParallel(false);
    op.Build();
    if (!op.IsDone() || op.Shape().IsNull()) return 2;
    const TopoDS_Shape result = op.Shape();
    GProp_GProps props;
    BRepGProp::LinearProperties(result, props);
    const bool control = mode == "control";
    const bool valid = BRepCheck_Analyzer(result).IsValid();
    const int edges=count(result, TopAbs_EDGE), faces=count(result, TopAbs_FACE), solids=count(result, TopAbs_SOLID);
    const double expected = control ? 20.0 : 264.314;
    // tests/boolean/end compares abs(length-reference)/reference to 0.01.
    const bool ok = valid && std::isfinite(props.Mass()) && std::abs(props.Mass()-expected) <= (control?1.e-6:0.01*expected)
                    && (!control || (valid && edges==2 && faces==0));
    std::cout << std::setprecision(15) << "mode=" << mode << " length=" << props.Mass()
              << " expected=" << expected << " vertices=" << count(result, TopAbs_VERTEX)
              << " edges=" << edges << " faces=" << faces << " solids=" << solids
              << " valid=" << valid << " verdict=" << (ok?"PASS":"FAIL") << std::endl;
    return ok ? 0 : 1;
}
