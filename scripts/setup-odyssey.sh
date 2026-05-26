#!/usr/bin/env bash
# Odyssey Engine Setup Script
# Initializes mission state, detects project type, creates MISSION.md and expedition branch.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER="$SCRIPT_DIR/odyssey_helper.py"
STATE_FILE=".claude/odyssey.local.md"

# ── Argument Parsing ──

PROMPT=""
ORIENTATION="engineer"
MAX_ITERATIONS=0  # 0 = unlimited, like ralph-loop
TIME_BUDGET=""
COMPLETION_PROMISE=""
MISSION_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --orientation)   ORIENTATION="$2"; shift 2 ;;
    --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
    --time-budget)   TIME_BUDGET="$2"; shift 2 ;;
    --completion-promise) COMPLETION_PROMISE="$2"; shift 2 ;;
    --mission-file)  MISSION_FILE="$2"; shift 2 ;;
    --resume)        echo "Resuming existing mission..."; exit 0 ;;
    *)               PROMPT="$1"; shift ;;
  esac
done

# ── Pre-flight Checks ──

if [[ -f "$STATE_FILE" ]]; then
  echo "ERROR: Odyssey already active. Use /odyssey-cancel first or /odyssey --resume."
  exit 1
fi

if [[ -z "$PROMPT" && -z "$MISSION_FILE" ]]; then
  echo "ERROR: Provide a PROMPT or --mission-file PATH"
  exit 1
fi

if [[ ! -d ".git" ]]; then
  echo "WARNING: Not a git repo. Git-based checkpointing will not work."
fi

# ── Parse Time Budget ──

time_seconds=0
if [[ -n "$TIME_BUDGET" ]]; then
  if [[ "$TIME_BUDGET" == *"h" ]]; then
    time_seconds=$(( $(echo "$TIME_BUDGET" | tr -d 'h') * 3600 ))
  elif [[ "$TIME_BUDGET" == *"m" ]]; then
    time_seconds=$(( $(echo "$TIME_BUDGET" | tr -d 'm') * 60 ))
  else
    time_seconds="$TIME_BUDGET"
  fi
fi

# ── Project Auto-Detection ──

project_info=$(python3 "$HELPER" detect --path "." 2>/dev/null || echo '{"type":"generic"}')
project_type=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type','generic'))" 2>/dev/null || echo "generic")
syntax_check=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('syntax_check',''))" 2>/dev/null || echo "")
guard_cmd=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('guard',''))" 2>/dev/null || echo "")
default_metric=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('default_metric','manual'))" 2>/dev/null || echo "manual")

echo "Detected project type: $project_type"

# ── Create MISSION.md ──

if [[ -n "$MISSION_FILE" && -f "$MISSION_FILE" ]]; then
  cp "$MISSION_FILE" "MISSION.md"
else
  # Generate from prompt
  mission_title=$(echo "$PROMPT" | head -c 80)
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  cat > "MISSION.md" <<MISSIONEOF
---
orientation: [${ORIENTATION}]
status: active
started_at: ${now}
expedition_branch: null
baseline_metric: null
best_metric: null
total_waypoints: 0
consecutive_discards: 0
---

# Mission: ${mission_title}

## Goal
${PROMPT}

## Context
Project type: ${project_type}. Auto-detected guard: ${guard_cmd:-none}.

## Scope

### Modifiable
- (auto — all files not in Read-Only)

### Read-Only (PROTECTED)
- (none specified)

## Metrics

| Name | Unit | Measure Command | Direction |
|------|------|----------------|-----------|
| ${default_metric} | - | (auto-detected) | lower |

## Guard
\`\`\`bash
${guard_cmd:-echo "no guard defined"}
\`\`\`

## Termination
- Task complete (all checks pass AND metric improved)
- OR stuck (10 consecutive discards)
- OR user interrupt (/odyssey-cancel)
- No iteration limit — runs until done

## What's Been Tried

### Wins
{Auto-updated by engine.}

### Dead Ends
{Auto-updated by engine.}

### Surprises
{Unexpected findings. Auto-updated in creative mode.}

## Current Best
- metric: (baseline not yet measured)
- Baseline: (pending)

## Ideas Backlog
{Auto-populated. Can be manually edited.}
MISSIONEOF
fi

echo "Created MISSION.md"

# ── Create Expedition Branch (git only) ──

branch_name="odyssey/$(date +%Y%m%d-%H%M%S)"
if [[ -d ".git" ]]; then
  git checkout -b "$branch_name" 2>/dev/null || true
  # Update MISSION.md frontmatter with branch name
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s|^expedition_branch:.*|expedition_branch: ${branch_name}|" "MISSION.md"
  else
    sed -i "s|^expedition_branch:.*|expedition_branch: ${branch_name}|" "MISSION.md"
  fi
  echo "Created expedition branch: $branch_name"
else
  echo "Skipping branch creation (not a git repo)."
fi

# ── Initialize JSONL ──

python3 "$HELPER" init \
  --jsonl "odyssey.jsonl" \
  --name "${branch_name#odyssey/}" \
  --direction "lower" \
  --orientation "$ORIENTATION"

# ── Create State File ──

mkdir -p .claude
session_id=$(python3 -c "import uuid; print(uuid.uuid4().hex[:12])")
now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$STATE_FILE" <<STATEEOF
---
active: true
iteration: 0
session_id: ${session_id}
max_iterations: ${MAX_ITERATIONS}
time_budget_seconds: ${time_seconds}
completion_promise: "${COMPLETION_PROMISE}"
orientation: ${ORIENTATION}
started_at: ${now}
mission_file: MISSION.md
consecutive_discards: 0
---

# Odyssey Mission Active

Orientation: ${ORIENTATION}
Max iterations: ${MAX_ITERATIONS:-unlimited}
Time budget: ${TIME_BUDGET:-none}
Project type: ${project_type}

## Mission Prompt

$(cat MISSION.md)
STATEEOF

# ── Commit State Files ──

if [[ -d ".git" ]]; then
  git add MISSION.md odyssey.jsonl "$STATE_FILE" 2>/dev/null || true
  git commit -m "odyssey: init mission — $mission_title" --no-verify 2>/dev/null || true
fi

# ── Summary ──

cat <<SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ODYSSEY ENGINE — Mission Initialized
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Goal:         ${PROMPT}
  Orientation:  ${ORIENTATION}
  Project:      ${project_type}
  Branch:       ${branch_name:-N/A}
  Max runs:     unlimited (until done or /odyssey-cancel)
  Time budget:  ${TIME_BUDGET:-none}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The stop hook is active. The loop will continue autonomously.
Use /odyssey-status to check progress.
Use /odyssey-cancel to stop.
SUMMARY
