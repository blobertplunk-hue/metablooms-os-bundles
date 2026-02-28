#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
#  termux-github.sh — GitHub File Manager for Termux (blobert-hue edition)
#  Usage: bash ~/termux-github.sh [setup|upload <path>|extract <file>|
#                                   push-bundle <file>|list|switch]
# =============================================================================

set -euo pipefail

# ── colours ───────────────────────────────────────────────────────────────────
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m'
B='\033[0;34m' C='\033[0;36m' W='\033[1;37m' N='\033[0m'

# ── hardcoded account ─────────────────────────────────────────────────────────
GITHUB_USER="blobert-hue"
CONFIG_FILE="$HOME/.termux_github_config"

# ── config ────────────────────────────────────────────────────────────────────
save_config() {
  cat > "$CONFIG_FILE" <<EOF
GITHUB_TOKEN="$GITHUB_TOKEN"
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
  GITHUB_REPO="${GITHUB_REPO:-}"
  GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
  UPLOAD_DIR="${UPLOAD_DIR:-}"
  USE_LFS="${USE_LFS:-false}"
}

# ── basic helpers ─────────────────────────────────────────────────────────────
info()  { echo -e "${C}[INFO]${N}  $*"; }
ok()    { echo -e "${G}[OK]${N}    $*"; }
warn()  { echo -e "${Y}[WARN]${N}  $*"; }
err()   { echo -e "${R}[ERROR]${N} $*"; }
die()   { err "$*"; exit 1; }
press_enter() { echo; read -rp "  Press [Enter] to continue..."; }

banner() {
  clear
  echo -e "${W}"
  echo "  ╔═══════════════════════════════════════════════╗"
  echo "  ║    Termux GitHub File Manager  v2.0           ║"
  echo "  ║    ${C}blobert-hue${W}  •  Extract  •  Upload        ║"
  echo "  ╚═══════════════════════════════════════════════╝"
  echo -e "${N}"
}

# ── token resolution (auto-detect, never ask twice) ───────────────────────────
resolve_token() {
  # 1. Already loaded from config or env
  [[ -n "${GITHUB_TOKEN:-}" ]] && return 0

  # 2. Standard env vars set by the user in ~/.bashrc
  if [[ -n "${GH_TOKEN:-}" ]]; then
    GITHUB_TOKEN="$GH_TOKEN"
    info "Token loaded from \$GH_TOKEN."
    return 0
  fi

  # 3. GitHub CLI (gh) if installed
  if command -v gh &>/dev/null; then
    local t
    t=$(gh auth token 2>/dev/null) && [[ -n "$t" ]] && {
      GITHUB_TOKEN="$t"
      info "Token loaded from 'gh' CLI."
      return 0
    }
  fi

  # 4. Prompt — only reached if token is completely absent
  echo
  echo -e "  ${Y}No GitHub token found.${N}"
  echo -e "  Create one at: ${B}https://github.com/settings/tokens${N}"
  echo -e "  Required scope: ${C}repo${N}\n"
  read -rsp "  Paste your Personal Access Token: " GITHUB_TOKEN; echo
  [[ -z "$GITHUB_TOKEN" ]] && die "Token is required."

  # Offer to persist it so this prompt never appears again
  echo
  echo -e "  ${W}Save token so you never need to enter it again?${N}"
  echo "   1) Save to ~/.termux_github_config  (recommended — private file)"
  echo "   2) Also export in ~/.bashrc          (available to all scripts)"
  echo "   3) Neither (token used this session only)"
  echo
  read -rp "  Choice [1]: " tsave; tsave="${tsave:-1}"

  if [[ "$tsave" == "1" || "$tsave" == "2" ]]; then
    save_config
    ok "Token saved to $CONFIG_FILE"
  fi
  if [[ "$tsave" == "2" ]]; then
    {
      echo ""
      echo "# GitHub token — added by termux-github.sh"
      echo "export GITHUB_TOKEN=\"$GITHUB_TOKEN\""
    } >> "$HOME/.bashrc"
    ok "Token exported in ~/.bashrc — run 'source ~/.bashrc' or open a new session."
  fi
}

# ── GitHub API wrapper ────────────────────────────────────────────────────────
gh_api() { curl -sf -H "Authorization: token $GITHUB_TOKEN" "$@"; }

# ── repo & branch fetchers ────────────────────────────────────────────────────
fetch_repos() {
  # Fetch up to 200 repos (2 pages), sorted by last-updated
  local page1 page2
  page1=$(gh_api "https://api.github.com/users/${GITHUB_USER}/repos?per_page=100&sort=updated&type=all&page=1" \
    | jq -r '.[].name') || true
  page2=$(gh_api "https://api.github.com/users/${GITHUB_USER}/repos?per_page=100&sort=updated&type=all&page=2" \
    | jq -r '.[].name') || true
  printf '%s\n%s\n' "$page1" "$page2" | grep -v '^$' | head -100
}

fetch_branches() {
  local repo="${1:-$GITHUB_REPO}"
  gh_api "https://api.github.com/repos/${GITHUB_USER}/${repo}/branches?per_page=100" \
    | jq -r '.[].name' 2>/dev/null || echo "main"
}

# ── numbered list picker ──────────────────────────────────────────────────────
pick_from_list() {
  # Usage: pick_from_list "prompt" "current_default" item1 item2 ...
  local prompt="$1" default="${2:-}"; shift 2
  local items=("$@") i=1
  for item in "${items[@]}"; do
    if [[ "$item" == "$default" ]]; then
      printf "  ${G}%3d)${N} %-40s ${Y}<-- current${N}\n" "$i" "$item"
    else
      printf "  %3d) %s\n" "$i" "$item"
    fi
    ((i++)) || true
  done
  echo
  local n
  while true; do
    read -rp "  $prompt [1-${#items[@]}]: " n
    [[ "$n" =~ ^[0-9]+$ ]] && (( n >= 1 && n <= ${#items[@]} )) && break
    warn "Enter a number between 1 and ${#items[@]}"
  done
  echo "${items[$((n-1))]}"
}

pick_repo() {
  info "Fetching your repositories from GitHub..."
  local repos=()
  mapfile -t repos < <(fetch_repos 2>/dev/null)
  [[ ${#repos[@]} -eq 0 ]] && die "No repositories found. Check your token/connection."
  echo
  echo -e "  ${W}Your repositories (most recently updated first):${N}\n"
  pick_from_list "Select repo" "${GITHUB_REPO:-}" "${repos[@]}"
}

pick_branch() {
  local repo="${1:-$GITHUB_REPO}"
  info "Fetching branches for $repo..."
  local branches=()
  mapfile -t branches < <(fetch_branches "$repo" 2>/dev/null)
  [[ ${#branches[@]} -eq 0 ]] && { echo "main"; return; }
  echo
  echo -e "  ${W}Branches in $repo:${N}\n"
  pick_from_list "Select branch" "${GITHUB_BRANCH:-main}" "${branches[@]}"
}

pick_file() {
  local path
  read -rp "  ${1:-Path}: " path
  path="${path/#\~/$HOME}"
  echo "$path"
}

# ── dependency check ──────────────────────────────────────────────────────────
check_deps() {
  local missing=()
  for cmd in git curl jq; do
    command -v "$cmd" &>/dev/null || missing+=("$cmd")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    warn "Missing packages: ${missing[*]}"
    read -rp "  Install them now? [Y/n] " ans
    [[ "${ans,,}" != "n" ]] || die "Required tools not installed."
    pkg install -y "${missing[@]}" || die "pkg install failed."
  fi
}

ensure_tool() {
  local cmd=$1 pkg=${2:-$1}
  command -v "$cmd" &>/dev/null && return 0
  warn "'$cmd' not found."
  read -rp "  Install '$pkg' now? [Y/n] " ans
  [[ "${ans,,}" == "n" ]] && return 1
  pkg install -y "$pkg" && return 0 || return 1
}

# ── setup wizard ───────────────────────────────────────────────────────────────
run_setup() {
  banner
  echo -e "${W}  === Setup Wizard ===${N}\n"
  echo -e "  ${C}GitHub user:${N} ${W}$GITHUB_USER${N}  (hardcoded — no need to type it)\n"

  resolve_token

  # Verify & show who we are
  info "Verifying token with GitHub..."
  local me code
  me=$(gh_api "https://api.github.com/user" 2>/dev/null) || me="{}"
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/user")
  if [[ "$code" == "200" ]]; then
    ok "Authenticated as: $(jq -r '.login' <<< "$me")"
  else
    warn "Token check returned HTTP $code — saved anyway, double-check your token."
  fi

  # Pick repo from live list
  echo
  GITHUB_REPO=$(pick_repo)
  echo -e "\n  ${G}Repo selected:${N} $GITHUB_REPO"

  # Pick branch from live list
  echo
  GITHUB_BRANCH=$(pick_branch "$GITHUB_REPO")
  echo -e "\n  ${G}Branch selected:${N} $GITHUB_BRANCH"

  # Folder inside repo
  echo
  read -rp "  Upload folder inside repo (leave blank for root): " ud
  UPLOAD_DIR="${ud:-}"
  UPLOAD_DIR="${UPLOAD_DIR#/}"; UPLOAD_DIR="${UPLOAD_DIR%/}"

  # LFS
  echo
  read -rp "  Enable Git LFS for files >50 MB? [y/N] " lfs
  USE_LFS=$([[ "${lfs,,}" == "y" ]] && echo true || echo false)

  save_config
  echo
  ok "All done! Config saved to $CONFIG_FILE"
  echo -e "\n  Run ${C}bash ~/termux-github.sh${N} anytime to open the menu."
  press_enter
}

# ── switch repo / branch without full re-setup ────────────────────────────────
switch_target() {
  banner
  echo -e "${W}  === Switch Repo / Branch ===${N}\n"
  resolve_token

  echo -e "  Current: ${C}${GITHUB_REPO}${N} / ${C}${GITHUB_BRANCH}${N}\n"
  echo "   1) Switch repo (then pick branch)"
  echo "   2) Switch branch only (stay in $GITHUB_REPO)"
  echo "   b) Back"
  echo
  read -rp "  Choice: " c; echo
  case "$c" in
    1) GITHUB_REPO=$(pick_repo)
       echo -e "\n  ${G}Repo:${N} $GITHUB_REPO"
       GITHUB_BRANCH=$(pick_branch "$GITHUB_REPO")
       echo -e "\n  ${G}Branch:${N} $GITHUB_BRANCH" ;;
    2) GITHUB_BRANCH=$(pick_branch "$GITHUB_REPO")
       echo -e "\n  ${G}Branch:${N} $GITHUB_BRANCH" ;;
    b|B) return ;;
  esac
  save_config
  echo
  ok "Switched to ${GITHUB_REPO} / ${GITHUB_BRANCH}"
  press_enter
}

# ── extract ────────────────────────────────────────────────────────────────────
do_extract() {
  local src="$1"
  [[ -f "$src" ]] || die "File not found: $src"

  local dest_dir
  dest_dir="${src%.*}"
  [[ "$dest_dir" == *.tar ]] && dest_dir="${dest_dir%.tar}"
  dest_dir="$(dirname "$src")/$(basename "$dest_dir")"
  mkdir -p "$dest_dir"

  info "Extracting '$(basename "$src")' → '$dest_dir' ..."
  case "${src,,}" in
    *.zip)             ensure_tool unzip unzip || die "unzip required"
                       unzip -q "$src" -d "$dest_dir" ;;
    *.tar.gz|*.tgz)   tar -xzf "$src" -C "$dest_dir" ;;
    *.tar.bz2|*.tbz2) tar -xjf "$src" -C "$dest_dir" ;;
    *.tar.xz|*.txz)   tar -xJf "$src" -C "$dest_dir" ;;
    *.tar)             tar -xf  "$src" -C "$dest_dir" ;;
    *.rar)             ensure_tool unrar unrar || die "unrar required"
                       unrar x "$src" "$dest_dir/" ;;
    *.7z)              ensure_tool 7z p7zip || die "p7zip required"
                       7z x "$src" -o"$dest_dir" ;;
    *.gz)              gunzip -k "$src" -c > "$dest_dir/$(basename "${src%.gz}")" ;;
    *)                 die "Unknown archive type: $src" ;;
  esac

  ok "Extracted to: $dest_dir"
  echo "$dest_dir"
}

# ── upload via git (any size) ──────────────────────────────────────────────────
do_upload() {
  local src="$1"
  [[ -e "$src" ]] || die "Path not found: $src"
  [[ -n "$GITHUB_TOKEN" ]] || die "Not configured — run setup first."
  [[ -n "$GITHUB_REPO"  ]] || die "No repo selected — run setup first."

  local repo_url="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git"
  local clone_dir
  clone_dir="$(mktemp -d)/repo"

  info "Cloning ${GITHUB_USER}/${GITHUB_REPO} (${GITHUB_BRANCH})..."
  if ! git clone --depth 1 --branch "$GITHUB_BRANCH" "$repo_url" "$clone_dir" 2>/dev/null; then
    git clone --depth 1 "$repo_url" "$clone_dir"
    git -C "$clone_dir" checkout -b "$GITHUB_BRANCH"
  fi

  git -C "$clone_dir" config user.name  "$GITHUB_USER"
  git -C "$clone_dir" config user.email "$GITHUB_USER@users.noreply.github.com"

  if [[ "$USE_LFS" == "true" ]]; then
    ensure_tool git-lfs git-lfs && git -C "$clone_dir" lfs install --local
  fi

  local target_dir="$clone_dir"
  if [[ -n "$UPLOAD_DIR" ]]; then
    target_dir="$clone_dir/$UPLOAD_DIR"
    mkdir -p "$target_dir"
  fi

  info "Copying files..."
  if [[ -d "$src" ]]; then cp -r "$src"/. "$target_dir/"
  else                      cp "$src" "$target_dir/"
  fi

  git -C "$clone_dir" add -A
  local changed
  changed=$(git -C "$clone_dir" status --porcelain | wc -l)
  if [[ "$changed" -eq 0 ]]; then
    warn "No changes detected — files already up to date."
    rm -rf "$(dirname "$clone_dir")"
    return 0
  fi

  git -C "$clone_dir" commit -m "Upload $(basename "$src") via Termux — $(date '+%Y-%m-%d %H:%M')"
  info "Pushing to GitHub..."
  git -C "$clone_dir" push origin "$GITHUB_BRANCH"
  rm -rf "$(dirname "$clone_dir")"
  ok "Done: https://github.com/${GITHUB_USER}/${GITHUB_REPO}/tree/${GITHUB_BRANCH}"
}

# ── upload via GitHub API (single files ≤25 MB, no git clone needed) ──────────
do_api_upload() {
  local src="$1"
  [[ -f "$src" ]] || die "File not found: $src"
  [[ -n "$GITHUB_TOKEN" ]] || die "Not configured — run setup first."
  [[ -n "$GITHUB_REPO"  ]] || die "No repo selected — run setup first."

  local size
  size=$(stat -c%s "$src" 2>/dev/null || stat -f%z "$src")
  if (( size > 25 * 1024 * 1024 )); then
    warn "File is $(( size / 1024 / 1024 )) MB — too large for API. Use 'Upload via git' instead."
    return 1
  fi

  local filename repo_path api_url sha content payload resp code
  filename="$(basename "$src")"
  repo_path="${UPLOAD_DIR:+$UPLOAD_DIR/}$filename"
  api_url="https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/contents/${repo_path}"

  sha=$(gh_api "$api_url" 2>/dev/null | jq -r '.sha // empty') || true
  content=$(base64 -w 0 "$src")

  if [[ -n "$sha" ]]; then
    payload=$(jq -n --arg msg "Update $filename via Termux" \
      --arg content "$content" --arg branch "$GITHUB_BRANCH" --arg sha "$sha" \
      '{message:$msg,content:$content,branch:$branch,sha:$sha}')
  else
    payload=$(jq -n --arg msg "Add $filename via Termux" \
      --arg content "$content" --arg branch "$GITHUB_BRANCH" \
      '{message:$msg,content:$content,branch:$branch}')
  fi

  info "Uploading '$filename' via GitHub API..."
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

# ── list repo contents ─────────────────────────────────────────────────────────
do_list() {
  [[ -n "$GITHUB_TOKEN" ]] || die "Not configured — run setup first."
  [[ -n "$GITHUB_REPO"  ]] || die "No repo selected — run setup first."
  local path="${1:-$UPLOAD_DIR}"
  info "Listing ${GITHUB_USER}/${GITHUB_REPO}/${path} (${GITHUB_BRANCH})..."
  gh_api "https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/contents/${path}?ref=${GITHUB_BRANCH}" \
    | jq -r '.[] | "\(.type)\t\(.size // 0)\t\(.name)"' \
    | awk -F'\t' '{
        if ($1=="dir") printf "  [DIR]  %s/\n", $3
        else printf "  [FILE] %-40s  %s\n", $3,
          ($2>1048576 ? int($2/1048576)"MB" : ($2>1024 ? int($2/1024)"KB" : $2"B"))
      }' || err "Could not list repo contents."
}

# ── interactive menu ───────────────────────────────────────────────────────────
show_config_summary() {
  local tok_hint="(none)"
  [[ -n "$GITHUB_TOKEN" ]] && tok_hint="${GITHUB_TOKEN:0:4}••••••••"
  if [[ -n "$GITHUB_REPO" ]]; then
    echo -e "  ${C}User:${N} $GITHUB_USER  ${C}Repo:${N} $GITHUB_REPO  ${C}Branch:${N} $GITHUB_BRANCH  ${C}Folder:${N} /${UPLOAD_DIR:-}  ${C}LFS:${N} $USE_LFS"
    echo -e "  ${C}Token:${N} $tok_hint"
  else
    echo -e "  ${Y}Not configured — press 1 to run setup.${N}"
    echo -e "  ${C}User:${N} $GITHUB_USER  ${C}Token:${N} $tok_hint"
  fi
  echo
}

main_menu() {
  while true; do
    banner
    show_config_summary
    echo -e "  ${W}What would you like to do?${N}\n"
    echo "   1) Setup (first time or reconfigure)"
    echo "   2) Switch repo / branch"
    echo "   3) Upload a file or folder  (git — any size)"
    echo "   4) Upload a single file     (API — ≤25 MB, no clone needed)"
    echo "   5) Extract an archive"
    echo "   6) Extract an archive + upload to GitHub"
    echo "   7) List files in current repo"
    echo "   8) Edit config in nano"
    echo "   q) Quit"
    echo
    read -rp "  Choice: " choice; echo

    case "$choice" in
      1) run_setup; load_config ;;
      2) switch_target; load_config ;;
      3) do_upload "$(pick_file 'Path to file or folder')"; press_enter ;;
      4) do_api_upload "$(pick_file 'Path to file (≤25 MB)')"; press_enter ;;
      5) do_extract "$(pick_file 'Path to archive')" > /dev/null; press_enter ;;
      6) local src extracted
         src=$(pick_file 'Path to archive')
         extracted=$(do_extract "$src")
         echo; read -rp "  Upload extracted folder '$extracted'? [Y/n] " ans
         [[ "${ans,,}" != "n" ]] && do_upload "$extracted"
         press_enter ;;
      7) read -rp "  Subfolder [Enter for root]: " sub
         do_list "$sub"; press_enter ;;
      8) nano "$CONFIG_FILE" 2>/dev/null || vi "$CONFIG_FILE"; load_config ;;
      q|Q|quit|exit) echo -e "  ${G}Goodbye!${N}"; exit 0 ;;
      *) warn "Unknown option. Try again."; sleep 1 ;;
    esac
  done
}

# ── entry point ────────────────────────────────────────────────────────────────
load_config
check_deps
resolve_token

case "${1:-menu}" in
  setup)       run_setup ;;
  switch)      switch_target ;;
  upload)      [[ -n "${2:-}" ]] || die "Usage: $0 upload <path>"; do_upload "$2" ;;
  api-upload)  [[ -n "${2:-}" ]] || die "Usage: $0 api-upload <path>"; do_api_upload "$2" ;;
  extract)     [[ -n "${2:-}" ]] || die "Usage: $0 extract <archive>"; do_extract "$2" ;;
  push-bundle) [[ -n "${2:-}" ]] || die "Usage: $0 push-bundle <archive>"
               extracted=$(do_extract "$2"); do_upload "$extracted" ;;
  list)        do_list "${2:-}" ;;
  menu|*)      main_menu ;;
esac
