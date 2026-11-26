"""CDL-era build adapter for the manifest suite."""
from pathlib import Path
import os
import subprocess
import sys
import time


def run(command, cwd, data=None, timeout=3600):
    start = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        return dict(command=list(map(str, command)), return_code=result.returncode, timed_out=False,
                    elapsed_seconds=round(time.monotonic()-start, 3),
                    output_tail=result.stdout.decode(errors="replace")[-12000:])
    except subprocess.TimeoutExpired as exc:
        return dict(command=list(map(str, command)), return_code=None, timed_out=True,
                    elapsed_seconds=round(time.monotonic()-start, 3),
                    output_tail=(exc.stdout or b"").decode(errors="replace")[-12000:])


def apply_patch(source, patch_arg):
    limit = 20 * 1024 * 1024
    with (sys.stdin.buffer if patch_arg == "-" else Path(patch_arg).open("rb")) as stream:
        patch = stream.read(limit + 1)
    if not 0 < len(patch) <= limit:
        raise ValueError("reference patch is empty or too large")
    for flags in (["--check"], []):
        result = run(["git", "apply", *flags, "--whitespace=nowarn", "-"], source, patch, 60)
        if result["return_code"] != 0:
            raise ValueError(result["output_tail"])
    return len(patch)


def configure_and_build(source, build):
    public = Path("/evaluation/cases/bundle/issues/occt-25828/1/public")
    unpack = build / "sdk"
    unpack.mkdir(parents=True)
    extracted = run(["tar", "-xJf", str(public / "cdl-toolchain.tar.xz"), "-C", str(unpack)], build)
    configured = extracted
    if extracted["return_code"] == 0:
        configured = run(["bash", str(unpack / "configure.sh"), str(source), str(build)], build)
    result = dict(configure=configured, build=None)
    if configured["return_code"] == 0:
        jobs = min(2, max(1, int(os.environ.get("BENCH_COMPILER_JOBS", 2))))
        result["build"] = run(["ninja", "-j", str(jobs), "lin64/gcc/lib/libTKBO.a"], build)
    return result
