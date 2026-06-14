#!/usr/bin/env bash
# Odyssey Engine Stop Hook
# Prevents the agent from exiting mid-mission. Runs until:
# - Convergence detected (agent says task is done in systemMessage)
# - Stuck (10 consecutive discards)
# - Time budget exceeded (optional)
# - Completion promise fulfilled (optional)
# - User runs /odyssey-cancel
# No iteration limit — like ralph-loop, it runs until the work is done.
set -euo pipefail

# Fallback for CLAUDE_PLUGIN_ROOT when running outside Claude Code
# (e.g. debugging, manual invocation). Claude Code injects this normally.
if [[ -z "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  CLAUDE_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
export CLAUDE_PLUGIN_ROOT

STATE_FILE=".claude/odyssey.local.md"

# No state file → no active mission → allow exit
if [[ ! -f "$STATE_FILE" ]]; then
  exit 0
fi

# Parse frontmatter values
get_fm_value() {
  grep "^$1:" "$STATE_FILE" 2>/dev/null | head -1 | sed "s/^$1: *//" | tr -d '"' | tr -d "'" || true
}

active=$(get_fm_value "active")
if [[ "$active" != "true" ]]; then
  exit 0
fi

iteration=$(get_fm_value "iteration" || echo "0")
session_id=$(get_fm_value "session_id")
completion_promise=$(get_fm_value "completion_promise")
orientation=$(get_fm_value "orientation" || echo "engineer")
started_at=$(get_fm_value "started_at")
time_budget_seconds=$(get_fm_value "time_budget_seconds" || echo "0")
consecutive_discards=$(get_fm_value "consecutive_discards" || echo "0")
mission_file=$(get_fm_value "mission_file" || echo "MISSION.md")
# Profile-driven convergence parameters (with backward-compatible defaults)
delivery_tier=$(get_fm_value "delivery_tier" || echo "standard")
patience_budget=$(get_fm_value "patience_budget" || echo "30")
discard_threshold=$(get_fm_value "discard_threshold" || echo "10")
min_metric_delta_pct=$(get_fm_value "min_metric_delta_pct" || echo "0.5")
convergence_window=$(get_fm_value "convergence_window" || echo "5")
auto_orient_switch=$(get_fm_value "auto_orient_switch" || echo "true")

# Validate numeric fields
iteration=${iteration:-0}
consecutive_discards=${consecutive_discards:-0}
patience_budget=${patience_budget:-30}
discard_threshold=${discard_threshold:-10}

# Helper: deactivate mission and allow exit
deactivate() {
  local reason="$1"
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' 's/^active:.*/active: false/' "$STATE_FILE"
    sed -i '' 's/^completed_at:.*/completed_at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'/' "$STATE_FILE"
  else
    sed -i 's/^active:.*/active: false/' "$STATE_FILE"
    sed -i 's/^completed_at:.*/completed_at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'/' "$STATE_FILE"
  fi
  echo '{"decision":"allow","reason":"'"$reason"'"}'
  exit 0
}

# Check time budget (optional)
if [[ "$time_budget_seconds" -gt 0 ]] && [[ -n "$started_at" ]]; then
  started_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$started_at" "+%s" 2>/dev/null || date -d "$started_at" "+%s" 2>/dev/null || echo "0")
  if [[ "$started_epoch" -gt 0 ]]; then
    now_epoch=$(date "+%s")
    elapsed=$((now_epoch - started_epoch))
    if [[ "$elapsed" -ge "$time_budget_seconds" ]]; then
      deactivate "time budget exceeded (${elapsed}s/${time_budget_seconds}s)"
    fi
  fi
fi

# Check completion promise in stdin (last assistant message)
if [[ -n "$completion_promise" ]]; then
  stdin_data=""
  if [[ ! -t 0 ]]; then
    stdin_data=$(cat)
  fi
  if echo "$stdin_data" | grep -q "<promise>${completion_promise}<\/promise>"; then
    deactivate "completion promise fulfilled"
  fi
fi

# Check convergence in stdin (agent self-reports task is done)
if [[ ! -t 0 ]]; then
  stdin_data="${stdin_data:-$(cat)}"
  if echo "$stdin_data" | grep -q "<converged/>"; then
    deactivate "converged: agent self-reported task complete"
  fi
fi

# Check MISSION.md status: complete → auto-deactivate
if [[ -f "$mission_file" ]]; then
  mission_status=$(grep "^status:" "$mission_file" 2>/dev/null | head -1 | sed 's/^status: *//' | tr -d '"' | tr -d "'" || true)
  if [[ "$mission_status" == "complete" ]]; then
    deactivate "MISSION.md status is complete — auto-converged"
  fi
fi

# Profile-driven convergence check (objective, data-based)
# Uses odyssey_helper.py convergence-check to read recent waypoints
if [[ -f "odyssey.jsonl" ]]; then
  conv_result=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/odyssey_helper.py" convergence-check \
    --jsonl odyssey.jsonl --tier "$delivery_tier" 2>/dev/null || echo "")
  if [[ -n "$conv_result" ]]; then
    converged_flag=$(echo "$conv_result" | python3 -c "import sys,json; print(str(json.load(sys.stdin).get('converged',False)).lower())" 2>/dev/null || echo "false")
    conv_reason=$(echo "$conv_result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('reason',''))" 2>/dev/null || echo "")
    if [[ "$converged_flag" == "true" ]]; then
      deactivate "converged: ${conv_reason}"
    fi
  fi
fi

# Profile-driven patience budget check
if [[ "$iteration" -ge "$patience_budget" ]]; then
  deactivate "patience budget exhausted: ${iteration}/${patience_budget} waypoints (tier: ${delivery_tier})"
fi

# Profile-driven stuck detection (uses discard_threshold instead of hardcoded 10)
if [[ "$consecutive_discards" -ge "$discard_threshold" ]]; then
  if [[ "$auto_orient_switch" == "true" ]]; then
    # Auto-switch orientation: stop hook directly mutates state file
    # (fully autonomous — does not depend on agent running sed)
    case "$orientation" in
      engineer)  next_orient="creative" ;;
      creative)  next_orient="production" ;;
      production) next_orient="engineer" ;;
      *)         next_orient="creative" ;;
    esac
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s/^orientation:.*/orientation: ${next_orient}/" "$STATE_FILE"
      sed -i '' "s/^consecutive_discards:.*/consecutive_discards: 0/" "$STATE_FILE"
    else
      sed -i "s/^orientation:.*/orientation: ${next_orient}/" "$STATE_FILE"
      sed -i "s/^consecutive_discards:.*/consecutive_discards: 0/" "$STATE_FILE"
    fi
    cat <<EOF
{"decision":"block","reason":"stuck: ${consecutive_discards} consecutive discards (tier ${delivery_tier} threshold ${discard_threshold}) — auto-switched to ${next_orient}","systemMessage":"ODYSSEY STUCK → AUTO-SWITCH (already applied)\n\nTier: ${delivery_tier} | Discards were ${consecutive_discards}/${discard_threshold} (now reset to 0) | Patience: ${iteration}/${patience_budget}\n\nStop hook has switched orientation: ${orientation} → ${next_orient}. State file already updated. Continue with ${next_orient} compass strategy. No manual action required."}
EOF
    exit 2
  else
    # production tier: require human decision
    cat <<EOF
{"decision":"block","reason":"stuck: ${consecutive_discards} consecutive discards (tier ${delivery_tier}, manual review required)","systemMessage":"ODYSSEY STUCK — MANUAL REVIEW REQUIRED\n\nTier: ${delivery_tier} | Discards: ${consecutive_discards}/${discard_threshold} | Patience: ${iteration}/${patience_budget}\n\nProduction tier does NOT auto-switch orientation. Choose:\n1. Switch orientation — output: /odyssey --orientation creative\n2. Broaden scope — edit MISSION.md Goals section\n3. Cancel — output: /odyssey-cancel\n4. Force exit — output: <converged/>"}
EOF
    exit 2
  fi
fi

# Increment iteration
new_iteration=$((iteration + 1))
if [[ "$(uname)" == "Darwin" ]]; then
  sed -i '' "s/^iteration:.*/iteration: ${new_iteration}/" "$STATE_FILE"
else
  sed -i "s/^iteration:.*/iteration: ${new_iteration}/" "$STATE_FILE"
fi

# Read MISSION.md for context (truncate to avoid oversized systemMessage)
mission_context=""
if [[ -f "$mission_file" ]]; then
  mission_context=$(head -80 "$mission_file")
fi

# Build actionable continuation prompt with convergence awareness
cat <<EOF
{"decision":"block","reason":"odyssey waypoint ${new_iteration}","systemMessage":"ODYSSEY WAYPOINT ${new_iteration} | ${orientation} mode | tier: ${delivery_tier} | discards: ${consecutive_discards}/${discard_threshold} | patience: ${iteration}/${patience_budget}\n\nExecute the next waypoint NOW. Follow these steps in order:\n\n1. git add -A && git commit -m \"waypoint-${new_iteration}: checkpoint\"\n2. Read MISSION.md section \"What's Been Tried\" to avoid repeating\n3. CONVERGENCE CHECK: data-driven check runs automatically before each waypoint. If converged, the loop stops. Otherwise continue. Manual check: if last ${convergence_window}+ keeps show avg delta < ${min_metric_delta_pct}%, output <converged/>.\n4. Pick ONE hypothesis from the Ideas Backlog (or generate a new one)\n5. Implement the change (one focused idea)\n6. Run verification: syntax check, then guard command, then metric\n7. DECIDE:\n   - KEEP: if guards pass and metric improved → commit, log to odyssey.jsonl, update MISSION.md Wins, run: python3 \$CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py reset-discards\n   - DISCARD: if any guard fails → git reset --hard HEAD~1, log to odyssey.jsonl, update MISSION.md Dead Ends (consecutive_discards will increment)\n8. Output a ONE LINE recap, then continue to next waypoint\n\nProfile context: tier=${delivery_tier}, patience=${patience_budget}, discard_limit=${discard_threshold}, min_delta=${min_metric_delta_pct}%, window=${convergence_window}, auto_switch=${auto_orient_switch}\n\nDo NOT stop. Do NOT ask for permission. Do NOT wait for user input.\n\nWhen you judge the task is complete (no more meaningful improvements possible), output <converged/> on a line by itself.\n\n---\nMISSION CONTEXT:\n${mission_context}"}
EOF

exit 2
