"""Write a portable Ninja build for the original geometric toolkits and WOK products."""
from pathlib import Path
import sys

src, root = (Path(arg).resolve() for arg in sys.argv[1:3])
toolkits = "TKernel TKMath TKG2d TKG3d TKGeomBase TKBRep TKGeomAlgo TKTopAlgo TKPrim TKBO".split()
packages = set()
for toolkit in toolkits:
    packages.update((src / toolkit / "PACKAGES").read_text().split())
real = sorted(p for pkg in packages for p in (src / pkg).glob("*")
              if p.suffix in {".c", ".cxx"} and not p.name.startswith("WNT"))
generated = sorted((root / "gen").glob("*.cxx"))
flags = ("-fPIC -w -O0 -DCSFDB -DLIN -DLININTEL -DOCC_CONVERT_SIGNALS "
         "-DHAVE_IOSTREAM -DHAVE_FSTREAM -DHAVE_LIMITS_H -DHAVE_IOMANIP "
         "-DHAVE_UNISTD_H -DHAVE_TIME_H -DHAVE_SYS_TYPES_H -DHAVE_SYS_STAT_H "
         "-DHAVE_PTHREAD_H -Iinc -Igen")
lines = [f"cflags = {flags}", "rule cpp",
         "  command = g++ -std=gnu++11 $cflags -MMD -MF $out.d -c $in -o $out",
         "  depfile = $out.d", "  deps = gcc", "rule cc",
         "  command = gcc $cflags -MMD -MF $out.d -c $in -o $out",
         "  depfile = $out.d", "  deps = gcc", "rule archive",
         "  command = ar rcs $out $in", ""]
objs = []
for file in real + generated:
    obj = "obj/" + file.name + ".o"
    if obj in objs:
        raise ValueError(f"Duplicate source name: {file}")
    objs.append(obj)
    lines.append(f"build {obj}: {'cc' if file.suffix == '.c' else 'cpp'} {file}")
lines.append(f"build lin64/gcc/lib/libTKBO.a: archive {' '.join(objs)}")
lines.append("default lin64/gcc/lib/libTKBO.a")
(root / "build.ninja").write_text("\n".join(lines) + "\n")
print(len(real), "original translation units,", len(generated), "generated units")
