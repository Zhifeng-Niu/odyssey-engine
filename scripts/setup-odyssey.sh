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
EXPLICIT_TIER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --orientation)   ORIENTATION="$2"; shift 2 ;;
    --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
    --time-budget)   TIME_BUDGET="$2"; shift 2 ;;
    --completion-promise) COMPLETION_PROMISE="$2"; shift 2 ;;
    --mission-file)  MISSION_FILE="$2"; shift 2 ;;
    --tier)          EXPLICIT_TIER="$2"; shift 2 ;;
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

project_info=$(python3 "$HELPER" detect --path "." 2>/dev/null || echo '{"type":"generic","delivery_tier":"standard","profile":{}}')
project_type=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type','generic'))" 2>/dev/null || echo "generic")
syntax_check=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('syntax_check',''))" 2>/dev/null || echo "")
guard_cmd=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('guard',''))" 2>/dev/null || echo "")
default_metric=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('default_metric','manual'))" 2>/dev/null || echo "manual")
delivery_tier=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('delivery_tier','standard'))" 2>/dev/null || echo "standard")
patience_budget=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('profile',{}).get('patience_budget',30))" 2>/dev/null || echo "30")
discard_threshold=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('profile',{}).get('discard_threshold',10))" 2>/dev/null || echo "10")
min_metric_delta=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('profile',{}).get('min_metric_delta_pct',0.5))" 2>/dev/null || echo "0.5")
convergence_window=$(echo "$project_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('profile',{}).get('convergence_window',5))" 2>/dev/null || echo "5")
auto_orient_switch=$(echo "$project_info" | python3 -c "import sys,json; print(str(json.load(sys.stdin).get('profile',{}).get('auto_orient_switch',True)).lower())" 2>/dev/null || echo "true")

# Allow explicit override via flag
if [[ -n "${EXPLICIT_TIER:-}" ]]; then
  delivery_tier="$EXPLICIT_TIER"
  profile_info=$(python3 "$HELPER" profile --tier "$delivery_tier" --json 2>/dev/null || echo "{}")
  patience_budget=$(echo "$profile_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('patience_budget',30))" 2>/dev/null || echo "30")
  discard_threshold=$(echo "$profile_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('discard_threshold',10))" 2>/dev/null || echo "10")
  min_metric_delta=$(echo "$profile_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('min_metric_delta_pct',0.5))" 2>/dev/null || echo "0.5")
  convergence_window=$(echo "$profile_info" | python3 -c "import sys,json; print(json.load(sys.stdin).get('convergence_window',5))" 2>/dev/null || echo "5")
  auto_orient_switch=$(echo "$profile_info" | python3 -c "import sys,json; print(str(json.load(sys.stdin).get('auto_orient_switch',True)).lower())" 2>/dev/null || echo "true")
fi

echo "Detected project type: $project_type"
echo "Delivery tier: $delivery_tier (patience=$patience_budget, discard_limit=$discard_threshold, min_delta=${min_metric_delta}%)"

# ── Create MISSION.md ──

if [[ -n "$MISSION_FILE" && -f "$MISSION_FILE" ]]; then
  cp "$MISSION_FILE" "MISSION.md"
else
  # Generate from template
  mission_title=$(echo "$PROMPT" | head -c 80)
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  guard_desc="${guard_cmd:-none}"
  guard_inline="${guard_cmd:-echo \"no guard defined\"}"

  TEMPLATE_PATH="$SCRIPT_DIR/../templates/MISSION.md.template"
  if [[ -f "$TEMPLATE_PATH" ]]; then
    # Use template with token substitution (single source of truth)
    sed \
      -e "s|{{ORIENTATION}}|${ORIENTATION}|g" \
      -e "s|{{NOW}}|${now}|g" \
      -e "s|{{TITLE}}|${mission_title}|g" \
      -e "s|{{PROMPT}}|${PROMPT}|g" \
      -e "s|{{PROJECT_TYPE}}|${project_type}|g" \
      -e "s|{{GUARD_DESC}}|${guard_desc}|g" \
      -e "s|{{GUARD_CMD}}|${guard_inline}|g" \
      -e "s|{{DEFAULT_METRIC}}|${default_metric}|g" \
      "$TEMPLATE_PATH" > "MISSION.md"
  else
    # Fallback: inline heredoc (kept for resilience if template removed)
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
delivery_tier: ${delivery_tier}
patience_budget: ${patience_budget}
discard_threshold: ${discard_threshold}
min_metric_delta_pct: ${min_metric_delta}
convergence_window: ${convergence_window}
auto_orient_switch: ${auto_orient_switch}
---

# Odyssey Mission Active

Orientation: ${ORIENTATION}
Delivery tier: ${delivery_tier} (patience=${patience_budget}, discard_limit=${discard_threshold}, min_delta=${min_metric_delta}%)
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
  Tier:         ${delivery_tier} (patience ${patience_budget}, discard_limit ${discard_threshold}, min_delta ${min_metric_delta}%)
  Branch:       ${branch_name:-N/A}
  Max runs:     unlimited (until done or /odyssey-cancel)
  Time budget:  ${TIME_BUDGET:-none}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The stop hook is active. The loop will continue autonomously.
Use /odyssey-status to check progress.
Use /odyssey-cancel to stop.
SUMMARY
