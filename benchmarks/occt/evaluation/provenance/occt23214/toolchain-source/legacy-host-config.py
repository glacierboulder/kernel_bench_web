"""Select the Linux headers used by these pre-CMake translation units."""
import re
import sys
from pathlib import Path
root = Path(sys.argv[1])
source = Path(sys.argv[2])
build = root / "build.ninja"
header = root / "legacy-host-config.h"
headers = """
dirent.h dlfcn.h float.h limits.h malloc.h netdb.h net/if.h pwd.h signal.h
stdio.h stdlib.h string.h strings.h sys/errno.h sys/file.h sys/ioctl.h sys/ipc.h
sys/mman.h sys/param.h sys/resource.h sys/sem.h sys/shm.h sys/socket.h sys/stat.h
sys/statvfs.h sys/time.h sys/times.h sys/types.h sys/utsname.h sys/wait.h
time.h unistd.h values.h fcntl.h
""".split()
lines = ["#pragma once", "#define RETSIGTYPE void", "#define HAVE_STATVFS 1"]
for item in headers:
    macro = "HAVE_" + re.sub("[^A-Z0-9]", "_", item.upper())
    lines += [f"#if __has_include(<{item}>)", f"#define {macro} 1", "#endif"]
header.write_text("\n".join(lines)+"\n")
original = build.read_text().splitlines()
new = []
for line in original:
    new.append(line)
    if line.startswith("build obj/") and ": " in line:
        unit = Path(line.rsplit(" ", 1)[1])
        if unit.is_file() and not (root / "gen" in unit.parents):
            text = unit.read_text(errors="ignore")
            if re.search(r"HAVE_[A-Z_]+|RETSIGTYPE", text):
                new.append(f"  cflags = $cflags -include {header}")
build.write_text("\n".join(new)+"\n")
