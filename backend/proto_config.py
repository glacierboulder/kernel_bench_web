"""Resolve the portable catalog and optional legacy OCCT execution bundle."""
from pathlib import Path
import os
from .settings import SETTINGS, ROOT as FRAMEWORK_ROOT


BENCHMARK_ROOT = SETTINGS.benchmark_root
# Kept for existing OCCT worker/evaluator snapshots. New integrations should
# use the catalog under BENCHMARK_ROOT and the source cache, not this layout.
LEGACY_PROTO_ROOT = BENCHMARK_ROOT
explicit_bundle = bool(os.environ.get('BENCHMARK_ROOT') or os.environ.get('BENCH_PROTO_ROOT'))
if not explicit_bundle and not (LEGACY_PROTO_ROOT / 'tasks').is_dir():
    LEGACY_PROTO_ROOT = FRAMEWORK_ROOT.parent / 'OCCT_bench_proto'
PROTO = LEGACY_PROTO_ROOT.resolve()
