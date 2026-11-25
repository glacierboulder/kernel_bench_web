// OCCT 8 names this exact TopExp::MapShapes argument type explicitly.
#pragma once
#include <NCollection_IndexedMap.hxx>
#include <TopTools_ShapeMapHasher.hxx>
#include <TopoDS_Shape.hxx>
using TopTools_IndexedMapOfShape = NCollection_IndexedMap<TopoDS_Shape, TopTools_ShapeMapHasher>;
