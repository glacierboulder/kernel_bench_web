#include <BOPAlgo_Builder.hxx>
#include <BOPAlgo_PaveFiller.hxx>
#include <BOPCol_ListOfShape.hxx>
#include <BRepBuilderAPI_Copy.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepGProp.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <gp_Ax2.hxx>
#include <gp_Pln.hxx>
#include <gp_Trsf.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>

static TopoDS_Shape fourthFace(const TopoDS_Shape& source) {
    TopTools_IndexedMapOfShape faces;
    TopExp::MapShapes(source, TopAbs_FACE, faces);
    if (faces.Extent() < 4) throw std::runtime_error("model has fewer than four faces");
    return faces(4);
}

static int measure(const std::string& model, const std::string& variant) {
    const bool normal = variant == "normal";
    TopoDS_Shape left, right;
    if (normal) {
        gp_Pln plane(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1));
        left = BRepBuilderAPI_MakeFace(plane, -2, -1, -1, 1).Shape();
        right = BRepBuilderAPI_MakeFace(plane, 1, 2, -1, 1).Shape();
    } else {
        BRep_Builder reader;
        TopoDS_Shape source;
        if (!BRepTools::Read(source, model.c_str(), reader))
            throw std::runtime_error("could not read input");
        gp_Trsf mirror;
        mirror.SetMirror(gp_Ax2(gp_Pnt(0,0,0), gp_Dir(1,0,0)));
        BRepBuilderAPI_Copy copy(source);
        left = fourthFace(source);
        right = fourthFace(BRepBuilderAPI_Transform(copy.Shape(), mirror).Shape());
        if (variant == "translated") {
            gp_Trsf shift;
            shift.SetTranslation(gp_Vec(0.125, -0.25, 0.5));
            left = BRepBuilderAPI_Transform(left, shift).Shape();
            right = BRepBuilderAPI_Transform(right, shift).Shape();
        } else if (variant == "swapped") {
            std::swap(left, right);
        } else if (variant != "original") {
            throw std::runtime_error("unknown variant");
        }
    }
    BOPCol_ListOfShape args;
    args.Append(left);
    args.Append(right);
    BOPAlgo_PaveFiller filler;
    filler.SetArguments(args);
    filler.SetRunParallel(Standard_False);
    filler.Perform();
    if (filler.ErrorStatus()) throw std::runtime_error("filler failed");
    BOPAlgo_Builder builder;
    builder.AddArgument(left);
    builder.AddArgument(right);
    builder.SetRunParallel(Standard_False);
    builder.PerformWithFiller(filler);
    if (builder.ErrorStatus()) throw std::runtime_error("general fuse failed");
    const TopoDS_Shape result = builder.Shape();
    GProp_GProps surf;
    BRepGProp::SurfaceProperties(result, surf);
    const double reference = normal ? 4 : 306.285;
    bool ok = std::isfinite(surf.Mass()) && std::abs(surf.Mass()-reference) <= 0.01*reference;
    const TopAbs_ShapeEnum types[] = {TopAbs_VERTEX, TopAbs_EDGE, TopAbs_WIRE, TopAbs_FACE,
                                      TopAbs_SHELL, TopAbs_SOLID};
    const char* labels[] = {"vertices", "edges", "wires", "faces", "shells", "solids"};
    const int expected[] = {normal ? 8 : 6, normal ? 8 : 11, normal ? 2 : 4, 2, 0, 0};
    std::cout << "variant=" << variant;
    for (int i=0; i<6; ++i) {
        TopTools_IndexedMapOfShape map;
        TopExp::MapShapes(result, types[i], map);
        std::cout << " " << labels[i] << "=" << map.Extent();
        ok = ok && map.Extent() == expected[i];
    }
    std::cout << std::setprecision(14) << " area=" << surf.Mass()
              << " verdict=" << (ok ? "PASS" : "FAIL") << std::endl;
    return ok ? 0 : 1;
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    try { return measure(argv[1], "normal"); }
    catch (const Standard_Failure& e) { std::cerr << "OCCT error " << e.GetMessageString() << std::endl; }
    catch (const std::exception& e) { std::cerr << "probe error " << e.what() << std::endl; }
    return 2;
}
