// Directly invoke the WOK CPPExt library on the schema read by mstranslate.
#include <tcl.h>
#include <WOKBuilder_MSTool.hxx>
#include <WOKBuilder_MSchema.hxx>
#include <TCollection_HAsciiString.hxx>
#include <TColStd_HSequenceOfHAsciiString.hxx>
#include <Standard_Failure.hxx>
#include <CPPExt.hxx>

static int extract(ClientData, Tcl_Interp* interp, int argc, const char** argv) {
    if (argc != 4) {
        Tcl_SetResult(interp, const_cast<char*>("usage: extract_type NAME TEMPLATE_DIR OUTPUT_DIR"), TCL_STATIC);
        return TCL_ERROR;
    }
    try {
        Handle(TColStd_HSequenceOfHAsciiString) dirs = new TColStd_HSequenceOfHAsciiString;
        dirs->Append(new TCollection_HAsciiString(argv[2]));
        Handle(TColStd_HSequenceOfHAsciiString) generated = new TColStd_HSequenceOfHAsciiString;
        CPP_Extract(WOKBuilder_MSTool::GetMSchema()->MetaSchema(),
                    new TCollection_HAsciiString(argv[1]), dirs,
                    new TCollection_HAsciiString(argv[3]), generated, "CSFDB");
        for (int i = 1; i <= generated->Length(); ++i) {
            Tcl_AppendElement(interp, generated->Value(i)->ToCString());
        }
        return TCL_OK;
    } catch (const Standard_Failure& e) {
        Tcl_SetResult(interp, const_cast<char*>(e.GetMessageString()), TCL_VOLATILE);
        return TCL_ERROR;
    }
}

extern "C" int Directwok_Init(Tcl_Interp* interp) {
    Tcl_CreateCommand(interp, "extract_type", extract, 0, 0);
    return TCL_OK;
}
