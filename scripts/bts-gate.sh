#!/usr/bin/env bash
# BTS Gate — logs decisions, never locks out
# Override: set BTS_OVERRIDE=1 or pass --override as argument
# Core principle: if this script is running, a decision to proceed was already made.

LOGFILE="${BTS_LOG:-/tmp/bts-gate.log}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
CONTEXT="${BTS_CONTEXT:-unspecified}"

log() {
    echo "[$TIMESTAMP] $*" | tee -a "$LOGFILE"
}

# Check for override
OVERRIDE=0
if [[ "${BTS_OVERRIDE}" == "1" ]] || [[ "$*" == *"--override"* ]]; then
    OVERRIDE=1
fi

if [[ "$OVERRIDE" == "1" ]]; then
    log "BTS OVERRIDE active — context: $CONTEXT — PASS"
    exit 0
fi

# Decision was already made upstream (Claude chose to proceed).
# Log it and pass.
log "BTS gate reached — decision already made — context: $CONTEXT — PASS"
exit 0
