#!/usr/bin/env python3
"""Odyssey Engine Helper CLI.

Manages JSONL experiment logs, project auto-detection, convergence profiles,
and state evaluation. Forked from autoresearch_helper.py with additions for
odyssey-engine. Uses stdlib only — no external dependencies.
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Project Auto-Detection ──

PROJECT_RULES = [
    ("Cargo.toml", "rust", "cargo check 2>&1", "cargo test 2>&1", "compilation_warnings"),
    ("go.mod", "go", "go vet ./... 2>&1", "go test ./... 2>&1", "test_pass_rate"),
    ("pyproject.toml", "python", 'python3 -c "import ast; [ast.parse(open(f).read()) for f in __import__(\'glob\').glob(\'**/*.py\', recursive=True)]" 2>&1', "pytest --tb=short -q 2>&1", "test_pass_rate"),
    ("setup.py", "python", 'python3 -c "import py_compile; [py_compile.compile(f, doraise=True) for f in __import__(\'glob\').glob(\'**/*.py\', recursive=True)]" 2>&1', "pytest --tb=short -q 2>&1", "test_pass_rate"),
    ("package.json", "typescript", "npx tsc --noEmit 2>&1", "npm test 2>&1", "type_error_count"),
    ("package.json", "javascript", "node --check 2>&1", "npm test 2>&1", "test_pass_rate"),
    ("Makefile", "make", "make -n 2>&1", "make test 2>&1", "exit_code"),
]

SENTINEL_ORDER = ["Cargo.toml", "go.mod", "pyproject.toml", "setup.py", "package.json", "Makefile"]

# ── Convergence Profiles ──
# Each tier maps project characteristics to convergence parameters.
# Higher tiers = more patience, stricter diminishing-return thresholds.

CONVERGENCE_PROFILES = {
    "prototype": {
        # Throwaway code, scripts, demos. Iterate fast, give up fast.
        "patience_budget": 15,            # max total waypoints
        "discard_threshold": 5,           # consecutive discards → stuck
        "min_metric_delta_pct": 1.0,      # <1% improvement = diminishing
        "convergence_window": 3,          # waypoints to examine for convergence
        "guard_timeout_mult": 0.5,        # tests should be fast
        "auto_orient_switch": True,       # stuck → auto try creative
        "description": "throwaway scripts, demos, experiments",
    },
    "standard": {
        # Normal project with some tests or CI. Balanced.
        "patience_budget": 30,
        "discard_threshold": 10,
        "min_metric_delta_pct": 0.5,
        "convergence_window": 5,
        "guard_timeout_mult": 1.0,
        "auto_orient_switch": True,
        "description": "typical project with tests or CI",
    },
    "production": {
        # Mission-critical. Patient iteration, strict convergence, no auto-switch
        # (human review required before changing strategy).
        "patience_budget": 50,
        "discard_threshold": 15,
        "min_metric_delta_pct": 0.1,
        "convergence_window": 5,
        "guard_timeout_mult": 2.0,        # allow slow integration tests
        "auto_orient_switch": False,
        "description": "mission-critical, deployed, semver ≥ 1.0",
    },
    "research": {
        # Exploration tasks where "no improvement" is still data.
        # High patience, any delta counts, large convergence window.
        "patience_budget": 100,
        "discard_threshold": 20,
        "min_metric_delta_pct": 0.0,      # any movement = signal
        "convergence_window": 10,
        "guard_timeout_mult": 1.0,
        "auto_orient_switch": True,
        "description": "open-ended exploration, hypothesis testing",
    },
}


def detect_project(path="."):
    """Auto-detect project type and characteristics by checking for sentinel files."""
    path = Path(path)
    base_result = {
        "type": "generic",
        "sentinel": None,
        "syntax_check": "",
        "guard": "",
        "default_metric": "manual",
    }

    for sentinel in SENTINEL_ORDER:
        if (path / sentinel).exists():
            for rule in PROJECT_RULES:
                if rule[0] == sentinel:
                    result = {
                        "type": rule[1],
                        "sentinel": sentinel,
                        "syntax_check": rule[2],
                        "guard": rule[3],
                        "default_metric": rule[4],
                    }
                    # TypeScript needs tsconfig.json
                    if rule[1] == "typescript" and not (path / "tsconfig.json").exists():
                        continue
                    if rule[1] == "javascript" and (path / "tsconfig.json").exists():
                        continue
                    base_result = result
                    break
            break

    # Enrich with project characteristics for tier inference
    base_result.update(detect_project_characteristics(path))
    base_result["delivery_tier"] = infer_delivery_tier(path, base_result)
    base_result["profile"] = CONVERGENCE_PROFILES[base_result["delivery_tier"]]
    print(json.dumps(base_result, indent=2))


def detect_project_characteristics(path):
    """Detect signals used to infer delivery tier."""
    path = Path(path)

    # Test presence (multiple conventions)
    test_indicators = [
        "tests", "test", "__tests__", "spec", "specs",
        "src/test", "src/tests",
    ]
    test_files_patterns = ["test_*.py", "*_test.go", "*_test.dart", "*.test.ts", "*.test.js", "*.spec.ts", "*.spec.js"]
    has_tests_dir = any((path / t).is_dir() for t in test_indicators)

    # Single bounded walk: match test-file patterns by filename anywhere in
    # the tree. Skips heavy/vendored dirs; stops at first hit or 2000 files.
    SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox", ".mypy_cache"}
    MAX_TEST_SCAN_FILES = 2000
    MAX_TEST_SCAN_DEPTH = 8

    has_test_files = False
    scanned = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(root, path)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= MAX_TEST_SCAN_DEPTH:
            dirs[:] = []
        for fname in files:
            scanned += 1
            if any(fnmatch.fnmatch(fname, pat) for pat in test_files_patterns):
                has_test_files = True
                break
            if scanned >= MAX_TEST_SCAN_FILES:
                break
        if has_test_files or scanned >= MAX_TEST_SCAN_FILES:
            break

    has_tests = has_tests_dir or has_test_files

    # CI presence
    ci_paths = [
        ".github/workflows",
        ".gitlab-ci.yml",
        ".circleci",
        "azure-pipelines.yml",
        "Jenkinsfile",
        ".travis.yml",
        "bitbucket-pipelines.yml",
    ]
    has_ci = any((path / c).exists() for c in ci_paths)

    # Changelog / docs / version signals
    has_changelog = any((path / c).exists() for c in ["CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md"])
    has_docs = (path / "docs").is_dir() or (path / "doc").is_dir() or (path / "README.md").exists()

    # Version (from common manifests)
    version_major = _extract_version_major(path)

    # Code size estimate (rough: count source files)
    code_files = 0
    src_dirs = [path / "src", path / "lib", path / "app"]
    src_dirs = [d for d in src_dirs if d.exists()]
    scan_dirs = src_dirs if src_dirs else [path]
    for d in scan_dirs[:1]:  # limit to first src dir for perf
        try:
            for ext in ("*.py", "*.ts", "*.js", "*.go", "*.rs", "*.java", "*.rb"):
                code_files += sum(1 for _ in d.rglob(ext))
        except (OSError, PermissionError):
            pass
    if code_files < 10:
        code_size = "S"
    elif code_files < 50:
        code_size = "M"
    elif code_files < 200:
        code_size = "L"
    else:
        code_size = "XL"

    return {
        "has_tests": has_tests,
        "has_ci": has_ci,
        "has_changelog": has_changelog,
        "has_docs": has_docs,
        "version_major": version_major,
        "code_size": code_size,
        "code_file_count": code_files,
    }


def _extract_version_major(path):
    """Extract major version from common manifest files. Returns int or 0."""
    path = Path(path)
    # package.json
    pj = path / "package.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text())
            v = str(data.get("version", "0"))
            return int(v.split(".")[0]) if v[0].isdigit() else 0
        except (json.JSONDecodeError, ValueError, IndexError):
            pass
    # plugin.json (Claude Code plugins)
    pj2 = path / "plugin.json"
    if pj2.exists():
        try:
            data = json.loads(pj2.read_text())
            v = str(data.get("version", "0"))
            return int(v.split(".")[0]) if v[0].isdigit() else 0
        except (json.JSONDecodeError, ValueError, IndexError):
            pass
    # Cargo.toml
    cargo = path / "Cargo.toml"
    if cargo.exists():
        try:
            text = cargo.read_text()
            m = re.search(r'^version\s*=\s*"(\d+)', text, re.MULTILINE)
            if m:
                return int(m.group(1))
        except (OSError, ValueError):
            pass
    # pyproject.toml
    pyproj = path / "pyproject.toml"
    if pyproj.exists():
        try:
            text = pyproj.read_text()
            m = re.search(r'^version\s*=\s*["\'](\d+)', text, re.MULTILINE)
            if m:
                return int(m.group(1))
        except (OSError, ValueError):
            pass
    return 0


def infer_delivery_tier(path, characteristics):
    """Infer delivery tier from project characteristics.

    Heuristics (highest match wins):
    - production: tests + CI + (changelog OR version ≥ 1) + has_docs
    - research: no guard AND (no tests OR has_docs as primary artifact)
    - standard: tests OR CI
    - prototype: nothing else matches
    """
    has_tests = characteristics.get("has_tests", False)
    has_ci = characteristics.get("has_ci", False)
    has_changelog = characteristics.get("has_changelog", False)
    has_docs = characteristics.get("has_docs", False)
    version_major = characteristics.get("version_major", 0)
    guard = characteristics.get("guard", "")
    has_guard = bool(guard and "no guard" not in guard.lower())

    # Production: comprehensive signals
    if has_tests and has_ci and version_major >= 1 and (has_changelog or has_docs):
        return "production"

    # Research: open-ended (no guard + has docs as primary artifact OR explicit exploration)
    if not has_guard and not has_tests and has_docs:
        return "research"

    # Standard: some engineering discipline
    if has_tests or has_ci or has_changelog:
        return "standard"

    # Prototype: nothing else
    return "prototype"


def _detect_guard(path):
    """Return the guard command for the first matching sentinel.

    Mirrors detect_project's sentinel scan so `profile` and `detect` always
    agree on tier inference.
    """
    path = Path(path)
    for sentinel in SENTINEL_ORDER:
        if not (path / sentinel).exists():
            continue
        for rule in PROJECT_RULES:
            if rule[0] != sentinel:
                continue
            if rule[1] == "typescript" and not (path / "tsconfig.json").exists():
                continue
            if rule[1] == "javascript" and (path / "tsconfig.json").exists():
                continue
            return rule[3]
        break
    return ""


def get_profile(tier):
    """Get convergence profile for a tier. Falls back to standard."""
    return CONVERGENCE_PROFILES.get(tier, CONVERGENCE_PROFILES["standard"])


# ── JSONL Log Management ──

def init_log(args):
    """Initialize a new JSONL log with config header."""
    header = {
        "type": "config",
        "name": args.name,
        "metricName": args.metric_name,
        "metricUnit": args.metric_unit or "",
        "bestDirection": args.direction,
        "orientation": args.orientation,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    with open(args.jsonl, "w") as f:
        f.write(json.dumps(header) + "\n")
    print(f"Initialized {args.jsonl}")


def log_waypoint(args):
    """Append a waypoint result (or a pivot / remeasure marker) to the JSONL log."""
    if not args.pivot and not args.remeasure and not args.status:
        raise SystemExit("odyssey_helper.py log: error: --status is required unless --pivot or --remeasure")
    if args.pivot and (args.status or args.metric is not None or args.was is not None):
        raise SystemExit("odyssey_helper.py log: error: --pivot cannot be combined with --status/--metric/--was")
    if args.remeasure and (args.status or args.metric is None or args.was is None):
        raise SystemExit("odyssey_helper.py log: error: --remeasure requires --metric <new> --was <old>, and no --status")
    if args.pivot and args.remeasure:
        raise SystemExit("odyssey_helper.py log: error: --pivot and --remeasure are mutually exclusive")

    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    if args.pivot:
        # Goal revision: marks a mission setpoint change. Convergence
        # evidence counts only waypoints logged after the last pivot.
        entry = {
            "type": "pivot",
            "run": args.run,
            "description": args.description or "goal revised",
            "timestamp": timestamp,
        }
        with open(args.jsonl, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return

    if args.remeasure:
        # Environment-drift probe: re-measure the CURRENT BEST artifact in
        # the live environment. In adaptive (game-theoretic) settings the
        # world moves under you — diminishing returns may mean "the opponent
        # adapted", not "we are done". convergence-check uses these entries
        # to distinguish the two.
        entry = {
            "run": args.run,
            "status": "remeasure",
            "metric": args.metric,
            "previous": args.was,
            "description": args.description or "re-measured current best in live environment",
            "timestamp": timestamp,
        }
        with open(args.jsonl, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return

    entry = {
        "run": args.run,
        "commit": args.commit or "0000000",
        "status": args.status,
        "description": args.description or "",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
    }
    if args.metric is not None:
        entry["metric"] = args.metric
    if args.secondary_metrics:
        try:
            entry["secondaryMetrics"] = json.loads(args.secondary_metrics)
        except json.JSONDecodeError:
            pass
    if args.asi:
        try:
            entry["asi"] = json.loads(args.asi)
        except json.JSONDecodeError:
            entry["asi"] = {"hypothesis": args.asi}

    with open(args.jsonl, "a") as f:
        f.write(json.dumps(entry) + "\n")


def evaluate_log(args):
    """Evaluate whether a metric value is an improvement."""
    config = _read_config(args.jsonl)
    if not config:
        print("ERROR: No config header found in JSONL")
        sys.exit(1)

    direction = config.get("bestDirection", "lower")
    best = _get_best_metric(args.jsonl, direction)
    new_value = args.metric

    if best is None:
        print(json.dumps({"improved": True, "previous_best": None, "new_value": new_value, "direction": direction}))
        return

    improved = (new_value > best) if direction == "higher" else (new_value < best)
    print(json.dumps({
        "improved": improved,
        "previous_best": best,
        "new_value": new_value,
        "direction": direction,
        "delta": new_value - best,
    }))


def summary_log(args):
    """Print a summary of the JSONL log."""
    config = _read_config(args.jsonl)
    if not config:
        print("No odyssey.jsonl found or missing config header")
        return

    entries = _read_entries(args.jsonl)
    keeps = [e for e in entries if e.get("status") == "keep"]
    discards = [e for e in entries if e.get("status") == "discard"]
    baseline = entries[0] if entries else None

    direction = config.get("bestDirection", "lower")
    best = _get_best_metric(args.jsonl, direction)

    print(f"Mission: {config.get('name', 'unknown')}")
    print(f"Orientation: {config.get('orientation', 'unknown')}")
    print(f"Total waypoints: {len(entries)}")
    print(f"  Kept: {len(keeps)}")
    print(f"  Discarded: {len(discards)}")
    if best is not None and baseline and "metric" in baseline:
        baseline_val = baseline["metric"]
        delta = best - baseline_val
        pct = (delta / abs(baseline_val) * 100) if baseline_val != 0 else 0
        print(f"Best {config.get('metricName', 'metric')}: {best} (baseline: {baseline_val}, delta: {delta:+.4f}, {pct:+.1f}%)")
    print(f"\nLast 5 waypoints:")
    for e in entries[-5:]:
        metric_str = f" | metric: {e.get('metric', 'N/A')}" if "metric" in e else ""
        print(f"  Run {e.get('run', '?')}: {e.get('status', '?')} — {e.get('description', '')}{metric_str}")


def status_log(args):
    """Print current status for the stop hook."""
    summary_log(args)


# ── Composite Scoring (quality gates, autodev-style) ──

DEFAULT_WEIGHTS = {"l1": 0.30, "l2": 0.25, "l3": 0.25, "l4": 0.20}


def cmd_score(args):
    """Score a waypoint across weighted quality-gate layers.

    L1 build+tests, L2 structured review, L3 security+performance,
    L4 regression — each 0-10. Encodes the simplicity criterion:
    equal composite + fewer lines = simplification win (keep);
    equal composite + more lines = discard.
    """
    if args.hard_fail:
        print(json.dumps({
            "composite": 0.0,
            "verdict": "hard-fail",
            "reason": "build failed — hard gate, discard regardless of other layers",
            "weights": DEFAULT_WEIGHTS,
        }))
        return

    layers = {"l1": args.l1, "l2": args.l2, "l3": args.l3, "l4": args.l4}
    for name, value in layers.items():
        if not 0.0 <= value <= 10.0:
            raise SystemExit(f"odyssey_helper.py score: error: --{name} must be within 0-10 (got {value})")

    weights = dict(DEFAULT_WEIGHTS)
    if args.weights:
        try:
            parts = [float(w) for w in args.weights.split(",")]
            if len(parts) != 4 or abs(sum(parts) - 1.0) > 0.001:
                raise ValueError
            weights = dict(zip(("l1", "l2", "l3", "l4"), parts))
        except ValueError:
            raise SystemExit('odyssey_helper.py score: error: --weights expects 4 comma-separated floats summing to 1.0')

    # Test-count incentives (autodev parity): added tests earn a bonus in
    # L1 and L4; removed tests penalize L1. Floors and caps at [0, 10].
    if args.tests_added:
        layers["l1"] = min(10.0, layers["l1"] + 1.0)
        layers["l4"] = min(10.0, layers["l4"] + 1.0)
    if args.tests_removed:
        layers["l1"] = max(0.0, layers["l1"] - 1.0 * args.tests_removed)
    layers = {k: round(v, 2) for k, v in layers.items()}

    composite = round(sum(layers[k] * weights[k] for k in layers), 2)
    baseline = round(args.baseline, 2)

    if composite > baseline:
        verdict, reason = "keep", f"composite {composite} > baseline {baseline}"
    elif composite < baseline:
        verdict, reason = "discard", f"composite {composite} < baseline {baseline}"
    elif args.lines < 0:
        verdict, reason = "keep", f"composite equal at {composite} with {args.lines} lines — simplification win"
    else:
        verdict, reason = "discard", f"composite equal at {composite} with {args.lines:+d} lines — complexity without gain"

    print(json.dumps({
        "composite": composite,
        "verdict": verdict,
        "reason": reason,
        "weights": weights,
        "layers": layers,
        "lines_delta": args.lines,
    }))


# ── Mission Grammar Validation ──
# MISSION.md IS a language — constrained natural language, parsed
# mechanically. `validate` is its grammar checker: no new syntax, just
# the difference between a language and a prayer.

REQUIRED_SECTIONS = ["Goal", "Metrics", "Guard", "Termination",
                     "What's Been Tried", "Ideas Backlog"]


def cmd_validate(args):
    """Mechanically check a MISSION.md against the mission grammar."""
    errors, warnings = [], []
    path = Path(args.mission)
    if not path.exists():
        print(json.dumps({"valid": False, "errors": [f"file not found: {path}"], "warnings": []}))
        return
    text = path.read_text(encoding="utf-8")

    if not text.lstrip().startswith("---"):
        errors.append("missing frontmatter (must start with ---)")
        fm = ""
    else:
        fm = text.split("---", 2)[1]
        for key in ("orientation", "status", "started_at"):
            if not re.search(rf"^{key}:", fm, flags=re.M):
                errors.append(f"frontmatter missing: {key}")

    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^## {re.escape(section)}", text, flags=re.M):
            errors.append(f"missing section: ## {section}")

    if re.search(r"^## Metrics", text, flags=re.M) and not re.search(r"^## Metrics\n[^|]*\|", text, flags=re.M):
        warnings.append("Metrics section has no table rows (| ... |)")

    guard_ok = re.search(r"^## Guard\s*\n+```", text, flags=re.M)
    if not guard_ok:
        errors.append("Guard section needs a ```bash fenced command block")

    if re.search(r"^field:\s*strategy", fm, flags=re.M):
        if "## Board" not in text:
            warnings.append("strategy field: Board section absent (compass needs it)")
    if "skeptic" in text.lower() and "## Arsenal" not in text:
        warnings.append("Arsenal section absent — mission cannot activate capabilities")

    print(json.dumps({
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "sections": len(re.findall(r"^## ", text, flags=re.M)),
    }, indent=2))


# ── Helpers ──

def _read_config(jsonl_path):
    """Read the config header from a JSONL file."""
    try:
        with open(jsonl_path) as f:
            first_line = f.readline().strip()
            entry = json.loads(first_line)
            if entry.get("type") == "config":
                return entry
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def _read_entries(jsonl_path):
    """Read all waypoint entries from a JSONL file."""
    entries = []
    try:
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") != "config":
                        entries.append(entry)
                except json.JSONDecodeError:
                    pass
    except FileNotFoundError:
        pass
    return entries


def _get_best_metric(jsonl_path, direction="lower"):
    """Get the best metric value from kept waypoints."""
    entries = _read_entries(jsonl_path)
    metrics = [e["metric"] for e in entries if e.get("status") == "keep" and "metric" in e]
    if not metrics:
        return None
    return max(metrics) if direction == "higher" else min(metrics)


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Odyssey Engine Helper")
    sub = parser.add_subparsers(dest="command")

    # detect
    p_detect = sub.add_parser("detect", help="Auto-detect project type, characteristics, and delivery tier")
    p_detect.add_argument("--path", default=".", help="Directory to scan")

    # profile
    p_profile = sub.add_parser("profile", help="Print convergence profile for a tier (or infer from path)")
    p_profile.add_argument("--tier", choices=list(CONVERGENCE_PROFILES.keys()), help="Explicit tier (default: auto-infer)")
    p_profile.add_argument("--path", default=".", help="Directory to scan if tier not specified")
    p_profile.add_argument("--json", action="store_true", help="Output as JSON (default: human-readable)")

    # init
    p_init = sub.add_parser("init", help="Initialize JSONL log")
    p_init.add_argument("--jsonl", required=True, help="JSONL file path")
    p_init.add_argument("--name", required=True, help="Mission name")
    p_init.add_argument("--metric-name", default="metric", help="Metric name")
    p_init.add_argument("--metric-unit", default="", help="Metric unit")
    p_init.add_argument("--direction", default="lower", choices=["lower", "higher"], help="Best direction")
    p_init.add_argument("--orientation", default="engineer", help="Orientation")
    p_init.add_argument("--delivery-tier", default=None, choices=list(CONVERGENCE_PROFILES.keys()), help="Delivery tier (default: auto-infer)")

    # log
    p_log = sub.add_parser("log", help="Log a waypoint result")
    p_log.add_argument("--jsonl", required=True, help="JSONL file path")
    p_log.add_argument("--run", type=int, required=True, help="Waypoint number")
    p_log.add_argument("--commit", default=None, help="Git commit SHA")
    p_log.add_argument("--metric", type=float, default=None, help="Metric value")
    p_log.add_argument("--status", default=None, choices=["keep", "discard", "crash"], help="Result status (required unless --pivot or --remeasure)")
    p_log.add_argument("--description", default="", help="What was tried")
    p_log.add_argument("--secondary-metrics", default=None, help="JSON string of secondary metrics")
    p_log.add_argument("--asi", default=None, help="JSON string or plain text for ASI data")
    p_log.add_argument("--pivot", action="store_true", help="Log a goal revision instead of a waypoint result")
    p_log.add_argument("--remeasure", action="store_true", help="Log a re-measurement of the current best (environment-drift probe)")
    p_log.add_argument("--was", type=float, default=None, help="With --remeasure: the previously recorded best value")

    # evaluate
    p_eval = sub.add_parser("evaluate", help="Evaluate if a metric is an improvement")
    p_eval.add_argument("--jsonl", required=True, help="JSONL file path")
    p_eval.add_argument("--metric", type=float, required=True, help="New metric value")

    # convergence-check (NEW)
    p_conv = sub.add_parser("convergence-check", help="Check if mission has converged based on recent waypoints")
    p_conv.add_argument("--jsonl", required=True, help="JSONL file path")
    p_conv.add_argument("--tier", default="standard", choices=list(CONVERGENCE_PROFILES.keys()), help="Delivery tier (determines thresholds)")

    # reset-discards (NEW)
    p_reset = sub.add_parser("reset-discards", help="Reset consecutive_discards counter in state file")
    p_reset.add_argument("--state-file", default=".claude/odyssey.local.md", help="Path to state file")

    # summary
    p_summary = sub.add_parser("summary", help="Print mission summary")
    p_summary.add_argument("--jsonl", required=True, help="JSONL file path")

    # status
    p_status = sub.add_parser("status", help="Print current status")
    p_status.add_argument("--jsonl", required=True, help="JSONL file path")

    # validate (mission grammar)
    p_val = sub.add_parser("validate", help="Mechanically check MISSION.md against the mission grammar")
    p_val.add_argument("--mission", default="MISSION.md", help="Path to MISSION.md")

    # score (composite quality gates)
    p_score = sub.add_parser("score", help="Composite quality-gate score + keep/discard verdict")
    p_score.add_argument("--l1", type=float, required=True, help="L1 build+tests 0-10")
    p_score.add_argument("--l2", type=float, required=True, help="L2 structured review 0-10")
    p_score.add_argument("--l3", type=float, required=True, help="L3 security+performance 0-10")
    p_score.add_argument("--l4", type=float, required=True, help="L4 regression 0-10")
    p_score.add_argument("--lines", type=int, required=True, help="Net line delta of the change")
    p_score.add_argument("--baseline", type=float, required=True, help="Previous best composite")
    p_score.add_argument("--tests-added", type=int, default=0, help="Test files added this waypoint (L1/L4 bonus)")
    p_score.add_argument("--tests-removed", type=int, default=0, help="Test files removed this waypoint (L1 penalty)")
    p_score.add_argument("--weights", default=None, help='Comma weights l1,l2,l3,l4 summing to 1.0 (default 0.30,0.25,0.25,0.20)')
    p_score.add_argument("--hard-fail", action="store_true", help="Build failed — hard gate overrides everything")

    args = parser.parse_args()
    if args.command == "detect":
        detect_project(args.path)
    elif args.command == "profile":
        cmd_profile(args)
    elif args.command == "init":
        init_log(args)
    elif args.command == "log":
        log_waypoint(args)
    elif args.command == "evaluate":
        evaluate_log(args)
    elif args.command == "convergence-check":
        cmd_convergence_check(args)
    elif args.command == "reset-discards":
        cmd_reset_discards(args)
    elif args.command == "summary":
        summary_log(args)
    elif args.command == "status":
        status_log(args)
    elif args.command == "score":
        cmd_score(args)
    elif args.command == "validate":
        cmd_validate(args)
    else:
        parser.print_help()


# ── Profile Command ──

def cmd_profile(args):
    """Print or return convergence profile."""
    if args.tier:
        tier = args.tier
    else:
        # Infer from path
        path = Path(args.path)
        chars = detect_project_characteristics(path)
        chars_full = {**chars, "guard": _detect_guard(path)}
        tier = infer_delivery_tier(path, chars_full)

    profile = get_profile(tier)
    output = {"tier": tier, **profile}

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"Tier: {tier}")
        print(f"Description: {profile['description']}")
        print(f"Patience budget: {profile['patience_budget']} waypoints")
        print(f"Discard threshold: {profile['discard_threshold']} consecutive")
        print(f"Min metric delta: {profile['min_metric_delta_pct']}%")
        print(f"Convergence window: {profile['convergence_window']} waypoints")
        print(f"Guard timeout multiplier: {profile['guard_timeout_mult']}x")
        print(f"Auto orientation switch: {profile['auto_orient_switch']}")


# ── Convergence Check Command ──

def cmd_convergence_check(args):
    """Check if mission has converged based on recent waypoints."""
    profile = get_profile(args.tier)
    window = profile["convergence_window"]
    min_delta = profile["min_metric_delta_pct"]

    entries = _read_entries(args.jsonl)

    # Non-stationary missions: a pivot entry marks a goal revision.
    # Evidence counts only waypoints logged after the last pivot —
    # pre-pivot measurements say nothing about the current objective.
    pivot_idx = [i for i, e in enumerate(entries) if e.get("type") == "pivot"]
    pivots = len(pivot_idx)
    if pivot_idx:
        entries = entries[pivot_idx[-1] + 1:]

    # Remeasures are drift probes, not waypoints: they neither consume
    # patience nor count toward trailing discards. They feed the
    # environment-drift check below.
    remeasures = [e for e in entries if e.get("status") == "remeasure" and "metric" in e and "previous" in e]
    entries = [e for e in entries if e.get("status") != "remeasure"]

    keeps = [e for e in entries if e.get("status") == "keep" and "metric" in e]

    result = {
        "converged": False,
        "reason": "",
        "evidence": [],
        "tier": args.tier,
        "window": window,
        "pivots": pivots,
        "stale": False,
    }

    # Churn: consecutive crashes at the tail. Evaluated BEFORE the
    # insufficient-data window check — a crash streak is the loop melting
    # down regardless of how many keeps exist. The single sanctioned stop
    # besides convergence: endlessly retrying the same failure is worse
    # than reporting back to the human.
    CHURN_LIMIT = 5
    trailing_crashes = 0
    for e in reversed(entries):
        if e.get("status") == "crash":
            trailing_crashes += 1
        else:
            break
    churn = trailing_crashes >= CHURN_LIMIT
    result["evidence"].append({
        "check": "churn",
        "count": trailing_crashes,
        "threshold": CHURN_LIMIT,
        "passed": churn,
    })

    # Not enough data yet
    if len(kills_check := keeps) < window:
        if churn:
            result["converged"] = True
            result["reason"] = (
                f"churn: {trailing_crashes} consecutive crashes (limit {CHURN_LIMIT}) — "
                f"stop and report to the human; do not retry the same approach"
            )
            print(json.dumps(result, indent=2))
            return
        result["reason"] = f"insufficient data ({len(kills_check)}/{window} keeps needed)"
        if pivots:
            result["reason"] += f" since last of {pivots} pivot(s)"
        print(json.dumps(result, indent=2))
        return

    recent = keeps[-window:]
    metrics = [e["metric"] for e in recent]

    # Check 1: diminishing returns
    # Compute relative deltas between consecutive keeps
    deltas = []
    for i in range(1, len(metrics)):
        prev = metrics[i - 1]
        curr = metrics[i]
        if prev == 0:
            rel = abs(curr) * 100  # treat as % of 1
        else:
            rel = abs(curr - prev) / abs(prev) * 100
        deltas.append(rel)

    avg_delta = sum(deltas) / len(deltas) if deltas else 0
    result["evidence"].append({
        "check": "diminishing_returns",
        "avg_delta_pct": round(avg_delta, 4),
        "threshold_pct": min_delta,
        "passed": avg_delta < min_delta,
    })

    # Check 2: patience budget exhausted
    total_waypoints = len(entries)
    result["evidence"].append({
        "check": "patience_budget",
        "used": total_waypoints,
        "budget": profile["patience_budget"],
        "passed": total_waypoints >= profile["patience_budget"],
    })

    # Check 3: consecutive discards (from raw entries, trailing)
    trailing_discards = 0
    for e in reversed(entries):
        if e.get("status") == "discard":
            trailing_discards += 1
        else:
            break
    result["evidence"].append({
        "check": "trailing_discards",
        "count": trailing_discards,
        "threshold": profile["discard_threshold"],
        "passed": trailing_discards >= profile["discard_threshold"],
    })

    # Converged if diminishing returns hit OR patience exhausted
    # (indices into result["evidence"]: 0 diminishing, 1 patience,
    # 2 trailing_discards, 3 churn, then optional environment_drift)
    diminishing = result["evidence"][0]["passed"]
    exhausted = result["evidence"][1]["passed"]
    stuck = result["evidence"][2]["passed"]

    # Environment drift: the latest probe re-measured the current best in
    # the live world. A significant degradation means the environment moved
    # (the opponent adapted, the audience fatigued, the market shifted) —
    # diminishing returns then means "they learned our pattern", NOT "done".
    drift = False
    if remeasures:
        latest = remeasures[-1]
        sig = max(min_delta * 10.0, 1.0) / 100.0  # significance band: 10x min delta, >=1%
        new_v, old_v = latest["metric"], latest["previous"]
        direction = "lower"  # resolved from config below if available
        config = _read_config(args.jsonl)
        if config:
            direction = config.get("bestDirection", "lower")
        if direction == "lower":
            drift = new_v > old_v * (1 + sig)
        else:
            drift = new_v < old_v * (1 - sig)
        result["evidence"].append({
            "check": "environment_drift",
            "remeasured": new_v,
            "previous_best": old_v,
            "significance_pct": round(sig * 100, 3),
            "passed": drift,
        })

    if churn:
        result["converged"] = True
        result["reason"] = (
            f"churn: {trailing_crashes} consecutive crashes (limit {CHURN_LIMIT}) — "
            f"stop and report to the human; do not retry the same approach"
        )
    elif drift:
        result["converged"] = False
        result["stale"] = True
        result["reason"] = (
            f"environment drift: current best re-measured at {new_v} vs recorded {old_v} "
            f"(>{round(sig * 100, 3)}% degradation) — the world moved under the mission; "
            f"re-baseline and reconsider before trusting diminishing returns"
        )
    elif diminishing:
        result["converged"] = True
        result["reason"] = f"diminishing returns: avg delta {avg_delta:.3f}% < threshold {min_delta}% over last {window} keeps"
    elif exhausted:
        result["converged"] = True
        result["reason"] = f"patience budget exhausted: {total_waypoints}/{profile['patience_budget']} waypoints used"
    elif stuck:
        result["converged"] = False  # stuck ≠ converged; needs orientation switch
        result["reason"] = f"stuck: {trailing_discards} consecutive discards (threshold {profile['discard_threshold']})"
    else:
        result["reason"] = f"continuing: avg delta {avg_delta:.3f}%, {total_waypoints}/{profile['patience_budget']} waypoints"

    print(json.dumps(result, indent=2))


# ── Reset Discards Command ──

def cmd_reset_discards(args):
    """Reset consecutive_discards counter in state file."""
    state_path = Path(args.state_file)
    if not state_path.exists():
        print(json.dumps({"ok": False, "error": f"state file not found: {state_path}"}))
        return

    text = state_path.read_text()
    new_text = re.sub(
        r'^consecutive_discards:.*$',
        'consecutive_discards: 0',
        text,
        flags=re.MULTILINE,
    )
    state_path.write_text(new_text)
    print(json.dumps({"ok": True, "reset_to": 0, "file": str(state_path)}))


if __name__ == "__main__":
    main()
