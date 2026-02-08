#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# mb-upload.sh — Upload Android Downloads to MetaBlooms GitHub
# ============================================================
#
# Usage:
#   mb-upload                     Upload all files from Downloads
#   mb-upload "*.zip"             Upload only ZIPs
#   mb-upload somefile.zip        Upload a specific file
#   mb-upload --dry-run           Show what would be uploaded
#   mb-upload --list              Just list what's in Downloads
#
# First-time setup (run once):
#   pkg install git git-lfs openssh
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
BRANCH="main"
MAX_RETRIES=4

# LFS-tracked extensions (must match .gitattributes)
LFS_EXTENSIONS="zip|7z|tar\.gz|iso|bin|exe|dmg|gguf|safetensors|pt|onnx|db|rtf"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERR]${NC} $1"; }

# --- Preflight checks ---
preflight() {
    # Storage access
    if [ ! -d "$DOWNLOADS" ]; then
        err "Downloads folder not found at $DOWNLOADS"
        err "Run: termux-setup-storage"
        exit 1
    fi

    # Repo exists
    if [ ! -d "$REPO_DIR/.git" ]; then
        err "Repo not found at $REPO_DIR"
        err "Run: git clone <your-repo-url> $REPO_DIR"
        exit 1
    fi

    # Git LFS
    if ! command -v git-lfs &>/dev/null; then
        err "git-lfs not installed"
        err "Run: pkg install git-lfs && git lfs install"
        exit 1
    fi

    # Bundle dir
    mkdir -p "$BUNDLE_DIR"
}

# --- List files in Downloads ---
list_downloads() {
    local pattern="${1:-*}"
    local count=0
    local total_size=0

    echo ""
    echo "=== Files in $DOWNLOADS ==="
    echo ""
    printf "%-60s %10s\n" "FILENAME" "SIZE"
    printf "%-60s %10s\n" "$(printf '%0.s-' {1..60})" "----------"

    while IFS= read -r -d '' file; do
        local fname=$(basename "$file")
        local size=$(stat -c%s "$file" 2>/dev/null || echo 0)
        local human=$(numfmt --to=iec --suffix=B "$size" 2>/dev/null || echo "${size}B")
        printf "%-60s %10s\n" "$fname" "$human"
        count=$((count + 1))
        total_size=$((total_size + size))
    done < <(find "$DOWNLOADS" -maxdepth 1 -type f -name "$pattern" -print0 | sort -z)

    echo ""
    local total_human=$(numfmt --to=iec --suffix=B "$total_size" 2>/dev/null || echo "${total_size}B")
    echo "$count files, $total_human total"
    echo ""
}

# --- Check if extension is LFS-tracked ---
is_lfs_tracked() {
    local fname="$1"
    local ext="${fname##*.}"

    # Handle .part0, .part1, etc.
    if echo "$fname" | grep -qE '\.part[0-9]+$'; then
        return 0
    fi

    # Handle .tar.gz
    if echo "$fname" | grep -qE '\.tar\.gz$'; then
        return 0
    fi

    if echo "$ext" | grep -qiE "^($LFS_EXTENSIONS)$"; then
        return 0
    fi

    return 1
}

# --- Add extension to .gitattributes if needed ---
ensure_lfs_tracking() {
    local fname="$1"
    local ext="${fname##*.}"

    if ! is_lfs_tracked "$fname"; then
        warn "Extension .$ext is NOT in .gitattributes"
        echo -n "Add *.${ext} to LFS tracking? [y/N] "
        read -r answer
        if [[ "$answer" =~ ^[Yy] ]]; then
            echo "*.${ext} filter=lfs diff=lfs merge=lfs -text" >> "$REPO_DIR/.gitattributes"
            cd "$REPO_DIR"
            git add .gitattributes
            ok "Added *.${ext} to .gitattributes"
        else
            warn "Skipping $fname (not LFS-tracked, not added)"
            return 1
        fi
    fi
    return 0
}

# --- Push with retry and exponential backoff ---
push_with_retry() {
    local attempt=1
    local wait=2

    while [ $attempt -le $MAX_RETRIES ]; do
        info "Push attempt $attempt/$MAX_RETRIES..."
        if git push -u origin "$BRANCH" 2>&1; then
            ok "Push succeeded"
            return 0
        fi

        if [ $attempt -lt $MAX_RETRIES ]; then
            warn "Push failed, retrying in ${wait}s..."
            sleep $wait
            wait=$((wait * 2))
        fi
        attempt=$((attempt + 1))
    done

    err "Push failed after $MAX_RETRIES attempts"
    return 1
}

# --- Upload files ---
upload() {
    local pattern="${1:-*}"
    local dry_run="${2:-false}"
    local files_to_upload=()
    local skipped=0
    local total_size=0

    # Collect files
    while IFS= read -r -d '' file; do
        files_to_upload+=("$file")
    done < <(find "$DOWNLOADS" -maxdepth 1 -type f -name "$pattern" -print0 | sort -z)

    if [ ${#files_to_upload[@]} -eq 0 ]; then
        warn "No files matching '$pattern' in $DOWNLOADS"
        exit 0
    fi

    echo ""
    info "Found ${#files_to_upload[@]} file(s) to upload"
    echo ""

    # Show what we'll upload
    for file in "${files_to_upload[@]}"; do
        local fname=$(basename "$file")
        local size=$(stat -c%s "$file" 2>/dev/null || echo 0)
        local human=$(numfmt --to=iec --suffix=B "$size" 2>/dev/null || echo "${size}B")
        local lfs_status=""
        if is_lfs_tracked "$fname"; then
            lfs_status="[LFS]"
        else
            lfs_status="[NOT LFS]"
        fi
        printf "  %-8s %-10s %s\n" "$lfs_status" "$human" "$fname"
        total_size=$((total_size + size))
    done

    local total_human=$(numfmt --to=iec --suffix=B "$total_size" 2>/dev/null || echo "${total_size}B")
    echo ""
    info "Total: $total_human"

    if [ "$dry_run" = "true" ]; then
        echo ""
        info "Dry run — nothing uploaded"
        return 0
    fi

    # Confirm
    echo ""
    echo -n "Upload ${#files_to_upload[@]} files ($total_human) to GitHub? [y/N] "
    read -r confirm
    if [[ ! "$confirm" =~ ^[Yy] ]]; then
        info "Aborted"
        return 0
    fi

    # Pull latest
    cd "$REPO_DIR"
    info "Pulling latest from $BRANCH..."
    git pull origin "$BRANCH" --rebase 2>/dev/null || true

    # Copy and stage files
    local staged=0
    for file in "${files_to_upload[@]}"; do
        local fname=$(basename "$file")
        local dest="$BUNDLE_DIR/$fname"

        # Check if already exists
        if [ -f "$dest" ]; then
            warn "SKIP (already exists): $fname"
            skipped=$((skipped + 1))
            continue
        fi

        # Ensure LFS tracking
        if ! ensure_lfs_tracking "$fname"; then
            skipped=$((skipped + 1))
            continue
        fi

        info "Copying: $fname"
        cp "$file" "$dest"
        git add "os_bundles/$fname"
        staged=$((staged + 1))
    done

    if [ $staged -eq 0 ]; then
        warn "Nothing new to upload (${skipped} skipped)"
        return 0
    fi

    # Commit
    local staged_human=$(cd "$REPO_DIR" && git diff --cached --stat | tail -1)
    local msg="Add $staged file(s) from Android Downloads ($total_human)"

    info "Committing: $msg"
    git commit -m "$msg"

    # Push
    push_with_retry

    echo ""
    ok "Done! $staged uploaded, $skipped skipped"
    echo ""
}

# --- Main ---
preflight

case "${1:-}" in
    --list|-l)
        list_downloads "${2:-*}"
        ;;
    --dry-run|-n)
        upload "${2:-*}" "true"
        ;;
    --help|-h)
        echo "Usage:"
        echo "  mb-upload                Upload all files from Downloads"
        echo "  mb-upload '*.zip'        Upload only ZIPs"
        echo "  mb-upload somefile.zip   Upload a specific file"
        echo "  mb-upload --dry-run      Show what would be uploaded"
        echo "  mb-upload --list         List Downloads contents"
        echo "  mb-upload --help         This message"
        ;;
    *)
        upload "${1:-*}" "false"
        ;;
esac
