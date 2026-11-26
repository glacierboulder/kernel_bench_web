"""Finish the WOK output using the Standard copy stage and generic override signatures."""
import re
import sys
from pathlib import Path

src, root = (Path(a).resolve() for a in sys.argv[1:3])
special = root / "inc/Standard_Persistent.hxx"
if not special.exists():
    special.symlink_to(src / "Standard/Standard_Persistent_proto.hxx")
for kind in ["Integer", "Real"]:
    derived = root / f"gen/TCollection_CompareOf{kind}.hxx"
    base = (root / f"gen/TCollection_PrivCompareOf{kind}.hxx").read_text()
    content = derived.read_text()
    for method in ["IsLower", "IsGreater"]:
        pattern = rf"{method}\([^)]*\)"
        inherited = re.search(pattern, base).group()
        if not re.search(pattern, content):
            raise ValueError(f"{derived}: {method} missing")
        content = re.sub(pattern, lambda _: inherited, content)
    if derived.read_text() != content:
        derived.write_text(content)
