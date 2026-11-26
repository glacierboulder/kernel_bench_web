"""Instrument the modified unit in isolation; the source checkout stays untouched."""
import difflib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

here=Path(__file__).resolve().parent
case=here if (here/"identity.json").is_file() else here.parent
cfg=json.loads((case/"identity.json").read_bytes())
run, ev=map(Path,sys.argv[1:])
root=Path(os.environ.get("OCCT_NATURAL_ROOT","/mnt/r27-builds/dedup-"+cfg["issue"]))
assets=case/"assets" if (case/"assets").is_dir() else case.parents[2]/"issues"/("occt-"+cfg["issue"])/"1/public"
repo=root/"source"
build=root/"build"
diag=root/"stage-diagnostic"
diag.mkdir(exist_ok=True)
sourcefile=cfg["production_path"]
def at(rev):
    return subprocess.check_output(["git","-C",repo,"show",rev+":"+sourcefile]).decode().splitlines(keepends=True)
b,f=map(at,[cfg["B"],cfg["F"]])
def source(side):
    text="".join(b if side=="B" else f)
    anchor="BOPAlgo_Tools::FillMap(aPB, nF, aMPBLI, aAllocator);\n              break;"
    assert text.count(anchor)==1
    text=text.replace(anchor,'std::cerr<<"TRACE ef-edge face="<<nF<<" edge="<<nE<<" queued="<<aMIEFC.Contains(nF)<<"\\n";\n              '+anchor)
    anchor="myDS->UpdateFaceInfoIn(nF);"
    assert text.count(anchor)==1
    text=text.replace(anchor,'std::cerr<<"TRACE updateFaceInfoIn face="<<nF<<"\\n";\n    '+anchor)
    return '#include <iostream>\n'+text
flags=["-std=gnu++11","-fPIC","-w","-O0","-DCSFDB","-DLIN","-DLININTEL","-DOCC_CONVERT_SIGNALS","-DHAVE_IOSTREAM","-DHAVE_FSTREAM","-DHAVE_LIMITS_H","-DHAVE_IOMANIP","-DHAVE_UNISTD_H","-DHAVE_TIME_H","-DHAVE_SYS_TYPES_H","-DHAVE_SYS_STAT_H","-DHAVE_PTHREAD_H","-I"+str(build/"inc"),"-I"+str(build/"gen")]
for side in ["B","F"]:
    src=diag/(side+"-"+Path(sourcefile).name)
    src.write_text(source(side))
    obj=diag/(side+".o")
    exe=diag/(side+".exe")
    subprocess.run(["g++",*flags,"-c",src,"-o",obj],check=True)
    subprocess.run(["g++",*flags,case/"probe.cxx",obj,build/"lin64/gcc/lib/libTKBO.a","-ldl","-lpthread","-lm","-o",exe],check=True)
    measured=subprocess.run([exe,"original",assets],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=100)
    assert measured.returncode==(side=="B") and "TRACE " in measured.stdout
    (ev/("stage-"+side+".log")).write_text(cfg[side]+"\n"+measured.stdout)
