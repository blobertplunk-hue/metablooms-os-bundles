#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
#  termux-github.sh — Extract & Upload files to GitHub from Android (Termux)
#  Usage: bash termux-github.sh [command] [args...]
#  Commands (optional — omit to open the interactive menu):
#    setup            Run the first-time configuration wizard
#    upload <path>    Upload a file or folder to GitHub
#    extract <file>   Extract an archive
#    push-bundle <file>  Extract an archive then upload the result
# =============================================================================

set -euo pipefail

# ── colours ──────────────────────────────────────────────────────────────────
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m'
B='\033[0;34m' C='\033[0;36m' W='\033[1;37m' N='\033[0m'

# ── config file (~/.termux_github_config) ────────────────────────────────────
CONFIG_FILE="$HOME/.termux_github_config"

save_config() {
  cat > "$CONFIG_FILE" <<EOF
GITHUB_TOKEN="$GITHUB_TOKEN"
GITHUB_USER="$GITHUB_USER"
GITHUB_REPO="$GITHUB_REPO"
GITHUB_BRANCH="$GITHUB_BRANCH"
UPLOAD_DIR="$UPLOAD_DIR"
USE_LFS="$USE_LFS"
EOF
  chmod 600 "$CONFIG_FILE"
}

load_config() {
  [[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
  GITHUB_TOKEN="${GITHUB_TOKEN:-}"
  GITHUB_USER="${GITHUB_USER:-}"
  GITHUB_REPO="${GITHUB_REPO:-}"
  GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
  UPLOAD_DIR="${UPLOAD_DIR:-/}"
  USE_LFS="${USE_LFS:-false}"
}

# ── helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${C}[INFO]${N}  $*"; }
ok()      { echo -e "${G}[OK]${N}    $*"; }
warn()    { echo -e "${Y}[WARN]${N}  $*"; }
err()     { echo -e "${R}[ERROR]${N} $*"; }
die()     { err "$*"; exit 1; }

banner() {
  clear
  echo -e "${W}"
  echo "  ╔══════════════════════════════════════════════╗"
  echo "  ║     Termux GitHub File Manager v1.0          ║"
  echo "  ║  Extract  •  Upload  •  Reusable on Android  ║"
  echo "  ╚══════════════════════════════════════════════╝"
  echo -e "${N}"
}

press_enter() { echo; read -rp "  Press [Enter] to continue..."; }

# ── dependency check ─────────────────────────────────────────────────────────
check_deps() {
  local missing=()
  for cmd in git curl jq; do
    command -v "$cmd" &>/dev/null || missing+=("$cmd")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    warn "Missing packages: ${missing[*]}"
    read -rp "  Install them now? [Y/n] " ans
    if [[ "${ans,,}" != "n" ]]; then
      pkg install -y "${missing[@]}" || die "Installation failed. Run: pkg install ${missing[*]}"
    else
      die "Required tools not installed."
    fi
  fi
}

# ── optional extras (install on demand) ──────────────────────────────────────
ensure_tool() {
  local cmd=$1 pkg=${2:-$1}
  command -v "$cmd" &>/dev/null && return 0
  warn "'$cmd' not found."
  read -rp "  Install '$pkg' now? [Y/n] " ans
  [[ "${ans,,}" == "n" ]] && return 1
  pkg install -y "$pkg" && return 0
  return 1
}

# ── setup wizard ──────────────────────────────────────────────────────────────
run_setup() {
  banner
  echo -e "${W}  === First-time Setup Wizard ===${N}\n"
  echo -e "  You'll need a GitHub Personal Access Token with ${Y}repo${N} scope."
  echo -e "  Create one at: ${B}https://github.com/settings/tokens${N}\n"

  read -rp "  GitHub username      : " GITHUB_USER
  read -rsp "  Personal Access Token: " GITHUB_TOKEN; echo
  read -rp "  Default repo name    : " GITHUB_REPO
  read -rp "  Default branch [main]: " br; GITHUB_BRANCH="${br:-main}"
  read -rp "  Folder inside repo   [/]: " ud; UPLOAD_DIR="${ud:-/}"

  # Trim leading/trailing slashes from UPLOAD_DIR for consistency
  UPLOAD_DIR="${UPLOAD_DIR#/}"; UPLOAD_DIR="${UPLOAD_DIR%/}"

  echo
  read -rp "  Enable Git LFS for large files (>50 MB)? [y/N] " lfs
  USE_LFS=$([[ "${lfs,,}" == "y" ]] && echo true || echo false)

  # Verify token
  info "Verifying credentials..."
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/user")
  if [[ "$code" == "200" ]]; then
    ok "Token verified successfully."
  else
    warn "Token verification failed (HTTP $code). Saved anyway — check your token."
  fi

  save_config
  ok "Config saved to $CONFIG_FILE"
  press_enter
}

# ── extract ───────────────────────────────────────────────────────────────────
do_extract() {
  local src="$1"
  [[ -f "$src" ]] || die "File not found: $src"

  local dest_dir
  # Strip common archive extensions to get a clean output folder name
  dest_dir="${src%.*}"
  [[ "$dest_dir" == *.tar ]] && dest_dir="${dest_dir%.tar}"
  dest_dir="$(basename "$dest_dir")"
  dest_dir="$(dirname "$src")/$dest_dir"

  mkdir -p "$dest_dir"
  info "Extracting '$src' → '$dest_dir' ..."

  case "${src,,}" in
    *.zip)
      ensure_tool unzip unzip || die "unzip required"
      unzip -q "$src" -d "$dest_dir" ;;
    *.tar.gz|*.tgz)
      tar -xzf "$src" -C "$dest_dir" ;;
    *.tar.bz2|*.tbz2)
      tar -xjf "$src" -C "$dest_dir" ;;
    *.tar.xz|*.txz)
      tar -xJf "$src" -C "$dest_dir" ;;
    *.tar)
      tar -xf "$src" -C "$dest_dir" ;;
    *.rar)
      ensure_tool unrar unrar || die "unrar required"
      unrar x "$src" "$dest_dir/" ;;
    *.7z)
      ensure_tool 7z p7zip || die "p7zip required"
      7z x "$src" -o"$dest_dir" ;;
    *.gz)
      # Single gzip file (not tar)
      gunzip -k "$src" -c > "$dest_dir/$(basename "${src%.gz}")" ;;
    *)
      die "Unknown archive type: $src" ;;
  esac

  ok "Extracted to: $dest_dir"
  echo "$dest_dir"   # return value — used by push-bundle
}

# ── GitHub upload (git-based, supports large files & LFS) ────────────────────
do_upload() {
  local src="$1"
  [[ -e "$src" ]] || die "Path not found: $src"
  [[ -n "$GITHUB_TOKEN" ]] || die "Not configured. Run: bash termux-github.sh setup"

  local repo_url="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git"
  local clone_dir
  clone_dir="$(mktemp -d)/repo"

  info "Cloning $GITHUB_USER/$GITHUB_REPO (branch: $GITHUB_BRANCH)..."
  if ! git clone --depth 1 --branch "$GITHUB_BRANCH" "$repo_url" "$clone_dir" 2>/dev/null; then
    # Branch may not exist yet — clone default and create branch
    git clone --depth 1 "$repo_url" "$clone_dir"
    git -C "$clone_dir" checkout -b "$GITHUB_BRANCH"
  fi

  # Configure git identity
  git -C "$clone_dir" config user.name  "${GITHUB_USER}"
  git -C "$clone_dir" config user.email "${GITHUB_USER}@users.noreply.github.com"

  # Set up LFS if requested
  if [[ "$USE_LFS" == "true" ]]; then
    ensure_tool git-lfs git-lfs && git -C "$clone_dir" lfs install --local
  fi

  # Determine target directory inside the repo
  local target_dir="$clone_dir"
  if [[ -n "$UPLOAD_DIR" ]]; then
    target_dir="$clone_dir/$UPLOAD_DIR"
    mkdir -p "$target_dir"
  fi

  # Copy files
  info "Copying files to repo..."
  if [[ -d "$src" ]]; then
    cp -r "$src"/. "$target_dir/"
  else
    cp "$src" "$target_dir/"
  fi

  # Stage everything
  git -C "$clone_dir" add -A

  local changed
  changed=$(git -C "$clone_dir" status --porcelain | wc -l)
  if [[ "$changed" -eq 0 ]]; then
    warn "No changes detected — files may already be up to date."
    rm -rf "$(dirname "$clone_dir")"
    return 0
  fi

  local commit_msg
  commit_msg="Upload $(basename "$src") via Termux — $(date '+%Y-%m-%d %H:%M')"
  git -C "$clone_dir" commit -m "$commit_msg"

  info "Pushing to GitHub..."
  git -C "$clone_dir" push origin "$GITHUB_BRANCH"

  rm -rf "$(dirname "$clone_dir")"
  ok "Uploaded: https://github.com/${GITHUB_USER}/${GITHUB_REPO}/tree/${GITHUB_BRANCH}"
}

# ── upload via GitHub REST API (no git, single small files ≤25 MB) ───────────
do_api_upload() {
  local src="$1"
  [[ -f "$src" ]] || die "File not found: $src"
  [[ -n "$GITHUB_TOKEN" ]] || die "Not configured. Run setup first."

  local size
  size=$(stat -c%s "$src" 2>/dev/null || stat -f%z "$src")
  if [[ "$size" -gt $((25 * 1024 * 1024)) ]]; then
    warn "File is $(( size / 1024 / 1024 )) MB — too large for API upload. Use 'Upload via git' instead."
    return 1
  fi

  local filename
  filename="$(basename "$src")"
  local repo_path="${UPLOAD_DIR:+$UPLOAD_DIR/}$filename"
  local api_url="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/contents/${repo_path}"

  # Check if file exists (need SHA to update)
  local sha
  sha=$(curl -sf -H "Authorization: token $GITHUB_TOKEN" "$api_url" 2>/dev/null \
    | jq -r '.sha // empty') || true

  local content
  content=$(base64 -w 0 "$src")

  local payload
  if [[ -n "$sha" ]]; then
    payload=$(jq -n --arg msg "Update $filename via Termux" \
                    --arg content "$content" \
                    --arg branch "$GITHUB_BRANCH" \
                    --arg sha "$sha" \
      '{message:$msg, content:$content, branch:$branch, sha:$sha}')
  else
    payload=$(jq -n --arg msg "Add $filename via Termux" \
                    --arg content "$content" \
                    --arg branch "$GITHUB_BRANCH" \
      '{message:$msg, content:$content, branch:$branch}')
  fi

  info "Uploading '$filename' via GitHub API..."
  local resp code
  resp=$(curl -s -w "\n%{http_code}" -X PUT \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$payload" "$api_url")
  code=$(tail -1 <<< "$resp")

  if [[ "$code" == "200" || "$code" == "201" ]]; then
    ok "Uploaded: https://github.com/${GITHUB_USER}/${GITHUB_REPO}/blob/${GITHUB_BRANCH}/${repo_path}"
  else
    err "API returned HTTP $code"
    tail -2 <<< "$resp" | head -1 | jq -r '.message // .' 2>/dev/null || true
    return 1
  fi
}

# ── list repo contents ────────────────────────────────────────────────────────
do_list() {
  [[ -n "$GITHUB_TOKEN" ]] || die "Not configured. Run setup first."
  local path="${1:-$UPLOAD_DIR}"
  local url="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/contents/${path}?ref=${GITHUB_BRANCH}"

  info "Listing $GITHUB_USER/$GITHUB_REPO/$path ..."
  curl -sf -H "Authorization: token $GITHUB_TOKEN" "$url" \
    | jq -r '.[] | "\(.type)\t\(.size // 0)\t\(.name)"' \
    | awk -F'\t' '{
        if ($1=="dir")  printf "  📁  %s/\n", $3
        else            printf "  📄  %-40s  %s\n", $3, ($2>1048576 ? int($2/1048576)"MB" : ($2>1024 ? int($2/1024)"KB" : $2"B"))
      }' \
  || err "Could not list repo contents."
}

# ── file picker helper ────────────────────────────────────────────────────────
pick_file() {
  local prompt="${1:-Enter path to file or folder}"
  local path
  read -rp "  $prompt: " path
  # Expand ~ and env vars
  path="${path/#\~/$HOME}"
  echo "$path"
}

# ── interactive menu ──────────────────────────────────────────────────────────
show_config_summary() {
  if [[ -n "$GITHUB_USER" ]]; then
    echo -e "  ${C}Repo:${N} ${GITHUB_USER}/${GITHUB_REPO}  ${C}Branch:${N} ${GITHUB_BRANCH}  ${C}Folder:${N} /${UPLOAD_DIR}  ${C}LFS:${N} ${USE_LFS}"
  else
    echo -e "  ${Y}Not configured — choose option 1 to set up.${N}"
  fi
  echo
}

main_menu() {
  while true; do
    banner
    show_config_summary
    echo -e "  ${W}What would you like to do?${N}\n"
    echo "   1) Setup / Change configuration"
    echo "   2) Upload a file to GitHub          (git — any size)"
    echo "   3) Upload a file to GitHub          (API — ≤25 MB, fastest)"
    echo "   4) Extract an archive"
    echo "   5) Extract an archive → upload to GitHub"
    echo "   6) List files in GitHub repo"
    echo "   7) Open config file in nano"
    echo "   q) Quit"
    echo
    read -rp "  Choice: " choice
    echo

    case "$choice" in
      1)
        run_setup; load_config ;;
      2)
        src=$(pick_file "Path to file or folder to upload")
        do_upload "$src"; press_enter ;;
      3)
        src=$(pick_file "Path to file to upload (≤25 MB)")
        do_api_upload "$src"; press_enter ;;
      4)
        src=$(pick_file "Path to archive file")
        do_extract "$src" > /dev/null; press_enter ;;
      5)
        src=$(pick_file "Path to archive file")
        extracted=$(do_extract "$src")
        echo
        read -rp "  Upload extracted folder '$extracted'? [Y/n] " ans
        [[ "${ans,,}" != "n" ]] && do_upload "$extracted"
        press_enter ;;
      6)
        read -rp "  Subfolder to list [press Enter for default]: " sub
        do_list "$sub"; press_enter ;;
      7)
        nano "$CONFIG_FILE" 2>/dev/null || vi "$CONFIG_FILE"
        load_config ;;
      q|Q|quit|exit)
        echo -e "  ${G}Goodbye!${N}"; exit 0 ;;
      *)
        warn "Unknown option. Please try again."; sleep 1 ;;
    esac
  done
}

# ── entry point ───────────────────────────────────────────────────────────────
load_config
check_deps

case "${1:-menu}" in
  setup)        run_setup ;;
  upload)       [[ -n "${2:-}" ]] || die "Usage: $0 upload <path>"; do_upload "$2" ;;
  api-upload)   [[ -n "${2:-}" ]] || die "Usage: $0 api-upload <path>"; do_api_upload "$2" ;;
  extract)      [[ -n "${2:-}" ]] || die "Usage: $0 extract <archive>"; do_extract "$2" ;;
  push-bundle)  [[ -n "${2:-}" ]] || die "Usage: $0 push-bundle <archive>"
                extracted=$(do_extract "$2"); do_upload "$extracted" ;;
  list)         do_list "${2:-}" ;;
  menu|*)       main_menu ;;
esac
