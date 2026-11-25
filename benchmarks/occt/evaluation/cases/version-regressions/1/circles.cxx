// Position and continuous angular coverage of exact circular intersection branches.
#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GeomAPI_IntSS.hxx>
#include <Geom_CylindricalSurface.hxx>
#include <Geom_Plane.hxx>
#include <Geom_ToroidalSurface.hxx>
#include <Standard_Failure.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Iterator.hxx>
#include <gp_Circ.hxx>
#include <gp_Cylinder.hxx>
#include <gp_Pln.hxx>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
const double tau = 2 * std::acos(-1.0);
constexpr double lengthTolerance = 1e-6;
using Interval = std::pair<double,double>;

TopoDS_Shape read(const char* path, bool includesSupports) {
    TopoDS_Shape shape;
    BRep_Builder builder;
    if (!BRepTools::Read(shape, path, builder) || shape.IsNull())
        throw std::runtime_error("could not read frozen control BREP");
    if (!includesSupports) return shape;
    // The archived M30703 DRAW fixture holds [result edge, cylinder face, plane face].
    std::vector<TopoDS_Shape> children;
    for (TopoDS_Iterator it(shape); it.More(); it.Next()) children.push_back(it.Value());
    if (children.size() != 3 || children[0].ShapeType() != TopAbs_EDGE ||
        children[1].ShapeType() != TopAbs_FACE || children[2].ShapeType() != TopAbs_FACE)
        throw std::runtime_error("unexpected frozen edge/support layout");
    const BRepAdaptor_Surface cylinder(TopoDS::Face(children[1])), plane(TopoDS::Face(children[2]));
    if (cylinder.GetType() != GeomAbs_Cylinder || plane.GetType() != GeomAbs_Plane
        || std::abs(cylinder.Cylinder().Radius()-5) > lengthTolerance
        || plane.Plane().Distance(gp_Pnt(0,0,0)) > lengthTolerance)
        throw std::runtime_error("unexpected frozen supports");
    return children[0];
}

TopoDS_Shape intersection(bool rings) {
    const gp_Ax3 axes(gp_Pnt(0,0,0),gp_Dir(0,0,1));
    Handle(Geom_Surface) surface;
    if (rings) surface = new Geom_ToroidalSurface(axes,100,20);
    else surface = new Geom_CylindricalSurface(axes,5);
    Handle(Geom_Surface) plane = new Geom_Plane(axes);
    GeomAPI_IntSS op(surface,plane,1e-7);
    if (!op.IsDone()) throw std::runtime_error("section geometry failed");
    BRep_Builder builder;
    TopoDS_Compound result;
    builder.MakeCompound(result);
    for (int i = 1; i <= op.NbLines(); ++i)
        builder.Add(result,BRepBuilderAPI_MakeEdge(op.Line(i)).Edge());
    return result;
}

std::string assess(const TopoDS_Shape& shape, const std::vector<double>& radii) {
    std::vector<std::vector<Interval>> branches(radii.size());
    for (TopExp_Explorer it(shape,TopAbs_EDGE); it.More(); it.Next()) {
        const BRepAdaptor_Curve curve(TopoDS::Edge(it.Current()));
        if (curve.GetType() != GeomAbs_Circle) return "unexpected_curve";
        const auto circle = curve.Circle();
        const auto normal = circle.Axis().Direction();
        if (circle.Location().Distance(gp_Pnt(0,0,0)) > lengthTolerance
            || std::hypot(normal.X(),normal.Y()) > 1e-8) return "displaced";
        auto branch = std::find_if(radii.begin(),radii.end(),[&](double radius) {
            return std::abs(radius-circle.Radius()) <= lengthTolerance;
        });
        if (branch == radii.end()) return "unexpected_radius";
        auto& intervals = branches[branch-radii.begin()];
        const double span = curve.LastParameter()-curve.FirstParameter();
        const auto start = curve.Value(normal.Z()>0 ? curve.FirstParameter() : curve.LastParameter());
        const double angle = std::fmod(std::atan2(start.Y(),start.X())+tau,tau);
        if (!std::isfinite(span) || span <= 0 || span > tau + lengthTolerance / *branch)
            return "invalid_interval";
        const double last = angle + std::min(span,tau);
        intervals.emplace_back(angle,std::min(last,tau));
        if (last > tau) intervals.emplace_back(0,last-tau);
    }
    if (std::any_of(branches.begin(),branches.end(),[](const std::vector<Interval>& b){return b.empty();}))
        return "missing_branch";
    for (std::size_t i=0;i<branches.size();++i) {
        auto& parts = branches[i];
        std::sort(parts.begin(),parts.end());
        double end = 0, largestGap = 0;
        for (const auto& p : parts) {
            largestGap = std::max(largestGap,p.first-end);
            end = std::max(end,p.second);
        }
        largestGap = std::max(largestGap,tau-end);
        std::cout << "METRICS radius=" << radii[i] << " largest_gap=" << largestGap << '\n';
        if (largestGap * radii[i] > lengthTolerance) return "incomplete";
    }
    return "pass";
}
} // namespace

int main(int argc, char** argv) {
    if (argc != 5) return 2;
    std::cout << std::setprecision(17);
    try {
        std::ifstream input(argv[1]);
        std::string mode;
        if (!(input >> mode) || (mode != "cylinder" && mode != "torus" && mode != "cylinder-with-supports")) return 2;
        const bool rings = mode == "torus";
        const bool supports = mode == "cylinder-with-supports";
        const auto radii = rings ? std::vector<double>{80,120} : std::vector<double>{5};
        const auto actual = assess(intersection(rings),radii);
        const auto healthy = assess(read(argv[2],supports),radii);
        const auto wrong = assess(read(argv[3],supports),radii);
        const auto gap = assess(read(argv[4],supports),radii);
        std::cout << "native " << actual << "\nhealthy " << healthy << "\nnegative " << wrong
                  << "\ngap " << gap << '\n';
        if (actual != "pass" || healthy != "pass" || wrong != (rings ? "missing_branch" : "displaced")
            || gap != "incomplete") return 1;
        std::cout << "TEST_DONE\n";
        return 0;
    } catch (const Standard_Failure& failure) {
        std::cerr << failure.GetMessageString() << '\n';
    } catch (const std::exception& failure) {
        std::cerr << failure.what() << '\n';
    }
    return 2;
}
