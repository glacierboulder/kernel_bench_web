// Exact per-span bounds for a straight section on two planar supports.
#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepAlgoAPI_Section.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <Geom2d_BSplineCurve.hxx>
#include <Geom2d_Line.hxx>
#include <Geom2d_TrimmedCurve.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Iterator.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Pln.hxx>
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr double geometryTol=1e-7, domainTol=1e-10;

struct Section { TopoDS_Edge edge; std::array<TopoDS_Face,2> faces; };

Section native() {
    const gp_Ax3 xy(gp_Pnt(0,0,0),gp_Dir(0,0,1),gp_Dir(1,0,0));
    const gp_Ax3 yz(gp_Pnt(0,0,0),gp_Dir(1,0,0),gp_Dir(0,1,0));
    const TopoDS_Face a=BRepBuilderAPI_MakeFace(gp_Pln(xy),-1,1,-5,5).Face();
    const TopoDS_Face b=BRepBuilderAPI_MakeFace(gp_Pln(yz),-5,5,-1,1).Face();
    BRepAlgoAPI_Section op(a,b,Standard_False);
    op.Approximation(Standard_True);
    op.ComputePCurveOn1(Standard_True);
    op.ComputePCurveOn2(Standard_True);
    op.Build();
    if (!op.IsDone() || op.Shape().IsNull()) throw std::runtime_error("section build failed");
    TopExp_Explorer edges(op.Shape(),TopAbs_EDGE);
    if (!edges.More()) throw std::runtime_error("section is empty");
    const auto edge=TopoDS::Edge(edges.Current());
    edges.Next();
    if (edges.More()) throw std::runtime_error("section has multiple edges");
    return {edge,{a,b}};
}

Section read(const char* path) {
    BRep_Builder builder;
    TopoDS_Shape pack;
    if (!BRepTools::Read(pack,path,builder) || pack.IsNull()) throw std::runtime_error("could not read frozen section");
    std::vector<TopoDS_Shape> parts;
    for (TopoDS_Iterator it(pack);it.More();it.Next()) parts.push_back(it.Value());
    if (parts.size()!=3 || parts[0].ShapeType()!=TopAbs_EDGE ||
        parts[1].ShapeType()!=TopAbs_FACE || parts[2].ShapeType()!=TopAbs_FACE)
        throw std::runtime_error("expected edge followed by XY and YZ faces");
    return {TopoDS::Edge(parts[0]),{TopoDS::Face(parts[1]),TopoDS::Face(parts[2])}};
}

bool support(const TopoDS_Face& face,bool yz) {
    const BRepAdaptor_Surface surface(face);
    if (surface.GetType()!=GeomAbs_Plane) return false;
    const auto plane=surface.Plane();
    if (plane.Distance(gp_Pnt(0,0,0))>geometryTol) return false;
    const auto normal=plane.Axis().Direction();
    if (std::abs(std::abs(yz ? normal.X() : normal.Z())-1)>domainTol) return false;
    std::array<bool,4> corners={};
    int edges=0,wires=0;
    for (TopExp_Explorer it(face,TopAbs_WIRE);it.More();it.Next()) ++wires;
    for (TopExp_Explorer it(face,TopAbs_EDGE);it.More();it.Next()) {
        ++edges;
        const BRepAdaptor_Curve edge(TopoDS::Edge(it.Current()));
        if (edge.GetType()!=GeomAbs_Line) return false;
        for (double t : {edge.FirstParameter(),edge.LastParameter()}) {
            const auto p=edge.Value(t);
            const double lateral=yz ? p.Z() : p.X();
            if (std::abs(std::abs(lateral)-1)>geometryTol || std::abs(std::abs(p.Y())-5)>geometryTol)
                return false;
            const int id=(lateral>0 ? 1 : 0) | (p.Y()>0 ? 2 : 0);
            corners[id]=true;
        }
    }
    return wires==1 && edges==4 && std::all_of(corners.begin(),corners.end(),[](bool x){return x;});
}

struct Error {
    double full=0,start=0,end=0,coarse=0,peak=0;
    size_t spans=0;
};

Error certifiedError(const TopoDS_Edge& edge,const TopoDS_Face& face,const BRepAdaptor_Curve& line) {
    const double lo=line.FirstParameter(), hi=line.LastParameter();
    double pLo,pHi;
    const auto pc=BRep_Tool::CurveOnSurface(edge,face,pLo,pHi);
    if (pc.IsNull() || std::abs(pLo-lo)>domainTol || std::abs(pHi-hi)>domainTol ||
        pc->FirstParameter()>lo+domainTol || pc->LastParameter()<hi-domainTol)
        throw std::runtime_error("UV range does not match the full three-dimensional edge");
    auto basis=pc;
    while (true) {
        const auto trim=Handle(Geom2d_TrimmedCurve)::DownCast(basis);
        if (trim.IsNull()) break;
        basis=trim->BasisCurve();
    }
    std::vector<double> cuts{lo,hi};
    const auto spline=Handle(Geom2d_BSplineCurve)::DownCast(basis);
    if (Handle(Geom2d_Line)::DownCast(basis).IsNull()) {
        if (spline.IsNull() || spline->Degree()!=1 || spline->IsRational() || spline->IsPeriodic() ||
            spline->FirstParameter()>lo+domainTol || spline->LastParameter()<hi-domainTol)
            throw std::runtime_error("UV basis cannot certify the full affine span");
        for (int i=1;i<=spline->NbKnots();++i) {
            const double t=spline->Knot(i);
            if (lo<t && t<hi) {
                if (spline->Multiplicity(i)!=1) throw std::runtime_error("UV curve is not continuous at a knot");
                cuts.push_back(t);
            }
        }
    }
    std::sort(cuts.begin(),cuts.end());
    if (std::adjacent_find(cuts.begin(),cuts.end())!=cuts.end()) throw std::runtime_error("duplicate span boundary");
    const BRepAdaptor_Surface surface(face);
    auto difference=[&](double t) {
        const auto uv=pc->Value(t);
        const double error=line.Value(t).Distance(surface.Value(uv.X(),uv.Y()));
        if (!std::isfinite(error)) throw std::runtime_error("non-finite error");
        return error;
    };
    Error e;
    e.start=difference(lo);
    e.end=difference(hi);
    e.peak=lo;
    e.spans=cuts.size()-1;
    // On each complete knot interval, C(t) and S(U(t),V(t)) are affine.
    // The norm of their difference is convex and attains its maximum at an endpoint.
    for (double t:cuts) {
        const double error=difference(t);
        if (error>e.full) {e.full=error;e.peak=t;}
    }
    for (int k=0;k<=16;++k) e.coarse=std::max(e.coarse,difference(lo+(hi-lo)*k/16));
    return e;
}

std::string assess(const Section& section) {
    if (!support(section.faces[0],false) || !support(section.faces[1],true))
        throw std::runtime_error("frozen planar support or its rectangular trim changed");
    const BRepAdaptor_Curve c(section.edge);
    if (c.GetType()!=GeomAbs_Line || c.LastParameter()<=c.FirstParameter())
        throw std::runtime_error("3D section is not an affine segment");
    const auto a=c.Value(c.FirstParameter()),b=c.Value(c.LastParameter());
    const auto& low=a.Y()<b.Y()?a:b;
    const auto& high=a.Y()<b.Y()?b:a;
    const bool whole=low.Distance(gp_Pnt(0,-5,0))<=geometryTol && high.Distance(gp_Pnt(0,5,0))<=geometryTol;
    TopoDS_Vertex v,w;
    TopExp::Vertices(section.edge,v,w);
    if (v.IsNull() || w.IsNull() || v.IsSame(w)) throw std::runtime_error("missing section vertices");
    const auto p=BRep_Tool::Pnt(v),q=BRep_Tool::Pnt(w);
    if (!(p.Distance(a)<=geometryTol && q.Distance(b)<=geometryTol) &&
        !(q.Distance(a)<=geometryTol && p.Distance(b)<=geometryTol))
        throw std::runtime_error("topological endpoints differ from the 3D trim");
    const bool valid=BRepCheck_Analyzer(section.edge).IsValid();
    std::cout << "RANGE y_min=" << low.Y() << " y_max=" << high.Y() << " valid=" << valid << '\n';
    std::array<Error,2> errors;
    for (size_t side=0;side<errors.size();++side) {
        auto& e=errors[side];
        e=certifiedError(section.edge,section.faces[side],c);
        std::cout << "UV side=" << side+1 << " spans=" << e.spans << " maximum=" << e.full
                  << " at_t=" << e.peak << " start=" << e.start << " end=" << e.end
                  << " diagnostic_17_point_max=" << e.coarse << '\n';
    }
    if (!whole) return "truncated";
    if (errors[0].full>geometryTol) return "first_side_mismatch";
    if (errors[1].full>geometryTol) return "second_side_mismatch";
    return valid?"pass":"invalid";
}
} // namespace

int main(int argc,char** argv) {
    if (argc!=5) return 2;
    std::cout << std::setprecision(17);
    try {
        const char* roles[]={"native","healthy-1","healthy-2","short","one-side"};
        const char* expected[]={"pass","pass","pass","truncated","second_side_mismatch"};
        bool matched=true;
        for (int i=0;i<5;++i) {
            const auto verdict=assess(i==0 ? native() : read(argv[i]));
            std::cout << "CONTROL " << roles[i] << ' ' << verdict << '\n';
            matched &= verdict==expected[i];
        }
        if (matched) std::cout << "TEST_DONE\n";
        return matched?0:1;
    } catch (const Standard_Failure& e) {
        std::cerr << e.GetMessageString() << '\n';
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
    }
    return 2;
}
