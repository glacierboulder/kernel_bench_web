// Parametric boundary and world coverage of the healthy M23612 trimmed torus.
#include <BRepAdaptor_Surface.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepPrimAPI_MakeTorus.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <Geom2dAdaptor_Curve.hxx>
#include <Standard_Failure.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <gp_Torus.hxx>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace {
const double pi = std::acos(-1.0);
constexpr double angleTolerance = 1e-10;

TopoDS_Shape read(const char* p) {
    TopoDS_Shape s;
    BRep_Builder builder;
    if (!BRepTools::Read(s,p,builder) || s.IsNull()) throw std::runtime_error("invalid BREP input");
    return s;
}

bool near(double a,double b) { return std::abs(a-b) <= angleTolerance; }
bool periodic(double a,double b) { return near(std::remainder(a-b,2*pi),0); }

const char* assess(const TopoDS_Shape& solid) {
    if (!BRepCheck_Analyzer(solid).IsValid()) return "invalid";
    TopoDS_Face torus;
    for (TopExp_Explorer it(solid,TopAbs_FACE); it.More(); it.Next()) {
        const auto face = TopoDS::Face(it.Current());
        if (BRepAdaptor_Surface(face).GetType() != GeomAbs_Torus) continue;
        if (!torus.IsNull()) return "multiple_surfaces";
        torus = face;
    }
    if (torus.IsNull()) return "missing_torus";
    const BRepAdaptor_Surface surf(torus);
    const auto t = surf.Torus();
    if (t.Location().Distance(gp_Pnt(0,0,0)) > 1e-7 || !near(t.Axis().Direction().Z(),1)
        || !near(t.MajorRadius(),10) || !near(t.MinorRadius(),2)) return "support";
    double u1,u2,v1,v2;
    BRepTools::UVBounds(torus,u1,u2,v1,v2);
    const double world = std::atan2(t.XAxis().Direction().Y(), t.XAxis().Direction().X());
    std::cout << "METRICS world_u=" << u1+world << ' ' << u2+world << " v=" << v1 << ' ' << v2 << '\n';
    if (!near(u2-u1,pi/4) || !near(v2-v1,pi/2)) return "truncated";
    if (!periodic(u1+world,0) || !periodic(v1,-pi/4)) return "displaced";
    unsigned trim = 0;
    int wires = 0;
    for (TopExp_Explorer it(torus,TopAbs_WIRE);it.More();it.Next()) ++wires;
    if (wires != 1) return "trim_topology";
    for (TopExp_Explorer it(torus,TopAbs_EDGE);it.More();it.Next()) {
        double first,last;
        const auto curve = BRep_Tool::CurveOnSurface(TopoDS::Edge(it.Current()),torus,first,last);
        if (curve.IsNull() || Geom2dAdaptor_Curve(curve,first,last).GetType()!=GeomAbs_Line) return "trim_topology";
        const auto p = curve->Value(first), q = curve->Value(last);
        unsigned edge = 0;
        if (near(std::abs(q.Y()-p.Y()),v2-v1)) {
            if (near(p.X(),u1) && near(q.X(),u1)) edge = 1;
            if (near(p.X(),u2) && near(q.X(),u2)) edge = 2;
        }
        if (near(std::abs(q.X()-p.X()),u2-u1)) {
            if (near(p.Y(),v1) && near(q.Y(),v1)) edge = 4;
            if (near(p.Y(),v2) && near(q.Y(),v2)) edge = 8;
        }
        if (!edge || (trim & edge)) return "trim_topology";
        trim |= edge;
    }
    return trim == 15 ? "pass" : "trim_topology";
}
} // namespace

int main(int argc,char** argv) {
    if (argc != 6) return 2;
    std::cout << std::setprecision(17);
    try {
        const gp_Ax2 frame(gp_Pnt(0,0,0),gp_Dir(0,0,1),gp_Dir(1,0,0));
        const auto shape = BRepPrimAPI_MakeTorus(frame,10,2,-pi/4,pi/4,pi/4).Shape();
        const char* roles[] = {"native","healthy","period","u-shift","v-shift","truncated"};
        const std::string expected[] = {"pass","pass","pass","displaced","displaced","truncated"};
        bool ok = true;
        for (int i=0;i!=6;++i) {
            const auto actual = assess(i==0 ? shape : read(argv[i]));
            std::cout << roles[i] << ' ' << actual << '\n';
            ok = ok && expected[i]==actual;
        }
        if (ok) std::cout << "TEST_DONE\n";
        return ok ? 0 : 1;
    } catch (const Standard_Failure& error) {
        std::cerr << error.GetMessageString() << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
    }
    return 2;
}
