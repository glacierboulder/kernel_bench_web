#include <BOPDS_DS.hxx>
#include <BOPDS_Interf.hxx>
#include <BOPDS_Curve.hxx>
#define main measured_shape_main
#include "probe.cxx"
#undef main

int main() {
    TopoDS_Shape a=rot(BRepPrimAPI_MakeCylinder(0.069,0.6).Shape(),0,0,1,90);
    TopoDS_Shape b=rot(BRepPrimAPI_MakeCylinder(0.024,0.4).Shape(),0,1,0,90);
    b=trans(rot(b,1,0,0,-45),-0.2,0,0.48);
    BOPCol_ListOfShape args;args.Append(a);args.Append(b);
    Handle(NCollection_BaseAllocator) mem=new NCollection_IncAllocator;
    BOPAlgo_PaveFiller pf(mem);pf.SetArguments(args);pf.SetFuzzyValue(0);pf.SetRunParallel(false);pf.Perform();
    if (pf.ErrorStatus()) return 2;
    BOPDS_VectorOfInterfFF& ff=pf.PDS()->InterfFF();
    for (int i=0;i<ff.Extent();++i) {
        BOPDS_InterfFF& hit=ff(i);
        const BOPDS_VectorOfCurve& curves=hit.Curves();
        std::cout<<"face_pair="<<i<<" curves="<<curves.Extent()<<" segments=";
        for (int j=0;j<curves.Extent();++j) std::cout<<curves(j).PaveBlocks().Extent()<<",";
        std::cout<<"\n";
    }
}
