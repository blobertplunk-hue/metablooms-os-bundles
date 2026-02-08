#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# mb-upload.sh — Upload Android Downloads to MetaBlooms GitHub
# ============================================================
#
# Built under MetaBlooms OS MPP governance:
#   Mastery:  MDEF-SHELL_SCRIPTING_20260208
#   Patterns: IDEMPOTENT (re-run safe), FAIL_CLOSED (unknown ext),
#             MONOTONIC (append-only uploads)
#   CDR:      Every function has rationale explaining WHY
#
# Usage:
#   mb-upload                     Upload all files from Downloads
#   mb-upload "*.zip"             Upload only ZIPs
#   mb-upload somefile.zip        Upload a specific file
#   mb-upload --dry-run           Show what would be uploaded
#   mb-upload --dry-run "*.zip"   Dry run filtered
#   mb-upload --list              List what's in Downloads
#   mb-upload --setup             Run first-time Termux setup
#
# First-time setup (or run mb-upload --setup):
#   pkg install git git-lfs coreutils openssh
#   git lfs install
#   termux-setup-storage
#   git clone <your-repo-url> ~/metablooms-os-bundles
#
# ============================================================

set -euo pipefail

# --- Config ---
DOWNLOADS="/storage/emulated/0/Download"
REPO_DIR="$HOME/metablooms-os-bundles"
BUNDLE_DIR="$REPO_DIR/os_bundles"
GITATTRIBUTES="$REPO_DIR/.gitattributes"
BRANCH="main"
MAX_RETRIES=4
SCRIPT_VERSION="2.0-governed"

# --- Colors (Termux supports ANSI) ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[FAIL]${NC} $*"; }

# ============================================================
# human_size — Format bytes as human-readable
# ============================================================
# Rationale: numfmt is in coreutils which may not be installed
# on a fresh Termux. This fallback ensures the script works
# without it. We try numfmt first (faster, handles edge cases),
# fall back to pure bash arithmetic.
# ============================================================
human_size() {
    local bytes="$1"
    if command -v numfmt &>/dev/null; then
        numfmt --to=iec --suffix=B "$bytes" 2>/dev/null && return
    fi
    # Pure bash fallback
    if   [ "$bytes" -ge 1073741824 ]; then echo "$(( bytes / 1073741824 ))GiB"
    elif [ "$bytes" -ge 1048576 ];    then echo "$(( bytes / 1048576 ))MiB"
    elif [ "$bytes" -ge 1024 ];       then echo "$(( bytes / 1024 ))KiB"
    else echo "${bytes}B"
    fi
}

# ============================================================
# parse_gitattributes — Read LFS-tracked extensions dynamically
# ============================================================
# Rationale: v1 hardcoded LFS_EXTENSIONS which drifts from
# .gitattributes. SC-006 requires dynamic parsing. This reads
# .gitattributes and builds a regex of tracked extensions.
# If .gitattributes doesn't exist, FAIL CLOSED (no way to
# know what's safe to upload).
# ============================================================
parse_gitattributes() {
    if [ ! -f "$GITATTRIBUTES" ]; then
        err ".gitattributes not found at $GITATTRIBUTES"
        err "Cannot determine LFS-tracked extensions. FAIL CLOSED."
        exit 1
    fi

    # Extract patterns like *.zip, *.exe, *.part[0-9]*
    # Convert to a format we can check against
    LFS_PATTERNS=()
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        # Extract the glob pattern (first field)
        local pattern
        pattern=$(echo "$line" | awk '{print $1}')
        # Only include lines that have filter=lfs
        if echo "$line" | grep -q "filter=lfs"; then
            LFS_PATTERNS+=("$pattern")
        fi
    done < "$GITATTRIBUTES"

    if [ ${#LFS_PATTERNS[@]} -eq 0 ]; then
        err "No LFS patterns found in .gitattributes. FAIL CLOSED."
        exit 1
    fi
}

# ============================================================
# is_lfs_tracked — Check if a filename matches LFS patterns
# ============================================================
# Rationale: Uses the dynamically-parsed LFS_PATTERNS array
# instead of a hardcoded regex. Handles glob patterns like
# *.zip, *.part[0-9]*, *.tar.gz by converting them to bash
# pattern matching.
# ============================================================
is_lfs_tracked() {
    local fname="$1"

    for pattern in "${LFS_PATTERNS[@]}"; do
        # Convert glob to extended pattern for case/esac matching
        # *.zip -> matches anything ending in .zip
        # *.part[0-9]* -> matches .part0, .part1, .part01, etc.
        # shellcheck disable=SC2254
        case "$fname" in
            $pattern) return 0 ;;
        esac
    done

    return 1
}

# ============================================================
# preflight — Verify all dependencies before any work
# ============================================================
# Rationale: FAIL_CLOSED pattern. Missing dependencies should
# halt immediately with clear remediation instructions, not
# produce confusing errors halfway through an upload.
# Checks: storage access, repo, git, git-lfs.
# ============================================================
preflight() {
    local failures=0

    # Storage access (requires termux-setup-storage)
    if [ ! -d "$DOWNLOADS" ]; then
        err "Downloads folder not found: $DOWNLOADS"
        err "  Fix: termux-setup-storage"
        failures=$((failures + 1))
    fi

    # Repo clone
    if [ ! -d "$REPO_DIR/.git" ]; then
        err "Repo not found: $REPO_DIR"
        err "  Fix: git clone <your-repo-url> $REPO_DIR"
        failures=$((failures + 1))
    fi

    # Git
    if ! command -v git &>/dev/null; then
        err "git not installed"
        err "  Fix: pkg install git"
        failures=$((failures + 1))
    fi

    # Git LFS
    if ! command -v git-lfs &>/dev/null; then
        err "git-lfs not installed"
        err "  Fix: pkg install git-lfs && git lfs install"
        failures=$((failures + 1))
    fi

    if [ $failures -gt 0 ]; then
        echo ""
        err "$failures preflight check(s) failed. FAIL CLOSED."
        err "Run: mb-upload --setup"
        exit 1
    fi

    # Create bundle dir if needed
    mkdir -p "$BUNDLE_DIR"

    # Parse .gitattributes (also fail-closed)
    parse_gitattributes

    ok "Preflight passed (${#LFS_PATTERNS[@]} LFS patterns loaded)"
}

# ============================================================
# list_downloads — Show what's in the Downloads folder
# ============================================================
# Rationale: User needs to see what's available before deciding
# what to upload. Shows LFS tracking status per file so they
# know which files will need .gitattributes updates.
# ============================================================
list_downloads() {
    local pattern="${1:-*}"
    local count=0
    local total_size=0

    echo ""
    echo -e "${BOLD}=== $DOWNLOADS ===${NC}"
    echo ""
    printf "  %-10s %10s  %s\n" "STATUS" "SIZE" "FILENAME"
    printf "  %-10s %10s  %s\n" "----------" "----------" "$(printf '%0.s-' {1..50})"

    while IFS= read -r -d '' file; do
        local fname
        fname=$(basename "$file")
        local size
        size=$(stat -c%s "$file" 2>/dev/null || echo 0)
        local human
        human=$(human_size "$size")

        local status
        if is_lfs_tracked "$fname"; then
            status="${GREEN}[LFS]${NC}"
        else
            status="${RED}[NO LFS]${NC}"
        fi

        # Check if already in repo
        if [ -f "$BUNDLE_DIR/$fname" ]; then
            status="${DIM}[EXISTS]${NC}"
        fi

        printf "  %-22s %10s  %s\n" "$status" "$human" "$fname"
        count=$((count + 1))
        total_size=$((total_size + size))
    done < <(find "$DOWNLOADS" -maxdepth 1 -type f -name "$pattern" -print0 | sort -z)

    echo ""
    echo "  $count files, $(human_size $total_size) total"
    echo ""
}

# ============================================================
# ensure_lfs_tracking — Gate unknown extensions
# ============================================================
# Rationale: FAIL_CLOSED for unknown extensions. Uploading a
# large file without LFS tracking bloats the git history
# permanently (can't undo without BFG/filter-branch). So we
# refuse to upload unless the user explicitly adds the
# extension to .gitattributes.
# ============================================================
ensure_lfs_tracking() {
    local fname="$1"
    local ext="${fname##*.}"

    if is_lfs_tracked "$fname"; then
        return 0
    fi

    warn "Extension .$ext is NOT LFS-tracked in .gitattributes"
    echo -ne "  Add ${BOLD}*.${ext}${NC} to LFS tracking? [y/N] "
    read -r answer
    if [[ "$answer" =~ ^[Yy] ]]; then
        echo "*.${ext} filter=lfs diff=lfs merge=lfs -text" >> "$GITATTRIBUTES"
        LFS_PATTERNS+=("*.${ext}")
        cd "$REPO_DIR" && git add .gitattributes
        ok "Added *.${ext} to .gitattributes"
        return 0
    else
        warn "Skipping $fname (extension not tracked, user declined)"
        return 1
    fi
}

# ============================================================
# push_with_retry — Push with exponential backoff
# ============================================================
# Rationale: Mobile network is unreliable. A single push failure
# shouldn't abort the whole upload. 4 retries with 2s/4s/8s/16s
# backoff covers most transient failures (30s total wait).
# After 4 failures, FAIL CLOSED — something is genuinely wrong.
# ============================================================
push_with_retry() {
    local attempt=1
    local wait_time=2

    while [ "$attempt" -le "$MAX_RETRIES" ]; do
        info "Push attempt $attempt/$MAX_RETRIES..."
        if git push -u origin "$BRANCH" 2>&1; then
            ok "Push succeeded"
            return 0
        fi

        if [ "$attempt" -lt "$MAX_RETRIES" ]; then
            warn "Push failed, retrying in ${wait_time}s..."
            sleep "$wait_time"
            wait_time=$((wait_time * 2))
        fi
        attempt=$((attempt + 1))
    done

    err "Push failed after $MAX_RETRIES attempts"
    err "Commit is saved locally. Push manually with:"
    err "  cd $REPO_DIR && git push -u origin $BRANCH"
    return 1
}

# ============================================================
# upload — Main upload pipeline
# ============================================================
# Rationale: This is the BUILD phase. It:
# 1. Collects matching files (find -print0 for space safety)
# 2. Shows preview with LFS status and sizes
# 3. Asks confirmation (SC-004)
# 4. Pulls latest to avoid merge conflicts
# 5. Copies each file, checking for duplicates (IDEMPOTENT)
# 6. Gates unknown extensions (FAIL_CLOSED)
# 7. Commits with descriptive message
# 8. Pushes with retry
#
# IDEMPOTENT: re-running skips files that already exist in
# os_bundles/. No duplicate commits, no duplicate files.
#
# MONOTONIC: files are only added, never removed or modified.
# ============================================================
upload() {
    local pattern="${1:-*}"
    local dry_run="${2:-false}"
    local files_to_upload=()
    local skipped=0
    local already_exists=0
    local total_size=0

    # Collect files (null-delimited for space safety per SC-007)
    while IFS= read -r -d '' file; do
        files_to_upload+=("$file")
    done < <(find "$DOWNLOADS" -maxdepth 1 -type f -name "$pattern" -print0 | sort -z)

    if [ ${#files_to_upload[@]} -eq 0 ]; then
        warn "No files matching '$pattern' in $DOWNLOADS"
        return 0
    fi

    echo ""
    info "Found ${#files_to_upload[@]} file(s) matching '$pattern'"
    echo ""

    # Preview (show what we'll upload with status)
    printf "  %-10s %10s  %s\n" "STATUS" "SIZE" "FILENAME"
    printf "  %-10s %10s  %s\n" "----------" "----------" "$(printf '%0.s-' {1..50})"

    for file in "${files_to_upload[@]}"; do
        local fname
        fname=$(basename "$file")
        local size
        size=$(stat -c%s "$file" 2>/dev/null || echo 0)
        local human
        human=$(human_size "$size")

        local status
        if [ -f "$BUNDLE_DIR/$fname" ]; then
            status="${DIM}[EXISTS]${NC}"
            already_exists=$((already_exists + 1))
        elif is_lfs_tracked "$fname"; then
            status="${GREEN}[READY]${NC}"
        else
            status="${YELLOW}[NO LFS]${NC}"
        fi

        printf "  %-22s %10s  %s\n" "$status" "$human" "$fname"
        total_size=$((total_size + size))
    done

    local total_human
    total_human=$(human_size "$total_size")
    local new_count=$(( ${#files_to_upload[@]} - already_exists ))

    echo ""
    info "Total: ${#files_to_upload[@]} files, $total_human"
    if [ $already_exists -gt 0 ]; then
        info "  $already_exists already in repo (will skip)"
        info "  $new_count new file(s) to upload"
    fi

    if [ "$dry_run" = "true" ]; then
        echo ""
        info "Dry run complete — nothing uploaded"
        return 0
    fi

    if [ "$new_count" -eq 0 ]; then
        ok "All files already in repo. Nothing to do. (IDEMPOTENT)"
        return 0
    fi

    # Confirm (SC-004)
    echo ""
    echo -ne "  Upload ${BOLD}$new_count${NC} new file(s) ($total_human) to GitHub? [y/N] "
    read -r confirm
    if [[ ! "$confirm" =~ ^[Yy] ]]; then
        info "Aborted by user"
        return 0
    fi

    # Pull latest to minimize merge conflicts
    cd "$REPO_DIR"
    info "Pulling latest from $BRANCH..."
    git pull origin "$BRANCH" --rebase 2>/dev/null || warn "Pull failed (may be offline, continuing)"

    # Copy and stage (IDEMPOTENT: skip existing files)
    local staged=0
    for file in "${files_to_upload[@]}"; do
        local fname
        fname=$(basename "$file")
        local dest="$BUNDLE_DIR/$fname"

        # IDEMPOTENT check: skip if already in repo
        if [ -f "$dest" ]; then
            skipped=$((skipped + 1))
            continue
        fi

        # FAIL_CLOSED: gate unknown extensions
        if ! ensure_lfs_tracking "$fname"; then
            skipped=$((skipped + 1))
            continue
        fi

        info "Copying: $fname ($(human_size "$(stat -c%s "$file")"))"
        cp -- "$file" "$dest"
        git add -- "os_bundles/$fname"
        staged=$((staged + 1))
    done

    if [ $staged -eq 0 ]; then
        warn "Nothing new to upload ($skipped skipped)"
        return 0
    fi

    # Commit with descriptive message
    local msg="Add $staged file(s) from Android Downloads"

    info "Committing: $msg"
    git commit -m "$msg"

    # Push with retry (handles mobile network flakiness)
    push_with_retry

    echo ""
    echo -e "${BOLD}============================================${NC}"
    ok "Upload complete"
    echo "  Uploaded: $staged"
    echo "  Skipped:  $skipped (duplicates or declined)"
    echo -e "${BOLD}============================================${NC}"
    echo ""
}

# ============================================================
# setup — First-time Termux configuration
# ============================================================
# Rationale: Users shouldn't have to remember 4 separate pkg
# commands. This runs them all in sequence.
# ============================================================
run_setup() {
    echo ""
    info "MetaBlooms OS — Termux First-Time Setup"
    echo ""

    info "Installing packages..."
    pkg install -y git git-lfs coreutils openssh 2>&1 || {
        err "Package installation failed"
        exit 1
    }

    info "Initializing Git LFS..."
    git lfs install

    info "Requesting storage access..."
    termux-setup-storage

    echo ""
    ok "Setup complete. Now clone your repo:"
    echo "  git clone <your-repo-url> ~/metablooms-os-bundles"
    echo ""
    echo "Then run: mb-upload"
    echo ""
}

# ============================================================
# Main — Route to subcommand
# ============================================================

case "${1:-}" in
    --setup|-s)
        run_setup
        ;;
    --list|-l)
        preflight
        list_downloads "${2:-*}"
        ;;
    --dry-run|-n)
        preflight
        upload "${2:-*}" "true"
        ;;
    --help|-h)
        echo ""
        echo -e "${BOLD}mb-upload${NC} v$SCRIPT_VERSION — MetaBlooms Android Uploader"
        echo ""
        echo "Usage:"
        echo "  mb-upload                Upload all files from Downloads"
        echo "  mb-upload '*.zip'        Upload only ZIPs"
        echo "  mb-upload somefile.zip   Upload a specific file"
        echo "  mb-upload --dry-run      Show what would be uploaded"
        echo "  mb-upload --list         List Downloads contents"
        echo "  mb-upload --setup        First-time Termux setup"
        echo "  mb-upload --help         This message"
        echo ""
        echo "Patterns: IDEMPOTENT (safe to re-run), FAIL_CLOSED (unknown extensions),"
        echo "          MONOTONIC (append-only, never deletes)"
        echo ""
        ;;
    *)
        preflight
        upload "${1:-*}" "false"
        ;;
esac
