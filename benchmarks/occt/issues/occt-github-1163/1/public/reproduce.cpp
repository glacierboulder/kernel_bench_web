#include <BRep_Builder.hxx>
#include <BRepBuilderAPI_Copy.hxx>
#include <BRepBuilderAPI_Transform.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepTools.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <TopoDS.hxx>
#include <gp_Trsf.hxx>
#include <gp_Ax1.hxx>
#include <Standard_Failure.hxx>
#include <fstream>
#include <iostream>
#include <string>
int main(int argc,char** argv) {
  if(argc!=3) {std::cerr << "Usage: test model.brep case.txt\n"; return 2;}
  std::ifstream cfg(argv[2]); std::string mode; cfg >> mode;
  if (!cfg || (mode!="original" && mode!="translate" && mode!="rotate" && mode!="copy" && mode!="box")) return 2;
  BRep_Builder builder; TopoDS_Shape shape;
  if(!BRepTools::Read(shape,argv[1],builder) || shape.IsNull()) {std::cerr << "input unavailable\n";return 2;}
  if (!BRepCheck_Analyzer(shape).IsValid()) {std::cerr << "input invalid\n";return 2;}
  if(mode=="translate" || mode=="rotate") {
    gp_Trsf t;
    if(mode=="translate") t.SetTranslation(gp_Vec(17,-13,9));
    else t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)),0.6457718232379019);
    shape=BRepBuilderAPI_Transform(shape,t,false).Shape();
  }
  if(mode=="copy") shape=BRepBuilderAPI_Copy(shape).Shape();
  if(mode=="box") shape=BRepPrimAPI_MakeBox(20,20,20).Shape();
  NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher> edges;TopExp::MapShapes(shape,TopAbs_EDGE,edges);
  const int index=mode=="box" ? 1 : 7;
  if(edges.Extent()<index) return 2;
  std::cout << "INPUT_OK mode=" << mode << " edge=" << index << std::endl;
  try {
    BRepFilletAPI_MakeFillet op(shape);op.Add(1.0,TopoDS::Edge(edges(index)));op.Build();
    if(!op.IsDone()) {
      if(mode=="copy" || mode=="box") {std::cerr << "control failed\n";return 1;}
      std::cout << "CONTROLLED_FAILURE TEST_DONE\n"; return 0;
    }
    TopoDS_Shape result=op.Shape();
    if(result.IsNull() || !BRepCheck_Analyzer(result).IsValid()) {std::cerr << "invalid result\n";return 1;}
    NCollection_IndexedMap<TopoDS_Shape,TopTools_ShapeMapHasher> faces;TopExp::MapShapes(result,TopAbs_FACE,faces);
    if(faces.Extent()<7) {std::cerr << "too few faces\n";return 1;}
    if(mode=="copy") BRepTools::Write(result,"copy-result.brep",true,false,TopTools_FormatVersion_VERSION_1);
    std::cout << "VALID_RESULT faces=" << faces.Extent() << " TEST_DONE\n";
    return 0;
  } catch(const Standard_Failure& failure) {
    std::cerr << "OCCT exception: " << failure.GetMessageString() << "\n";
    return 1;
  }
}
