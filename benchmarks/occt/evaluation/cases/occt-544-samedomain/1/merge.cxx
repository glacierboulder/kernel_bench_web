#include "geometry.hxx"
#include <BRepAlgoAPI_Fuse.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <fstream>
#include <unistd.h>

// The four frozen controls and the candidate kernel's live result share the same reader.
static void measure(const char* geometry, const char* output) {
    const TopoDS_Shape shape = read(geometry);
    std::ofstream stream(output);
    stream.exceptions(std::ios::badbit | std::ios::failbit);
    auto* previous = std::cout.rdbuf(stream.rdbuf());
    try {
        describe(shape);
        std::cout.flush();
    } catch (...) {
        std::cout.rdbuf(previous);
        throw;
    }
    std::cout.rdbuf(previous);
}

int main(int argc, char** argv) {
    if (argc != 5) return 2;
    try {
        std::cout << std::setprecision(17);
        const auto left = BRepPrimAPI_MakeBox(5, 8, 6).Shape();
        const auto right = BRepPrimAPI_MakeBox(gp_Pnt(5, 0, 0), 5, 8, 6).Shape();
        BRepAlgoAPI_Fuse op(left, right);
        if (!op.IsDone() || op.HasErrors()) throw std::runtime_error("fuse failed");
        op.SimplifyResult(true, true);
        if (!op.IsDone() || op.HasErrors() || !BRepTools::Write(op.Shape(), "native.brep"))
            throw std::runtime_error("simplification or serialization failed");
        measure("native.brep", "native.measure");
        const char* outputs[] = {"healthy.measure", "seam.measure", "shift.measure", "notch.measure"};
        for (int n = 0; n < 4; ++n) measure(argv[n+1], outputs[n]);
        execlp("python3", "python3", "-I", "-B", "judge.py", argv[1], argv[2], argv[3], argv[4],
               static_cast<char*>(nullptr));
        throw std::runtime_error("could not start the geometric oracle");
    } catch (const Standard_Failure& error) {
        std::cerr << error.GetMessageString() << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
    }
    return 2;
}
