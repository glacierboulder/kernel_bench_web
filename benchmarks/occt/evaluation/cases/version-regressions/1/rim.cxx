// Healthy circular analogue of the GH-1371 closed-edge fillet.
#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Vertex.hxx>
#include <GProp_GProps.hxx>
#include <BRepGProp.hxx>
#include <gp_Circ.hxx>
#include <gp_Torus.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

constexpr double tolerance = 1e-6;
const double pi = std::acos(-1.0);
const double expectedVolume = pi * (9 * 25 + 16 + 2 * pi + 2.0 / 3);

bool near(double a, double b) { return std::abs(a - b) <= tolerance; }

TopoDS_Shape read(const char* path) {
    BRep_Builder builder;
    TopoDS_Shape shape;
    if (!BRepTools::Read(shape, path, builder) || shape.IsNull())
        throw std::runtime_error("could not read control BREP");
    return shape;
}

TopoDS_Edge topRim(const TopoDS_Shape& shape) {
    TopoDS_Edge target;
    for (TopExp_Explorer it(shape, TopAbs_EDGE); it.More(); it.Next()) {
        const auto edge = TopoDS::Edge(it.Current());
        const BRepAdaptor_Curve curve(edge);
        if (curve.GetType() != GeomAbs_Circle) continue;
        const auto circle = curve.Circle();
        if (circle.Location().Distance(gp_Pnt(0, 0, 10)) > tolerance || !near(circle.Radius(), 5)
            || !near(std::abs(circle.Axis().Direction().Z()), 1)
            || !near(curve.LastParameter() - curve.FirstParameter(), 2*pi)) continue;
        const auto first = TopExp::FirstVertex(edge);
        const auto last = TopExp::LastVertex(edge);
        if (first.IsNull() || last.IsNull() || !first.IsSame(last)) continue;
        if (!target.IsNull() && !target.IsSame(edge))
            throw std::runtime_error("multiple closed top rims");
        target = edge;
    }
    if (target.IsNull()) throw std::runtime_error("missing closed top rim");
    return target;
}

TopoDS_Shape native() {
    gp_Circ profile(gp_Ax2(gp_Pnt(0,0,0), gp_Dir(0,0,1)), 5);
    const auto edge = BRepBuilderAPI_MakeEdge(profile).Edge();
    const auto wire = BRepBuilderAPI_MakeWire(edge).Wire();
    const auto disk = BRepBuilderAPI_MakeFace(wire).Face();
    const auto cylinder = BRepPrimAPI_MakePrism(disk, gp_Vec(0,0,10)).Shape();
    BRepFilletAPI_MakeFillet fillet(cylinder);
    fillet.Add(1, topRim(cylinder));
    fillet.Build();
    if (!fillet.IsDone()) throw std::runtime_error("fillet failed");
    return fillet.Shape();
}

std::string evaluate(const TopoDS_Shape& output) {
    TopExp_Explorer solids(output, TopAbs_SOLID);
    if (!solids.More() || !BRepCheck_Analyzer(output).IsValid()) return "invalid";
    const auto solid = solids.Current();
    solids.Next();
    if (solids.More()) return "invalid";
    GProp_GProps properties;
    BRepGProp::VolumeProperties(output, properties, 1e-10);
    bool top = false;
    int tori = 0;
    for (TopExp_Explorer it(output, TopAbs_FACE); it.More(); it.Next()) {
        BRepAdaptor_Surface surface(TopoDS::Face(it.Current()));
        if (surface.GetType() != GeomAbs_Torus) continue;
        ++tori;
        const gp_Torus torus = surface.Torus();
        top = torus.Location().Distance(gp_Pnt(0,0,9)) <= tolerance && near(torus.MajorRadius(),4)
            && near(torus.MinorRadius(),1) && near(std::abs(torus.Axis().Direction().Z()),1);
    }
    int misses = 0;
    BRepClass3d_SolidClassifier classifier(solid);
    for (double r : {0., 3.8, 4.55, 4.9, 5.25})
        for (double z : {.1, .5, 5., 9.5, 9.9})
            for (int i = 0; i < (r == 0 ? 1 : 8); ++i) {
                double theta = (i + .25) * pi / 4;
                classifier.Perform(gp_Pnt(r*std::cos(theta), r*std::sin(theta), z), 1e-7);
                double limit = z < 9 ? 5 : 4 + std::sqrt(1 - (z-9)*(z-9));
                misses += classifier.State() != (r < limit ? TopAbs_IN : TopAbs_OUT);
            }
    std::cout << "METRICS torus_count=" << tori << " target=" << top
              << " volume=" << properties.Mass() << " material_mismatches=" << misses << '\n';
    if (tori == 0 && misses) return "uncut";
    if (tori == 1 && !top && near(properties.Mass(), expectedVolume) && misses) return "wrong_rim";
    if (tori != 1 || !top || misses || !near(properties.Mass(), expectedVolume)) return "geometry_changed";
    return "pass";
}

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    std::cout << std::setprecision(17);
    try {
        const char* expected[] = {"pass", "pass", "wrong_rim", "uncut"};
        const char* roles[] = {"native", "healthy", "wrong-rim", "untouched"};
        bool matched = true;
        for (int n = 0; n <= 3; ++n) {
            const auto observed = evaluate(n == 0 ? native() : read(argv[n]));
            std::cout << roles[n] << ' ' << observed << '\n';
            matched = matched && observed == expected[n];
        }
        if (matched) std::cout << "TEST_DONE\n";
        return matched ? 0 : 1;
    } catch (const Standard_Failure& failure) {
        std::cerr << failure.GetMessageString() << '\n';
    } catch (const std::exception& failure) {
        std::cerr << failure.what() << '\n';
    }
    return 2;
}
