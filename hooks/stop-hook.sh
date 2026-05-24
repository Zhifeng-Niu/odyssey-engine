#!/usr/bin/env bash
# Odyssey Engine Stop Hook
# Prevents the agent from exiting mid-mission. Forked from ralph-loop with
# additions: time budget, consecutive discard tracking, orientation awareness.
set -euo pipefail

STATE_FILE=".claude/odyssey.local.md"

# No state file → no active mission → allow exit
if [[ ! -f "$STATE_FILE" ]]; then
  exit 0
fi

# Parse frontmatter values
get_fm_value() {
  grep "^$1:" "$STATE_FILE" | head -1 | sed "s/^$1: *//" | tr -d '"' | tr -d "'"
}

active=$(get_fm_value "active")
if [[ "$active" != "true" ]]; then
  exit 0
fi

iteration=$(get_fm_value "iteration" || echo "0")
max_iterations=$(get_fm_value "max_iterations" || echo "0")
session_id=$(get_fm_value "session_id")
completion_promise=$(get_fm_value "completion_promise")
orientation=$(get_fm_value "orientation" || echo "engineer")
started_at=$(get_fm_value "started_at")
time_budget_seconds=$(get_fm_value "time_budget_seconds" || echo "0")
consecutive_discards=$(get_fm_value "consecutive_discards" || echo "0")
mission_file=$(get_fm_value "mission_file" || echo "MISSION.md")

# Validate numeric fields
iteration=${iteration:-0}
max_iterations=${max_iterations:-0}
consecutive_discards=${consecutive_discards:-0}

# Check max iterations
if [[ "$max_iterations" -gt 0 ]] && [[ "$iteration" -ge "$max_iterations" ]]; then
  # Mission complete — remove state file and allow exit
  rm -f "$STATE_FILE"
  echo '{"decision":"allow","reason":"max iterations reached ('"$iteration"'/'"$max_iterations"')"}'
  exit 0
fi

# Check time budget
if [[ "$time_budget_seconds" -gt 0 ]] && [[ -n "$started_at" ]]; then
  started_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$started_at" "+%s" 2>/dev/null || date -d "$started_at" "+%s" 2>/dev/null || echo "0")
  if [[ "$started_epoch" -gt 0 ]]; then
    now_epoch=$(date "+%s")
    elapsed=$((now_epoch - started_epoch))
    if [[ "$elapsed" -ge "$time_budget_seconds" ]]; then
      rm -f "$STATE_FILE"
      echo '{"decision":"allow","reason":"time budget exceeded ('"$elapsed"'s/'"$time_budget_seconds"'s)"}'
      exit 0
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
    rm -f "$STATE_FILE"
    echo '{"decision":"allow","reason":"completion promise fulfilled"}'
    exit 0
  fi
fi

# Check stuck (10 consecutive discards)
if [[ "$consecutive_discards" -ge 10 ]]; then
  cat <<EOF
{"decision":"block","reason":"stuck: 10 consecutive discards","systemMessage":"⚠️ ODYSSEY STUCK: 10 consecutive waypoints discarded with no progress. Consider: (1) switch orientation with /odyssey --orientation creative, (2) broaden scope, (3) /odyssey-cancel to stop. Output <promise>STUCK</promise> to exit gracefully."}
EOF
  exit 2
fi

# Increment iteration
new_iteration=$((iteration + 1))
if [[ "$(uname)" == "Darwin" ]]; then
  sed -i '' "s/^iteration:.*/iteration: ${new_iteration}/" "$STATE_FILE"
else
  sed -i "s/^iteration:.*/iteration: ${new_iteration}/" "$STATE_FILE"
fi

# Read mission prompt
mission_prompt=""
if [[ -f "$mission_file" ]]; then
  mission_prompt=$(cat "$mission_file")
fi

# Build status line
status_line="Odyssey waypoint ${new_iteration} | ${orientation} mode | discards: ${consecutive_discards}"

# Block exit and replay prompt
cat <<EOF
{"decision":"block","reason":"odyssey mission active, waypoint ${new_iteration}","systemMessage":"🔄 ${status_line}\n\nContinue the mission. Follow the loop procedure: checkpoint → act → verify → decide → record. To stop: output <promise>${completion_promise}<\/promise>\n\n---\nMISSION:\n${mission_prompt}"}
EOF

exit 2
