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
    auto box = BRepPrimAPI_MakeBox(10,20,30).Shape();
    for (double z : {15.,40.}) {
        auto face = BRepBuilderAPI_MakeFace(gp_Pln(0,0,1,-z)).Face();
        BRepAlgoAPI_Common common(face,box);
        if (!common.IsDone() || common.HasWarnings()) return 4;
        GProp_GProps p;
        BRepGProp::SurfaceProperties(common.Shape(),p,1e-8);
        std::cout << "BOX " << z << " AREA " << p.Mass() << std::endl;
        if (std::abs(p.Mass() - (z == 15 ? 200. : 0.)) > 1e-8) return 5;
    }
    std::cout << "TEST_DONE" << std::endl;
}
