"""Verify completed DRAW checkpoints, including shell tolerance on defect cases."""
import argparse
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("log", type=Path)
parser.add_argument("exit_code", type=int)
parser.add_argument("--regression", action="store_true")
args = parser.parse_args()
text = args.log.read_text(errors="replace")
ok = args.exit_code == 0 and text.splitlines().count("CASE_PASS") == 1
ok = ok and not re.search(r"RUN_ERROR|SIGSEGV|An exception was caught", text)
if not args.regression:
    dumps = re.search(r"TOL_BEFORE_DUMP(.*?)TOL_AFTER_DUMP(.*?)TOL_END_DUMP", text, re.S)
    if dumps is None:
        ok = False
    else:
        maxima = []
        for dump in dumps.groups():
            values = [float(v) for v in re.findall(r"Tolerance\s*:\s*([-+0-9.eE]+)", dump)]
            maxima.append(max(values, default=-1))
        before, after = maxima
        ok = ok and before > 0 and after > 0 and after - before <= 0.0001 + 0.0001 * before
print("PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
