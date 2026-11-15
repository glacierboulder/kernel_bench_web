#include <BRepAlgoAPI_Common.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <gp_Ax3.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <iomanip>
#include <cmath>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRep_Tool.hxx>
#include <TopoDS.hxx>
#include <TopExp_Explorer.hxx>
#include <gp_Pln.hxx>
#include <fstream>
#include <iostream>
int main() {
    std::ifstream in("fuselage-derived.brep");
    std::string header;
    std::getline(in, header);
    TopoDS_Shape solid;
    BRepTools::Read(solid, in, BRep_Builder());
    if (solid.IsNull()) return 2;
    std::cout << std::setprecision(14);
    int fail = 0;
    double reference=0;
    for (double angle : {0.,90.}) {
        double rad = angle*std::acos(-1.)/180;
        gp_Ax3 axes(gp_Pnt(),gp_Dir(0,0,1),gp_Dir(std::cos(rad),std::sin(rad),0));
        const auto plane = BRepBuilderAPI_MakeFace(gp_Pln(axes)).Face();
        BRepAlgoAPI_Common common(plane, solid);
        auto result = common.Shape();
        if (!common.IsDone() || result.IsNull()) return 3;
        GProp_GProps props;
        BRepGProp::SurfaceProperties(result,props);
        GProp_GProps adaptive;
        BRepGProp::SurfaceProperties(result,adaptive,1e-8);
        if (angle == 0) reference=adaptive.Mass();
        int faces=0;
        for(TopExp_Explorer it(result,TopAbs_FACE);it.More();it.Next()) ++faces;
        std::cout << "ANGLE " << angle << " FACE " << faces
                  << " AREA " << props.Mass()
                  << " ADAPTIVE_AREA " << adaptive.Mass()
                  << " WARN " << common.HasWarnings()
                  << " VALID " << BRepCheck_Analyzer(result).IsValid() << std::endl;
        if (faces != 1 || common.HasWarnings() || !BRepCheck_Analyzer(result).IsValid()
            || !std::isfinite(adaptive.Mass()) || adaptive.Mass() <= 0
            || std::abs(adaptive.Mass()-reference) > reference*1e-4) ++fail;
    }
    if (fail) return 1;

    std::cout << "TEST_DONE" << std::endl;
}
