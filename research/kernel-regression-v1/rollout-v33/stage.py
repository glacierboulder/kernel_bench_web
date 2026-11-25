"""Build a private qualification archive containing one proposed opt-in suite."""
import argparse
import io
import json
from pathlib import Path
import tarfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BENCH = REPO / "benchmarks/occt"
PREVIOUS = HERE.parent / "rollout-v32"


def candidate():
    suite = json.loads((HERE / "proposed.json").read_text())
    path = f"evaluation/suites/regression/{suite['id']}/{suite['version']}.json"
    entry = {"id": suite["id"], "version": suite["version"], "path": path}
    source = (PREVIOUS / "catalog.snapshot.json").read_text()
    opening = '  "evaluation_suites": [\n'
    if source.count(opening) != 1:
        raise ValueError("catalog inventory")
    index = source.replace(opening, opening + "    " + json.dumps(entry, separators=(",", ":")) + ",\n", 1)
    return {"catalog.json": index, path: (HERE / "proposed.json").read_text()}


def pack(output):
    data = {f"benchmarks/occt/{name}": text for name, text in candidate().items()}
    with tarfile.open(output, "w:gz") as tar:
        for name in ("backend", "benchmarks/occt", "frontend"):
            for file in (REPO / name).rglob("*"):
                path = file.relative_to(REPO).as_posix()
                if file.is_file() and path not in data and not file.name.startswith("._") and "__pycache__" not in file.parts:
                    tar.add(file, path)
        for file in (HERE / "run-entry.sh", HERE / "bwrap-gcc13", HERE / "cmake-receipt", HERE.parent / "rollout-v22/collect.py", HERE.parent / "rollout-v21/neutral.diff"):
            tar.add(file, file.relative_to(REPO))
        for name, content in data.items():
            blob = content.encode()
            item = tarfile.TarInfo(name)
            item.size = len(blob)
            tar.addfile(item, io.BytesIO(blob))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    pack(parser.parse_args().pack)
