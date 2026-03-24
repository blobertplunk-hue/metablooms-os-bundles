#!/usr/bin/env bash
# BTS Gate — Structured Decision Engine
#
# BTS is an audit trail and reasoning record. It never blocks.
# Every consequential decision must be researched, ranked across five options,
# and justified against a single criterion: will this code work — now, in the
# medium term, and in the long term?
#
# Usage (set env vars before calling):
#   BTS_DECISION_CONTEXT  — what decision is being made
#   BTS_OPTIONS           — newline-delimited list of exactly 5 options considered
#   BTS_CHOSEN_OPTION     — number (1-5) of the selected option
#   BTS_JUSTIFICATION     — why this option wins on durability/correctness
#   BTS_LOG               — log file path (default: /tmp/bts-gate.log)
#   BTS_OVERRIDE=1        — manual override (skips option logging)

LOGFILE="${BTS_LOG:-/tmp/bts-gate.log}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

log() {
    printf '%s\n' "$*" | tee -a "$LOGFILE"
}

# Override path
if [[ "${BTS_OVERRIDE}" == "1" ]] || [[ "$*" == *"--override"* ]]; then
    log "--- BTS OVERRIDE [$TIMESTAMP] ---"
    log "Context:   ${BTS_DECISION_CONTEXT:-unspecified}"
    log "Result:    PASS (manual override)"
    log "---"
    exit 0
fi

# Validate inputs
CONTEXT="${BTS_DECISION_CONTEXT:-unspecified}"
CHOSEN="${BTS_CHOSEN_OPTION:-}"
JUSTIFICATION="${BTS_JUSTIFICATION:-}"
OPTIONS="${BTS_OPTIONS:-}"

# Write structured decision log
log "--- BTS DECISION [$TIMESTAMP] ---"
log "Context:   $CONTEXT"
log "Options:"

option_num=1
while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    log "  $option_num. $line"
    (( option_num++ ))
done <<< "$OPTIONS"

if [[ -n "$CHOSEN" ]]; then
    log "Chosen:    Option $CHOSEN"
fi

log "Criterion: Will this code work now, in the medium term, and in the long term?"

if [[ -n "$JUSTIFICATION" ]]; then
    log "Justified: $JUSTIFICATION"
fi

log "Result:    PASS"
log "---"

exit 0
