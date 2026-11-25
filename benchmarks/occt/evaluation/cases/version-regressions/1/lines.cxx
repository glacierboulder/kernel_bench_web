// Independent checks for infinite cylinder generators and bounded plane section edges.
#include <BRepAdaptor_Curve.hxx>
#include <BRepAlgoAPI_Section.hxx>
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GeomAPI_IntSS.hxx>
#include <Geom_CylindricalSurface.hxx>
#include <Geom_Plane.hxx>
#include <Precision.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Lin.hxx>
#include <gp_Pln.hxx>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
constexpr double tol = 1e-7;

TopoDS_Shape read(const char* p) {
    TopoDS_Shape s;
    BRep_Builder b;
    if (!BRepTools::Read(s,p,b) || s.IsNull()) throw std::runtime_error("could not read line control");
    return s;
}

TopoDS_Shape native(bool unbounded) {
    const gp_Pln transverse(gp_Pnt(0,0,0),gp_Dir(1,0,0));
    if (unbounded) {
        const gp_Ax3 axes(gp_Pnt(0,0,0),gp_Dir(0,0,1));
        Handle(Geom_Surface) cylinder = new Geom_CylindricalSurface(axes,100);
        Handle(Geom_Surface) plane = new Geom_Plane(transverse);
        GeomAPI_IntSS op(cylinder,plane,1e-7);
        if (!op.IsDone()) throw std::runtime_error("surface intersection did not finish");
        TopoDS_Compound result;
        BRep_Builder builder;
        builder.MakeCompound(result);
        for (int i=1;i<=op.NbLines();++i)
            builder.Add(result, BRepBuilderAPI_MakeEdge(op.Line(i)).Edge());
        return result;
    }
    const gp_Pln horizontal(gp_Pnt(0,0,0),gp_Dir(0,0,1));
    const auto a = BRepBuilderAPI_MakeFace(horizontal,-20,20,-20,20).Face();
    const auto b = BRepBuilderAPI_MakeFace(transverse,-20,20,-20,20).Face();
    BRepAlgoAPI_Section op(a,b);
    if (!op.IsDone()) throw std::runtime_error("topology section did not finish");
    return op.Shape();
}

std::string evaluate(const TopoDS_Shape& result,bool unbounded) {
    int count = 0;
    unsigned sides = 0;
    bool truncated = false;
    for (TopExp_Explorer it(result,TopAbs_EDGE);it.More();it.Next()) {
        ++count;
        const auto edge = TopoDS::Edge(it.Current());
        const BRepAdaptor_Curve curve(edge);
        if (curve.GetType()!=GeomAbs_Line) return "not_a_line";
        const auto line = curve.Line();
        const double a = curve.FirstParameter(), b = curve.LastParameter();
        TopoDS_Vertex first,last;
        TopExp::Vertices(edge,first,last);
        if (unbounded) {
            if (std::abs(line.Location().X())>tol || std::abs(std::abs(line.Location().Y())-100)>tol
                || std::hypot(line.Direction().X(),line.Direction().Y())>tol) return "displaced";
            unsigned which = line.Location().Y()>0 ? 1 : 2;
            if (sides & which) return "duplicate";
            sides |= which;
            truncated |= !Precision::IsNegativeInfinite(a) || !Precision::IsPositiveInfinite(b)
                         || !first.IsNull() || !last.IsNull();
        } else {
            if (line.Distance(gp_Pnt(0,0,0))>tol || std::hypot(line.Direction().X(),line.Direction().Z())>tol)
                return "displaced";
            if (first.IsNull() || last.IsNull()) return "missing_endpoints";
            const auto p = curve.Value(a), q = curve.Value(b);
            const double lo = std::min(p.Y(),q.Y()), hi = std::max(p.Y(),q.Y());
            std::cout << "METRICS segment_y=" << lo << ' ' << hi << '\n';
            if (std::abs((hi-lo)-40)>tol) return "truncated";
            if (std::abs(lo+20)>tol || std::abs(hi-20)>tol) return "shifted";
        }
    }
    if (count != (unbounded ? 2 : 1)) return "missing_branch";
    return truncated ? "truncated" : "pass";
}
} // namespace

int main(int argc,char** argv) {
    if (argc!=5) return 2;
    try {
        std::ifstream selector(argv[1]);
        std::string mode;
        if (!(selector>>mode) || (mode!="generators" && mode!="finite-section")) return 2;
        const bool unbounded = mode=="generators";
        auto current = evaluate(native(unbounded),unbounded);
        auto healthy = evaluate(read(argv[2]),unbounded);
        auto wrong = evaluate(read(argv[3]),unbounded);
        auto truncated = evaluate(read(argv[4]),unbounded);
        std::cout << "native " << current << "\nhealthy " << healthy << "\nnegative " << wrong
                  << "\ntruncated " << truncated << '\n';
        if (current!="pass" || healthy!="pass" || wrong!=(unbounded?"duplicate":"shifted")
            || truncated!="truncated") return 1;
        std::cout << "TEST_DONE\n";
        return 0;
    } catch (const Standard_Failure& failure) {
        std::cerr << failure.GetMessageString() << '\n';
    } catch (const std::exception& failure) {
        std::cerr << failure.what() << '\n';
    }
    return 2;
}
