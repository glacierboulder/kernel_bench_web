#include <BRep_Builder.hxx>
#include <BRepBndLib.hxx>
#include <BRepTools.hxx>
#include <Bnd_Box.hxx>
#include <Bnd_BoundSortBox.hxx>
#include <Bnd_HArray1OfBox.hxx>
#include <TColStd_ListOfInteger.hxx>
#include <TopoDS_Shape.hxx>

#include <iostream>

int main(int argc, char** argv)
{
  if (argc != 3)
  {
    std::cerr << "usage: issue_506_repro brd.brep hole.brep\n";
    return 64;
  }

  TopoDS_Shape aBoard;
  TopoDS_Shape aHole;
  BRep_Builder aBuilder;
  if (!BRepTools::Read(aBoard, argv[1], aBuilder)
      || !BRepTools::Read(aHole, argv[2], aBuilder))
  {
    std::cerr << "could not read BREP input\n";
    return 65;
  }

  Bnd_Box aBoardBox;
  BRepBndLib::Add(aBoard, aBoardBox);
  Bnd_Box aHoleBox;
  BRepBndLib::Add(aHole, aHoleBox);
  Bnd_Box anEnclosingBox = aBoardBox;
  anEnclosingBox.Add(aHoleBox);

  Handle(Bnd_HArray1OfBox) aHoleBoxes = new Bnd_HArray1OfBox(0, 0);
  aHoleBoxes->SetValue(0, aHoleBox);

  Bnd_BoundSortBox aSortedBoxes;
  aSortedBoxes.Initialize(anEnclosingBox, aHoleBoxes);
  const TColStd_ListOfInteger& anIndices = aSortedBoxes.Compare(aBoardBox);
  std::cout << "indices.Size(): " << anIndices.Size() << '\n';
  for (TColStd_ListOfInteger::Iterator anIt(anIndices); anIt.More(); anIt.Next())
  {
    std::cout << "Index " << anIt.Value() << '\n';
  }

  return anIndices.Size() == 1 && anIndices.First() == 0 ? 0 : 1;
}
