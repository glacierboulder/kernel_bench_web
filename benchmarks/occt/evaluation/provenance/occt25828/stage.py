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
helper=r"""
static void diagnostic(const IntWalk_PWalking& walk,const Standard_Integer id,
                       const IntPatch_SequenceOfLine& lines,const char* version) {
  if (id<1 || id>lines.Length()) return;
  Handle(IntPatch_WLine) old=Handle(IntPatch_WLine)::DownCast(lines.Value(id));
  if (old.IsNull()) return;
  const int n=old->NbPnts(), m=walk.NbPoints();
  double before=0, after=0;
  for(int i=1; i<n; ++i) before+=old->Point(i).Value().Distance(old->Point(i+1).Value());
  for(int i=1; i<m; ++i) after+=walk.Value(i).Value().Distance(walk.Value(i+1).Value());
  const int prefer=(n<m || (n==m && before<after));
  std::cerr<<"TRACE duplicate prevPts="<<n<<" nextPts="<<m<<" oldLen="<<before
           <<" newLen="<<after<<" preferNew="<<prefer<<" action="
           <<((version[0]=='F' && prefer)?"replace":"keep")<<std::endl;
}
"""
def source(side):
    ops=[x for x in difflib.SequenceMatcher(None,b,f,autojunk=False).get_opcodes() if x[0]!="equal"]
    assert len(ops)==8 and all(row[0]=="insert" for row in ops)
    lines=list(b if side=="B" else f)
    for _,i,j,k,l in reversed(ops):
        chunk="".join(f[k:l])
        if "static void DublicateOfLinesProcessing" in chunk:
            ix=i if side=="B" else k
            lines.insert(ix,helper)
            continue
        flag=re.search(r"if\((RejetLigne|RejectLine)\)",chunk)[1]
        diagcall='if('+flag+') diagnostic(PW,ver,SLin,"'+side+'");\n'
        ix=i if side=="B" else k
        lines.insert(ix,diagcall)
    return '#include <iostream>\n'+"".join(lines)
flags=["-std=gnu++11","-fPIC","-w","-O0","-DCSFDB","-DLIN","-DLININTEL","-DOCC_CONVERT_SIGNALS","-DHAVE_IOSTREAM","-DHAVE_FSTREAM","-DHAVE_LIMITS_H","-DHAVE_IOMANIP","-DHAVE_UNISTD_H","-DHAVE_TIME_H","-DHAVE_SYS_TYPES_H","-DHAVE_SYS_STAT_H","-DHAVE_PTHREAD_H","-I"+str(build/"inc"),"-I"+str(build/"gen")]
for side in ["B","F"]:
    src=diag/(side+"-"+Path(sourcefile).name)
    src.write_text(source(side))
    obj=diag/(side+".o")
    exe=diag/(side+".exe")
    subprocess.run(["g++",*flags,"-c",src,"-o",obj],check=True)
    subprocess.run(["g++",*flags,case/"probe.cxx",obj,build/"lin64/gcc/lib/libTKBO.a","-ldl","-lpthread","-lm","-o",exe],check=True)
    measured=subprocess.run([exe,"original",assets],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=100)
    (ev/("stage-"+side+".log")).write_text(cfg[side]+"\n"+measured.stdout)
    assert measured.returncode==(side=="B") and "TRACE " in measured.stdout, (side,measured.returncode,measured.stdout[-600:])
