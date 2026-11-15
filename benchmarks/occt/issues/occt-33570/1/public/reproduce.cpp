#include <TopExp.hxx>
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepPrimAPI_MakeSphere.hxx>
#include <TopExp_Explorer.hxx>
#include <cstdio>
int main() {
  auto a = BRepPrimAPI_MakeSphere(gp_Pnt(0,5.5,18),4).Shape();
  auto b = BRepPrimAPI_MakeSphere(gp_Pnt(0,4.5,14),1).Shape();
  BRepAlgoAPI_Cut cut(a,b);
  if (!cut.IsDone()) return 2;
  int expected[] = {4,7,2,2};
  TopAbs_ShapeEnum types[] = {TopAbs_VERTEX,TopAbs_EDGE,TopAbs_WIRE,TopAbs_FACE};
  bool pass = true;
  for (int i=0;i<4;++i) {
    NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher> map;
    TopExp::MapShapes(cut.Shape(),types[i],map);
    std::printf("type=%d actual=%d expected=%d\n",types[i],map.Extent(),expected[i]);
    pass &= map.Extent()==expected[i];
  }
  return pass ? 0 : 1;
}

