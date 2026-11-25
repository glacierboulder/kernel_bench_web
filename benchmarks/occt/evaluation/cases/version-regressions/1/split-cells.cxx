// Check the four convex prisms against analytic half-plane clipping.
#include <BOPAlgo_Builder.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepClass3d_SolidClassifier.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRep_Tool.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Edge.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Solid.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Pln.hxx>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
const double angle = std::acos(-1.0)/18, c = std::cos(angle), s = std::sin(angle);
constexpr double positionTolerance = 1e-6, volumeTolerance = 1e-4;

double side(double x, double z) { return c*x - s*(z-5) - 10.25; }

struct Cell {
    std::string name;
    double x0, sign, volume;
    gp_Pnt center;
    std::vector<gp_Pnt> corners;
    std::array<gp_Pnt,3> probes;
};

Cell reference(double left, double sign, const std::string& name) {
    using Point = std::array<double,2>;
    const std::array<Point,4> box = {{{left,0},{left+10,0},{left+10,10},{left,10}}};
    std::vector<Point> polygon;
    for (size_t i = 0; i < box.size(); ++i) {
        const auto a = box[i], b = box[(i+1)%box.size()];
        double ha = sign*side(a[0],a[1]), hb = sign*side(b[0],b[1]);
        if (ha >= 0) polygon.push_back(a);
        if (ha*hb < 0) {
            const double alpha = ha/(ha-hb);
            polygon.push_back({a[0]+alpha*(b[0]-a[0]),a[1]+alpha*(b[1]-a[1])});
        }
    }
    double area2=0, cx=0, cz=0;
    std::vector<gp_Pnt> vertices;
    for (size_t i = 0; i < polygon.size(); ++i) {
        const auto a = polygon[i], b = polygon[(i+1)%polygon.size()];
        const double cross = a[0]*b[1]-a[1]*b[0];
        area2 += cross;
        cx += cross*(a[0]+b[0]);
        cz += cross*(a[1]+b[1]);
        vertices.emplace_back(a[0],0,a[1]);
        vertices.emplace_back(a[0],10,a[1]);
    }
    if (area2 <= 0) throw std::runtime_error("empty analytic cell");
    cx /= 3*area2;
    cz /= 3*area2;
    const auto a = polygon.front(), b = polygon.back();
    return {name,left,sign,5*area2,gp_Pnt(cx,5,cz),vertices,
        {gp_Pnt(cx,5,cz),gp_Pnt(.7*cx+.3*a[0],2,.7*cz+.3*a[1]),
         gp_Pnt(.7*cx+.3*b[0],8,.7*cz+.3*b[1])}};
}

TopoDS_Shape native() {
    const auto a = BRepPrimAPI_MakeBox(10,10,10).Shape();
    const auto b = BRepPrimAPI_MakeBox(gp_Pnt(10.25,0,0),10,10,10).Shape();
    const gp_Pln plane(gp_Pnt(10.25/c,5,5), gp_Dir(c,0,-s));
    const auto splitter = BRepBuilderAPI_MakeFace(plane,-100,100,-100,100).Shape();
    BOPAlgo_Builder builder;
    builder.AddArgument(a); builder.AddArgument(b); builder.AddArgument(splitter);
    builder.Perform();
    if (builder.Shape().IsNull()) throw std::runtime_error("general fuse produced no result");
    return builder.Shape();
}

TopoDS_Shape read(const char* path) {
    TopoDS_Shape result;
    BRep_Builder builder;
    if (!BRepTools::Read(result,path,builder) || result.IsNull())
        throw std::runtime_error("could not read frozen group");
    return result;
}

std::array<double,7> offsets(const gp_Pnt& p,const Cell& cell) {
    return {p.X()-cell.x0, cell.x0+10-p.X(), p.Y(), 10-p.Y(), p.Z(),10-p.Z(),cell.sign*side(p.X(),p.Z())};
}

bool boundary(const TopoDS_Shape& shape,const Cell& cell) {
    std::vector<gp_Pnt> vertices;
    for (TopExp_Explorer it(shape,TopAbs_VERTEX); it.More(); it.Next())
        vertices.push_back(BRep_Tool::Pnt(TopoDS::Vertex(it.Current())));
    if (vertices.empty()) return false;
    for (const auto& p : vertices)
        for (double d : offsets(p,cell))
            if (d < -positionTolerance) return false;
    // All analytic vertices must be present. Extra subdivisions on a facet are allowed.
    for (const auto& p : cell.corners) {
        bool found=false;
        for (const auto& q : vertices) found |= p.Distance(q)<=positionTolerance;
        if (!found) return false;
    }
    for (TopExp_Explorer it(shape,TopAbs_EDGE); it.More(); it.Next())
        if (BRepAdaptor_Curve(TopoDS::Edge(it.Current())).GetType()!=GeomAbs_Line) return false;
    for (TopExp_Explorer it(shape,TopAbs_FACE); it.More(); it.Next()) {
        const auto face = TopoDS::Face(it.Current());
        if (BRepAdaptor_Surface(face).GetType()!=GeomAbs_Plane) return false;
        unsigned common = 127;
        for (TopExp_Explorer v(face,TopAbs_VERTEX); v.More(); v.Next()) {
            const auto d = offsets(BRep_Tool::Pnt(TopoDS::Vertex(v.Current())),cell);
            for (unsigned k=0;k<d.size();++k)
                if (std::abs(d[k])>positionTolerance) common &= ~(1u<<k);
        }
        if (!common) return false;
    }
    return true;
}

struct Verdict { int missing, misplaced; };

Verdict assess(const TopoDS_Shape& result,const std::array<Cell,4>& cells) {
    std::array<bool,4> found = {};
    TopTools_IndexedMapOfShape solids;
    TopExp::MapShapes(result,TopAbs_SOLID,solids);
    int wrong = 0;
    for (int n=1;n<=solids.Extent();++n) {
        const auto shape = solids(n);
        if (!BRepCheck_Analyzer(shape).IsValid()) throw std::runtime_error("invalid cell");
        GProp_GProps mass;
        BRepGProp::VolumeProperties(shape,mass);
        size_t index = cells.size();
        for (size_t k=0;k<cells.size();++k)
            if (std::abs(mass.Mass()-cells[k].volume)<=volumeTolerance) {
                if (index!=cells.size()) throw std::runtime_error("ambiguous cell volume");
                index=k;
            }
        if (index==cells.size() || found[index]) throw std::runtime_error("unexpected or duplicate cell");
        found[index]=true;
        const auto& expected = cells[index];
        BRepClass3d_SolidClassifier classify(TopoDS::Solid(shape));
        int misses=0;
        for (size_t k=0;k<cells.size();++k) for (const auto& p : cells[k].probes) {
            classify.Perform(p,1e-7);
            misses += classify.State()!=(k==index ? TopAbs_IN : TopAbs_OUT);
        }
        const double offset=mass.CentreOfMass().Distance(expected.center);
        const bool contour=boundary(shape,expected);
        wrong += offset>positionTolerance || misses || !contour;
        std::cout << "CELL " << expected.name << " volume=" << mass.Mass()
            << " centroid_error=" << offset << " witnesses_wrong=" << misses << " boundary=" << contour << '\n';
    }
    int missing=0;
    for (size_t k=0;k<cells.size();++k) if (!found[k]) {
        ++missing;
        std::cout << "MISSING " << cells[k].name << '\n';
    }
    return {missing,wrong};
}
} // namespace

int main(int argc,char** argv) {
    if (argc != 7) return 2;
    std::cout << std::setprecision(17);
    try {
        const std::array<Cell,4> cells={reference(0,-1,"A_minus"),reference(0,1,"A_plus"),
                                      reference(10.25,-1,"B_minus"),reference(10.25,1,"B_plus")};
        const char* roles[]={"native","healthy-1","healthy-2","missing","shift-all","shift-one","balanced"};
        const Verdict expected[]={{0,0},{0,0},{0,0},{1,0},{0,4},{0,1},{0,2}};
        bool passed=true;
        for (int i=0;i<7;++i) {
            const auto result=assess(i==0 ? native() : read(argv[i]),cells);
            std::cout << "CONTROL " << roles[i] << " missing=" << result.missing << " misplaced=" << result.misplaced << '\n';
            passed &= result.missing==expected[i].missing && result.misplaced==expected[i].misplaced;
        }
        if (passed) std::cout << "TEST_DONE\n";
        return passed ? 0 : 1;
    } catch (const Standard_Failure& e) {
        std::cerr << e.GetMessageString() << '\n';
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
    }
    return 2;
}
