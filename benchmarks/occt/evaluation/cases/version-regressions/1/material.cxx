// Replay separate healthy Boolean contracts on the kernels named by their suite manifests.
#include <BRepAdaptor_Surface.hxx>
#include <BRepAlgoAPI_Common.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <gp_Pln.hxx>
#include <gp_Sphere.hxx>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr double tolerance = 1e-6;
const double pi = std::acos(-1.0);

TopoDS_Shape read(const char* filename) {
    TopoDS_Shape shape;
    BRep_Builder builder;
    if (!BRepTools::Read(shape, filename, builder) || shape.IsNull())
        throw std::runtime_error("could not read control BREP");
    return shape;
}

TopoDS_Shape sphere(const gp_Pnt& center, double radius) {
    return BRepPrimAPI_MakeSphere(center, radius).Shape();
}

TopoDS_Shape box(const gp_Pnt& position, double dx, double dy, double dz) {
    return BRepPrimAPI_MakeBox(position, dx, dy, dz).Shape();
}

template<class Operation>
TopoDS_Shape run(const TopoDS_Shape& a, const TopoDS_Shape& b) {
    Operation op(a,b);
    if (!op.IsDone() || op.Shape().IsNull())
        throw std::runtime_error("Boolean operation failed");
    return op.Shape();
}

struct Fixture {
    TopoDS_Shape native;
    double volume;
    gp_Pnt centroid;
    std::vector<gp_Pnt> inside, outside;
};

Fixture fixture(const std::string& mode) {
    if (mode == "half-sphere") {
        auto native = run<BRepAlgoAPI_Common>(sphere(gp_Pnt(0,0,0),4),box(gp_Pnt(0,-4,-4),4,8,8));
        return {native,128*pi/3,gp_Pnt(1.5,0,0),{{2,0,0},{0.1,1,0},{2,1,1}},
                {{-2,0,0},{-0.1,1,0},{4.2,0,0}}};
    }
    if (mode == "shell") {
        const gp_Pnt center(50,50,50);
        auto shell = run<BRepAlgoAPI_Cut>(sphere(center,15),sphere(center,10));
        auto native = run<BRepAlgoAPI_Common>(shell,box(gp_Pnt(0,0,0),100,100,100));
        return {native,4*pi*(3375-1000)/3,center,{{61,50,50},{39,50,50},{50,61,50}},
                {{50,50,50},{59,50,50},{66,50,50}}};
    }
    if (mode == "disjoint-cut") {
        const gp_Pnt center(0,5.5,18);
        auto native = run<BRepAlgoAPI_Cut>(sphere(center,4),sphere(gp_Pnt(0,4.5,10),1));
        return {native,256*pi/3,center,{{-3,5.5,18},{2,5.5,18}},
                {{6,5.5,18},{0,4.5,10},{0,5.5,24}}};
    }
    if (mode == "box-location") {
        auto native = run<BRepAlgoAPI_Common>(box(gp_Pnt(0,0,0),10,10,10),box(gp_Pnt(5,0,0),10,10,10));
        return {native,500,gp_Pnt(7.5,5,5),{{5.5,5,5},{7.5,5,5},{9.5,5,5}},
                {{2.5,5,5},{10.5,5,5},{7.5,-.5,5},{7.5,5,10.5}}};
    }
    throw std::runtime_error("unknown fixture");
}

bool support(const TopoDS_Shape& shape, const std::string& mode) {
    std::vector<double> radii;
    int planes = 0;
    for (TopExp_Explorer faces(shape, TopAbs_FACE); faces.More(); faces.Next()) {
        const auto face = TopoDS::Face(faces.Current());
        const BRepAdaptor_Surface surface(face);
        if (surface.GetType() == GeomAbs_Sphere) {
            const gp_Sphere s = surface.Sphere();
            radii.push_back(s.Radius());
            if (mode == "half-sphere" &&
                (s.Location().Distance(gp_Pnt(0,0,0)) > tolerance || std::abs(s.Radius()-4) > tolerance))
                return false;
            if (mode == "shell") {
                if (s.Location().Distance(gp_Pnt(50,50,50)) > tolerance) return false;
                if (std::abs(s.Radius()-10) <= tolerance && face.Orientation() != TopAbs_REVERSED)
                    return false;
            }
        } else if (surface.GetType() == GeomAbs_Plane) {
            ++planes;
            if (mode == "half-sphere") {
                const auto plane = surface.Plane();
                double normalX = plane.Axis().Direction().X();
                if (face.Orientation() == TopAbs_REVERSED) normalX = -normalX;
                if (std::abs(normalX+1) > tolerance || plane.Distance(gp_Pnt(0,0,0)) > tolerance) return false;
            }
        } else {
            return false;
        }
    }
    if (mode == "box-location") return radii.empty() && planes == 6;
    if (mode == "shell")
        return radii.size() == 2 && std::abs(std::min(radii[0],radii[1])-10) <= tolerance
            && std::abs(std::max(radii[0],radii[1])-15) <= tolerance;
    if (mode == "half-sphere") return !radii.empty() && planes >= 1;
    return radii.size() == 1 && std::abs(radii.front()-4) <= tolerance
        && planes == (mode == "half-sphere" ? 1 : 0);
}

std::string assess(const TopoDS_Shape& shape, const Fixture& expected, const std::string& mode) {
    TopExp_Explorer solids(shape, TopAbs_SOLID);
    if (!solids.More() || !BRepCheck_Analyzer(shape).IsValid()) return "invalid";
    const TopoDS_Shape solid = solids.Current();
    solids.Next();
    if (solids.More()) return "invalid";
    GProp_GProps properties;
    BRepGProp::VolumeProperties(solid,properties,1e-10);
    const double volume = properties.Mass();
    const double displacement = properties.CentreOfMass().Distance(expected.centroid);
    BRepClass3d_SolidClassifier classify(solid);
    int misses = 0;
    for (const auto& p : expected.inside) {
        classify.Perform(p, 1e-7);
        misses += classify.State() != TopAbs_IN;
    }
    for (const auto& p : expected.outside) {
        classify.Perform(p, 1e-7);
        misses += classify.State() != TopAbs_OUT;
    }
    const bool supports = support(solid, mode);
    std::cout << "METRICS volume=" << volume << " center_error=" << displacement
              << " material_mismatches=" << misses << " surface_support=" << supports << '\n';
    if (!std::isfinite(volume) || std::abs(volume - expected.volume) > tolerance)
        return "wrong_volume";
    if (!supports || displacement > tolerance || misses)
        return "wrong_location";
    return "pass";
}
} // namespace

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    std::cout << std::setprecision(17);
    try {
        std::ifstream modeFile(argv[1]);
        std::string mode;
        if (!(modeFile >> mode)) throw std::runtime_error("missing fixture selector");
        const auto f = fixture(mode);
        auto native = assess(f.native, f, mode);
        auto healthy = assess(read(argv[2]), f, mode);
        auto wrong = assess(read(argv[3]), f, mode);
        std::cout << "native " << native << "\nhealthy " << healthy << "\nnegative " << wrong << '\n';
        if (native != "pass" || healthy != "pass" || wrong != "wrong_location") return 1;
        std::cout << "TEST_DONE\n";
        return 0;
    } catch (const Standard_Failure& failure) {
        std::cerr << failure.GetMessageString() << '\n';
    } catch (const std::exception& failure) {
        std::cerr << failure.what() << '\n';
    }
    return 2;
}
