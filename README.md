# Reformat Helper

Scripts to make Windows reformats painless. Run the pre-reformat stuff before wiping, clone this repo on the fresh install, run the post-reformat script, done.

---

## BEFORE Reformatting

### 1. Run the audit

```powershell
cd C:\Users\sakha\Code\reformat_helper
python pre_reformat_audit.py
```

This scans `C:\Users\sakha\Code` for dirty repos, unpushed work, standalone tools (ffmpeg, yt-dlp, etc.), AppData configs, and installed programs. Generates a full report with a checklist in `reformat_audit_output/`.

### 2. Export snapshots you'll want later

Open **PowerShell** (not CMD) and run these:

```powershell
# VS Code extensions (the post-reformat script uses vscode_extensions.txt in this repo,
# but this is a fresh backup just in case)
code --list-extensions > $env:USERPROFILE\Desktop\vscode-extensions.txt

# npm global packages
npm list -g --depth=0 > $env:USERPROFILE\Desktop\npm-globals.txt

# Python packages (full list including sub-deps — safer for restore)
pip freeze > $env:USERPROFILE\Desktop\python-packages.txt

# If you also want just the top-level packages you intentionally installed:
pip list --not-required > $env:USERPROFILE\Desktop\python-packages-toplevel.txt
```

### 3. Back up these folders/files

Copy all of these to a USB drive or cloud folder (e.g. `K:\after reformatting\`):

| What | Where | Why |
|------|-------|-----|
| Git config | `C:\Users\sakha\.gitconfig` | User name, email, LFS config, autocrlf |
| AWS credentials | `C:\Users\sakha\.aws\` | AWS CLI config |
| Azure credentials | `C:\Users\sakha\.azure\` | Azure CLI config |
| Claude settings | `C:\Users\sakha\.claude\` and `.claude.json` | Claude Code config and credentials |
| VS Code settings | `%APPDATA%\Code\User\` | `settings.json`, `keybindings.json`, snippets. Or check if Settings Sync is on: File → Preferences → Settings Sync |
| The export files | From your Desktop | The `.txt` files from step 2 |
| The audit report | `reformat_audit_output/` folder | Your pre-reformat checklist and full scan |

### 4. Make sure everything is pushed

Check the audit report for:
- Dirty repos (uncommitted changes)
- Local-only branches (no upstream)
- Local-only commits (not pushed)
- Stashes (WILL be lost)
- Non-git directories (no remote backup at all)

### 5. Commit and push this repo

```powershell
cd C:\Users\sakha\Code\reformat_helper
git add -A
git commit -m "Pre-reformat snapshot"
git push
```

Now you're safe to reformat.

---

## Reformatting

1. Download **Media Creation Tool** from Microsoft
2. Plug in a fast USB drive (or external NVMe)
3. Run Media Creation Tool — it downloads Windows and creates a bootable USB in one step
4. Restart, mash **F12** (or **Del**) to get to the boot menu
5. Select the USB drive, let Windows install, reformat your drive
6. Complete Windows setup

---

## AFTER Reformatting

### Step 1: Get Python + Git (just these two, manually)

You need these two things before the script can take over:

1. Download and install **Python** from [python.org](https://www.python.org/downloads/)
   - **Check "Add Python to PATH"** during install
2. Download and install **Git** from [git-scm.com](https://git-scm.com/download/win)
   - Or just download this repo as a ZIP from GitHub

### Step 2: Clone this repo and run the setup script

```powershell
mkdir C:\Users\sakha\Code
cd C:\Users\sakha\Code
git clone https://github.com/sakhaltai/reformat_helper.git
cd reformat_helper
```

**Right-click PowerShell → Run as Administrator**, then:

```powershell
python post_reformat_setup.py
```

Go make coffee. The script installs **everything** automatically — dev tools AND desktop apps.

### What the script installs automatically

| Phase | What | How |
|-------|------|-----|
| 1 | Chocolatey | PowerShell installer |
| 2 | Git, Git LFS, ffmpeg, yt-dlp | `choco install` |
| 2 | Python + pip | `choco install` |
| 2 | NVM for Windows + Node.js LTS | `choco install` + `nvm install lts` |
| 2 | Yarn | `npm install -g yarn` |
| 3 | Chrome, Firefox | `choco install` |
| 3 | Blender, OBS, HandBrake, VLC, K-Lite Codec Pack | `choco install` |
| 3 | Spotify | `choco install` |
| 3 | VS Code, GitHub Desktop, Docker Desktop | `choco install` |
| 3 | Obsidian, AutoHotkey, PowerToys, TreeSize Free | `choco install` |
| 3 | Discord, Slack, Signal | `choco install` |
| 3 | Adobe Creative Cloud, Figma, AnyDesk, 1Password | `choco install` |
| 3 | Steam, Epic Games Launcher | `choco install` |
| 3 | Jellyfin Media Player | `choco install` |
| 3 | NVIDIA App | `choco install` |
| 3 | WinRAR, Google Earth Pro, Toggl Track | `choco install` |
| 4 | Macrium Reflect Free 8.0.7783 (pinned) | `choco install --version` |
| 4 | LINE Desktop | `winget install` |
| 5 | VS Code extensions (65) | `code --install-extension` |
| 5 | .gitconfig | File copy from template |

### What it does NOT install (and why)

- **Anaconda** — none of your projects use conda envs. If you need it later: `choco install anaconda3`
- **pnpm** — no projects use it
- **Proton Drive** — install manually if needed
- **aescripts ZXP/UXP Installer** — manual download: https://aescripts.com/learn/zxp-installer/
- **aescripts Manager** — manual download: https://aescripts.com/learn/aescripts-aeplugins-manager-app/

### Step 3: Restore your backups

From your backup drive (e.g. `K:\after reformatting\`):

```powershell
# Claude settings
Copy-Item -Recurse "K:\after reformatting\.claude" "$env:USERPROFILE\.claude"
Copy-Item "K:\after reformatting\.claude.json" "$env:USERPROFILE\.claude.json"

# Git config (the script restores from gitconfig_template, but if you want
# your exact backup instead):
Copy-Item "K:\after reformatting\.gitconfig" "$env:USERPROFILE\.gitconfig"

# AWS / Azure (if you use them)
Copy-Item -Recurse "K:\after reformatting\.aws" "$env:USERPROFILE\.aws"
Copy-Item -Recurse "K:\after reformatting\.azure" "$env:USERPROFILE\.azure"

# VS Code settings (keybindings, settings, snippets)
Copy-Item -Recurse "K:\after reformatting\users_appdata_roaming_code_users\*" "$env:APPDATA\Code\User\"
```

### Step 4: Restore Python/npm packages (optional)

```powershell
# Python packages from your freeze file
pip install -r "K:\after reformatting\python-packages.txt"

# npm globals (read the file and install each one)
Get-Content "K:\after reformatting\npm-globals.txt" | ForEach-Object { npm install -g $_ }
```

### Step 5: Clone all repos + install dependencies

```powershell
cd C:\Users\sakha\Code\reformat_helper
python clone_and_install.py
```

This clones and installs deps for:

| Repo | Location | Manager | Deps |
|------|----------|---------|------|
| bird-bingo | `sakhalteam/` | npm | React, Vite, Tailwind |
| japanese-articles | `sakhalteam/` | npm | React, Vite, Tailwind, react-markdown |
| nikbeat | `sakhalteam/` | npm | React, Vite, Tailwind |
| sakhalteam.github.io | `sakhalteam/` | npm | React, Vite, Three.js |
| adobe-scripts | `Code/` | — | (no deps) |
| ae_expressions | `Code/` | — | (no deps) |
| aeroja | `Code/` | yarn | React, Vite, Tailwind, Adobe CEP |
| python_tools | `Code/` | — | (no deps) |
| reformat_helper | `Code/` | — | (this repo — already cloned) |
| sakhaltai.github.io | `Code/` | npm | React, Vite, Tailwind |

### Step 6: Fonts

Restore from your Macrium backup image.

### Step 7: Verify

```powershell
git --version
python --version
node --version
npm --version
yarn --version
ffmpeg -version
yt-dlp --version
blender --version
code --version
```

### Step 8: Ongoing maintenance

- Run `choco upgrade all -y` periodically to update everything (Macrium Reflect is pinned and won't be touched)
- Run `choco list` to see what's installed via Chocolatey
- Your NVIDIA drivers will update via the NVIDIA App, not choco

---

## Files in this repo

| File | Purpose |
|------|---------|
| `pre_reformat_audit.py` | Run before reformatting — scans everything and generates a report |
| `post_reformat_setup.py` | Run after reformatting (as admin) — installs dev toolchain + desktop apps |
| `clone_and_install.py` | Clones all repos and installs their dependencies |
| `vscode_extensions.txt` | Snapshot of your VS Code extensions |
| `gitconfig_template` | Your .gitconfig to restore |
| `.gitignore` | Keeps audit output out of the repo |
