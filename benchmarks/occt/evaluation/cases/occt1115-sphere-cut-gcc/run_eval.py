from pathlib import Path
import subprocess

def apply_patch(source, patch_arg):
    patch = Path(patch_arg).resolve()
    size = patch.stat().st_size
    if size:
        result = subprocess.run(["git", "apply", str(patch)], cwd=source, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ValueError(result.stderr)
    return size

def configure_and_build(source, build):
    result = subprocess.run([
        "cmake", "-S", str(source), "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG", "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
        *[f"-DBUILD_MODULE_{name}=OFF" for name in (
            "ApplicationFramework", "DataExchange", "Draw", "FoundationClasses",
            "ModelingAlgorithms", "ModelingData", "Visualization")],
        "-DBUILD_ADDITIONAL_TOOLKITS=TKBO;TKPrim", "-DUSE_FREETYPE=OFF", "-DUSE_TK=OFF",
    ], capture_output=True, text=True, timeout=180)
    out = {"configure": {"return_code": result.returncode, "output_tail": (result.stdout + result.stderr)[-12000:]}}
    if result.returncode == 0:
        result = subprocess.run(["cmake", "--build", str(build), "--parallel", "8", "--target", "TKBO", "TKPrim"],
                                capture_output=True, text=True, timeout=10200)
        out["build"] = {"return_code": result.returncode, "output_tail": (result.stdout + result.stderr)[-12000:]}
    return out

