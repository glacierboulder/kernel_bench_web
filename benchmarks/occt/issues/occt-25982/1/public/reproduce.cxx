#include <BOPAlgo_Builder.hxx>
#include <BOPAlgo_PaveFiller.hxx>
#include <BRepBuilderAPI_Copy.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <gp_Ax2.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    TopoDS_Shape original;
    BRep_Builder reader;
    if (!BRepTools::Read(original, argv[1], reader)) return 2;
    BRepBuilderAPI_Copy copied(original);
    gp_Trsf mirror;
    mirror.SetMirror(gp_Ax2(gp_Pnt(0,0,0), gp_Dir(1,0,0)));
    TopTools_IndexedMapOfShape a, b;
    TopExp::MapShapes(original, TopAbs_FACE, a);
    TopExp::MapShapes(BRepBuilderAPI_Transform(copied.Shape(), mirror).Shape(), TopAbs_FACE, b);
    if (a.Extent() < 4 || b.Extent() < 4) return 2;
    BOPCol_ListOfShape args;
    args.Append(a(4)); args.Append(b(4));
    BOPAlgo_PaveFiller filler;
    filler.SetArguments(args);
    filler.Perform();
    if (filler.ErrorStatus()) return 2;
    BOPAlgo_Builder builder;
    builder.AddArgument(a(4)); builder.AddArgument(b(4));
    builder.PerformWithFiller(filler);
    if (builder.ErrorStatus()) return 2;
    TopoDS_Shape result = builder.Shape();
    int expected[] = {6, 11, 4, 2, 0, 0};
    const char* names[] = {"vertices","edges","wires","faces","shells","solids"};
    TopAbs_ShapeEnum types[] = {TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE,TopAbs_FACE,TopAbs_SHELL,TopAbs_SOLID};
    bool ok = true;
    for (int i=0;i<6;++i) {
        TopTools_IndexedMapOfShape entries;
        TopExp::MapShapes(result, types[i], entries);
        std::cout << names[i] << "=" << entries.Extent() << " ";
        ok = ok && entries.Extent() == expected[i];
    }
    GProp_GProps props;
    BRepGProp::SurfaceProperties(result, props);
    double area = props.Mass();
    ok = ok && std::abs(area-306.285) <= 306.285*0.01;
    std::cout << std::setprecision(14) << "area=" << area << " verdict=" << (ok ? "PASS" : "FAIL") << "\n";
    return ok ? 0 : 1;
}
