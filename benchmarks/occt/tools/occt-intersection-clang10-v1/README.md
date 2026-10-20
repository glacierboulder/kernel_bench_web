# OCCT intersection task tools

Run the supplied source build with at most two compiler jobs:

```bash
./tools/build.sh repo build
```

Run a visible Tcl/DRAW case:

```bash
python3 tools/run_draw_case.py \
  --build-dir build --resource-dir repo/resources \
  --case-dir visible/issue_example --script reproduce.tcl
```

Set compiler and Tcl locations through the `BENCH_*` environment variables or
the deployment toolchain profile. The tools do not install dependencies or
refer to a particular user's home directory.

The DRAW runner accepts a case only when the script emits the successful
`bench_finish` oracle summary, including at least one assertion and no failed
assertions. A bare `TEST_DONE` line is insufficient. Each script submitted to
the suite should contain or inline the trusted assertion helper; it must not
load helpers from an unbundled path.
