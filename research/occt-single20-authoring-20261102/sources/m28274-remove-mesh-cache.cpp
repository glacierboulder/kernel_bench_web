#include <BRepTools.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS_Shape.hxx>
#include <cmath>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  BRep_Builder builder;
  TopoDS_Shape original;
  std::ifstream upstream("/workspace/upstream.brep");
  BRepTools::Read(original, upstream, builder);
  if (original.IsNull()) return 3;
  const std::string outputPath = std::string(argv[1]) + "/bug28274-exact.brep";
  {
    std::ofstream output(outputPath);
    output << "DBRep_DrawableShape\n\n";
    BRepTools::Write(original, output, false, false, TopTools_FormatVersion_VERSION_1);
    if (!output.good()) return 4;
  }
  std::ifstream input(outputPath);
  std::string header;
  std::getline(input, header);
  std::getline(input, header);
  TopoDS_Shape restored;
  BRepTools::Read(restored, input, builder);
  if (restored.IsNull() || !BRepCheck_Analyzer(restored).IsValid()) return 5;
  for (TopAbs_ShapeEnum kind : {TopAbs_VERTEX, TopAbs_EDGE, TopAbs_WIRE, TopAbs_FACE}) {
    TopTools_IndexedMapOfShape before, after;
    TopExp::MapShapes(original, kind, before);
    TopExp::MapShapes(restored, kind, after);
    if (before.Extent() != after.Extent()) return 6;
    std::cout << "PRESERVED_TOPOLOGY kind=" << kind << " count=" << before.Extent() << '\n';
  }
  GProp_GProps before, after;
  BRepGProp::SurfaceProperties(original, before);
  BRepGProp::SurfaceProperties(restored, after);
  const double difference = std::abs(before.Mass() - after.Mass());
  if (difference > 1.e-12 * std::abs(before.Mass())) return 7;
  std::cout << "INPUT_VALID exact_BREP_preserved=1 mesh_cache_excluded=1 area_difference="
            << difference << '\n';
  return 0;
}
