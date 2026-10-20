# Evaluator-only files

Do not mount or distribute this directory, `private/`, or the prototype root
to an agent. Expose only one `tasks/task_*/` directory. Hidden issue text,
BREP inputs, the hidden C++ reproducer, and the evaluator implementation are
kept here or under `private/evaluator_assets/`.

Run a task evaluator as:

```sh
./private/evaluators/task_single/run_eval.sh PATCH REPORT
./private/evaluators/task_group/run_eval.sh PATCH REPORT
./private/evaluators/task_active/run_eval.sh PATCH REPORT FINDINGS_JSONL
./private/evaluators/task_group_visible3/run_eval.sh PATCH REPORT
./private/evaluators/task_group_visible4/run_eval.sh PATCH REPORT
./private/evaluators/task_group_visible5/run_eval.sh PATCH REPORT
./private/evaluators/task_group_visible5all/run_eval.sh PATCH REPORT
```

`PATCH` may be `-` to read a unified diff from standard input. Evaluators copy
the common source snapshot to a fresh temporary directory, apply the patch,
build the DRAW targets in the existing Conda environment, then execute the
bounded visible/hidden reproductions. Task C additionally validates the
small findings-file contract and path containment; discovery quality is not
scored in this prototype. The `task_group_visible3` evaluator runs only its
three visible issue reproductions and has no hidden issue input.

The web worker invokes `run_eval.py --task visible3` for the public three-issue
group. Its evaluator-side mount contains only that task's visible inputs; it
does not expose the original private evaluator assets.

The generic evaluator also accepts `--task visible4` for the public
#690/#693/#172 group and `--task visible5` for the public #370/#872/#1452
group. `--task visible5all` combines the five public issues #690/#693/#172/
#370/#1452 without hidden checks. Their manual wrappers mount only the
corresponding visible material.
