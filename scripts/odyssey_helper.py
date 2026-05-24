#!/usr/bin/env python3
"""Odyssey Engine Helper CLI.

Manages JSONL experiment logs, project auto-detection, and state evaluation.
Forked from autoresearch_helper.py with additions for odyssey-engine.
Uses stdlib only — no external dependencies.
"""

import argparse
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


def detect_project(path="."):
    """Auto-detect project type by checking for sentinel files."""
    path = Path(path)
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
                    print(json.dumps(result, indent=2))
                    return
    print(json.dumps({"type": "generic", "sentinel": None, "syntax_check": "", "guard": "", "default_metric": "manual"}))


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
    """Append a waypoint result to the JSONL log."""
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
    p_detect = sub.add_parser("detect", help="Auto-detect project type")
    p_detect.add_argument("--path", default=".", help="Directory to scan")

    # init
    p_init = sub.add_parser("init", help="Initialize JSONL log")
    p_init.add_argument("--jsonl", required=True, help="JSONL file path")
    p_init.add_argument("--name", required=True, help="Mission name")
    p_init.add_argument("--metric-name", default="metric", help="Metric name")
    p_init.add_argument("--metric-unit", default="", help="Metric unit")
    p_init.add_argument("--direction", default="lower", choices=["lower", "higher"], help="Best direction")
    p_init.add_argument("--orientation", default="engineer", help="Orientation")

    # log
    p_log = sub.add_parser("log", help="Log a waypoint result")
    p_log.add_argument("--jsonl", required=True, help="JSONL file path")
    p_log.add_argument("--run", type=int, required=True, help="Waypoint number")
    p_log.add_argument("--commit", default=None, help="Git commit SHA")
    p_log.add_argument("--metric", type=float, default=None, help="Metric value")
    p_log.add_argument("--status", required=True, choices=["keep", "discard"], help="Result status")
    p_log.add_argument("--description", default="", help="What was tried")
    p_log.add_argument("--secondary-metrics", default=None, help="JSON string of secondary metrics")
    p_log.add_argument("--asi", default=None, help="JSON string or plain text for ASI data")

    # evaluate
    p_eval = sub.add_parser("evaluate", help="Evaluate if a metric is an improvement")
    p_eval.add_argument("--jsonl", required=True, help="JSONL file path")
    p_eval.add_argument("--metric", type=float, required=True, help="New metric value")

    # summary
    p_summary = sub.add_parser("summary", help="Print mission summary")
    p_summary.add_argument("--jsonl", required=True, help="JSONL file path")

    # status
    p_status = sub.add_parser("status", help="Print current status")
    p_status.add_argument("--jsonl", required=True, help="JSONL file path")

    args = parser.parse_args()
    if args.command == "detect":
        detect_project(args.path)
    elif args.command == "init":
        init_log(args)
    elif args.command == "log":
        log_waypoint(args)
    elif args.command == "evaluate":
        evaluate_log(args)
    elif args.command == "summary":
        summary_log(args)
    elif args.command == "status":
        status_log(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
