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
  grep "^$1:" "$STATE_FILE" 2>/dev/null | head -1 | sed "s/^$1: *//" | tr -d '"' | tr -d "'" || true
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
  # Mark as inactive
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' 's/^active:.*/active: false/' "$STATE_FILE"
    sed -i '' 's/^completed_at:.*/completed_at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'/' "$STATE_FILE"
  else
    sed -i 's/^active:.*/active: false/' "$STATE_FILE"
    sed -i 's/^completed_at:.*/completed_at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'/' "$STATE_FILE"
  fi
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
      if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' 's/^active:.*/active: false/' "$STATE_FILE"
        sed -i '' 's/^completed_at:.*/completed_at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'/' "$STATE_FILE"
      else
        sed -i 's/^active:.*/active: false/' "$STATE_FILE"
        sed -i 's/^completed_at:.*/completed_at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'/' "$STATE_FILE"
      fi
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
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' 's/^active:.*/active: false/' "$STATE_FILE"
      sed -i '' 's/^completed_at:.*/completed_at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'/' "$STATE_FILE"
    else
      sed -i 's/^active:.*/active: false/' "$STATE_FILE"
      sed -i 's/^completed_at:.*/completed_at: '"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'/' "$STATE_FILE"
    fi
    echo '{"decision":"allow","reason":"completion promise fulfilled"}'
    exit 0
  fi
fi

# Check stuck (10 consecutive discards)
if [[ "$consecutive_discards" -ge 10 ]]; then
  cat <<EOF
{"decision":"block","reason":"stuck: 10 consecutive discards","systemMessage":"ODYSSEY STUCK: 10 consecutive waypoints discarded. No progress. Options:\n1. Switch orientation — output: /odyssey --orientation creative\n2. Broaden scope — edit MISSION.md Goals section\n3. Cancel — output: /odyssey-cancel\n4. Force exit — output: <promise>STUCK</promise>\n\nWhat would you like to do?"}
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

# Read MISSION.md for context (truncate to avoid oversized systemMessage)
mission_context=""
if [[ -f "$mission_file" ]]; then
  mission_context=$(head -80 "$mission_file")
fi

# Build actionable continuation prompt
cat <<EOF
{"decision":"block","reason":"odyssey waypoint ${new_iteration}","systemMessage":"ODYSSEY WAYPOINT ${new_iteration} | ${orientation} mode | discards: ${consecutive_discards}\n\nExecute the next waypoint NOW. Follow these steps in order:\n\n1. git add -A && git commit -m \"waypoint-${new_iteration}: checkpoint\"\n2. Read MISSION.md section \"What's Been Tried\" to avoid repeating\n3. Pick ONE hypothesis from the Ideas Backlog (or generate a new one)\n4. Implement the change (one focused idea)\n5. Run verification: syntax check, then guard command, then metric\n6. DECIDE:\n   - KEEP: if guards pass and metric improved → commit, log to odyssey.jsonl, update MISSION.md Wins\n   - DISCARD: if any guard fails → git reset --hard HEAD~1, log to odyssey.jsonl, update MISSION.md Dead Ends\n7. Update .claude/odyssey.local.md consecutive_discards counter\n8. Output a ONE LINE recap, then continue to next waypoint\n\nDo NOT stop. Do NOT ask for permission. Do NOT wait for user input.\n\n---\nMISSION CONTEXT:\n${mission_context}"}
EOF

exit 2
