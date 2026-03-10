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

Copy all of these to a USB drive or cloud folder:

| What | Where | Why |
|------|-------|-----|
| SSH keys | `C:\Users\sakha\.ssh\` | Without these you'd need to generate new keys and re-add them to GitHub |
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

## AFTER Reformatting

### Step 1: Get Python + Git

You need these two things manually before the script can take over:

1. Download and install **Python** from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during install
2. Download and install **Git** from [git-scm.com](https://git-scm.com/download/win)
   - Or just download this repo as a ZIP from GitHub

### Step 2: Clone and run

```powershell
cd C:\Users\sakha\Code
git clone https://github.com/sakhaltai/reformat_helper.git
cd reformat_helper
```

**Right-click PowerShell → Run as Administrator**, then:

```powershell
python post_reformat_setup.py
```

Go make coffee. The script handles everything below automatically.

### What the script installs

| Tool | How | Why |
|------|-----|-----|
| Chocolatey | PowerShell installer | Package manager for Windows (like apt/brew) |
| Git + Git LFS | `choco install` | Version control (your repos use LFS) |
| ffmpeg | `choco install` | Audio/video processing |
| yt-dlp | `choco install` | Video downloader |
| Python + pip | `choco install` | Python dev |
| NVM for Windows | `choco install` | Manages Node.js versions |
| Node.js LTS | `nvm install lts` | JavaScript runtime (includes npm and npx) |
| Yarn | `npm install -g yarn` | Package manager (aeroja, aether use it) |
| VS Code extensions | `code --install-extension` | All 65 extensions from your current setup |
| .gitconfig | File copy | Your git user/email, LFS, autocrlf |

### What it does NOT install (and why)

- **Anaconda** — 20GB and none of your projects use conda envs. If you need it: `choco install anaconda3`
- **pnpm** — no projects use it
- **Desktop apps** — the script prints a list of download links at the end

### Step 3: Restore your backups

From your USB drive / cloud backup:

```powershell
# SSH keys
Copy-Item -Recurse "D:\backup\.ssh" "$env:USERPROFILE\.ssh"

# Claude settings
Copy-Item -Recurse "D:\backup\.claude" "$env:USERPROFILE\.claude"
Copy-Item "D:\backup\.claude.json" "$env:USERPROFILE\.claude.json"

# AWS / Azure (if you use them)
Copy-Item -Recurse "D:\backup\.aws" "$env:USERPROFILE\.aws"
Copy-Item -Recurse "D:\backup\.azure" "$env:USERPROFILE\.azure"
```

### Step 4: Restore Python/npm packages (optional)

```powershell
# Python packages from your freeze file
pip install -r D:\backup\python-packages.txt

# npm globals (read the file and install each one)
Get-Content D:\backup\npm-globals.txt | ForEach-Object { npm install -g $_ }
```

### Step 5: Clone all repos + install dependencies

One script handles everything — clones all your repos (including sakhalteam org repos into a `sakhalteam/` subfolder) and runs the right install command for each:

```powershell
cd C:\Users\sakha\Code\reformat_helper
python clone_and_install.py
```

This clones and installs deps for:

| Repo | Manager | Deps |
|------|---------|------|
| sakhalteam/bird-bingo | npm | React, Vite, Tailwind |
| sakhalteam/japanese-articles | npm | React, Vite, Tailwind, react-markdown |
| sakhalteam/nikbeat | npm | React, Vite, Tailwind |
| sakhalteam/sakhalteam.github.io | npm | React, Vite, Three.js |
| sakhalteam/adhdo | — | (no deps) |
| aeroja | yarn | React, Vite, Tailwind, Adobe CEP |
| aether | yarn | React, Vite, Tailwind, shadcn, Adobe CEP |
| sakhaltai.github.io | npm | React, Vite, Tailwind |
| rodeo2024 | pip | spacy, selenium, beautifulsoup4 |
| adobe-scripts | — | (no deps) |
| ae_expressions | — | (no deps) |
| python_tools | — | (no deps) |

If you add new repos later, just edit the `REPOS` list in `clone_and_install.py`.

### Step 6: Install desktop apps

These need manual installers:

- [VS Code](https://code.visualstudio.com) (install first so the script can add extensions)
- [1Password](https://1password.com/downloads)
- [Discord](https://discord.com/download)
- [Figma](https://figma.com/downloads)
- [Slack](https://slack.com/downloads/windows)
- [Spotify](https://spotify.com/download)
- [Docker Desktop](https://docker.com/products/docker-desktop)
- [OBS Studio](https://obsproject.com) (+ input-overlay plugin)
- [Signal](https://signal.org/download)
- [Notion](https://notion.so/desktop)

### Step 7: Fonts

Restore from your Macrium backup image.

### Step 8: Verify

```powershell
git --version
python --version
node --version
npm --version
yarn --version
ffmpeg -version
yt-dlp --version
```

---

## Files in this repo

| File | Purpose |
|------|---------|
| `pre_reformat_audit.py` | Run before reformatting — scans everything and generates a report |
| `post_reformat_setup.py` | Run after reformatting (as admin) — installs dev toolchain |
| `clone_and_install.py` | Clones all repos and installs their dependencies |
| `vscode_extensions.txt` | Snapshot of your VS Code extensions |
| `gitconfig_template` | Your .gitconfig to restore |
| `.gitignore` | Keeps audit output out of the repo |
