# termux-github.sh — Quick Reference

Extract archives and upload files to GitHub from your Android phone in Termux.

---

## One-time install

```bash
# 1. Install Termux from F-Droid (recommended) or Play Store
# 2. Install core packages
pkg update && pkg install -y git curl jq

# 3. Get this script (one of these ways):
#   a) Clone the repo
git clone https://github.com/YOUR_USER/YOUR_REPO
cd YOUR_REPO

#   b) Or just download the single file
curl -O https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/termux-github.sh

# 4. Make it executable
chmod +x termux-github.sh

# 5. (Optional) Put it on your PATH so you can run it from anywhere
cp termux-github.sh ~/bin/github
```

---

## First run — setup wizard

```bash
bash termux-github.sh setup
```

You will be prompted for:

| Field | Example |
|---|---|
| GitHub username | `blobertplunk` |
| Personal Access Token | `ghp_xxxxxxxxxxxx` |
| Repo name | `metablooms-os-bundles` |
| Default branch | `main` |
| Folder inside repo | `os_bundles` |
| Enable Git LFS for large files? | `y` (if you have files > 50 MB) |

> **Get a token:** GitHub → Settings → Developer settings → Personal access tokens → Generate new token → tick **repo**

Config is saved to `~/.termux_github_config` (chmod 600, only you can read it).

---

## Interactive menu (recommended for daily use)

```bash
bash termux-github.sh
```

```
  ╔══════════════════════════════════════════════╗
  ║     Termux GitHub File Manager v1.0          ║
  ║  Extract  •  Upload  •  Reusable on Android  ║
  ╚══════════════════════════════════════════════╝

   1) Setup / Change configuration
   2) Upload a file to GitHub          (git — any size)
   3) Upload a file to GitHub          (API — ≤25 MB, fastest)
   4) Extract an archive
   5) Extract an archive → upload to GitHub
   6) List files in GitHub repo
   7) Open config file in nano
   q) Quit
```

---

## Command-line shortcuts (for scripting / shortcuts)

```bash
# Upload a single file
bash termux-github.sh upload /sdcard/Download/myfile.zip

# Upload a whole folder
bash termux-github.sh upload /sdcard/Documents/MyProject

# Fast API upload (small files ≤25 MB)
bash termux-github.sh api-upload /sdcard/notes.txt

# Extract an archive
bash termux-github.sh extract /sdcard/Download/archive.zip

# Extract AND upload in one step
bash termux-github.sh push-bundle /sdcard/Download/bundle.tar.gz

# List repo contents
bash termux-github.sh list
bash termux-github.sh list os_bundles
```

---

## Supported archive formats

| Extension | Required package |
|---|---|
| `.zip` | `unzip` (auto-installed) |
| `.tar`, `.tar.gz`, `.tgz` | built-in |
| `.tar.bz2`, `.tbz2` | built-in |
| `.tar.xz`, `.txz` | built-in |
| `.rar` | `unrar` (auto-installed) |
| `.7z` | `p7zip` (auto-installed) |
| `.gz` | built-in |

---

## Large files (> 100 MB)

GitHub blocks individual files over 100 MB. Enable **Git LFS** during setup (`y` when asked). Then:

```bash
# In Termux, install git-lfs
pkg install git-lfs
```

The script will configure LFS automatically for every push when enabled.

---

## Tips

- **Termux storage access** — run `termux-setup-storage` once to get access to `/sdcard/`
- **Alias** — add to `~/.bashrc`: `alias github='bash ~/termux-github.sh'`
- **Re-run setup** anytime to switch repos or rotate your token
- The config file lives at `~/.termux_github_config` — edit it directly with option 7
