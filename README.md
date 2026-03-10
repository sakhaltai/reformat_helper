# Reformat Helper

Scripts to make Windows reformats painless. Run the pre-reformat audit before wiping, then clone this repo on the fresh install and run the post-reformat setup.

## Before reformatting

```powershell
python pre_reformat_audit.py
```

This scans your `C:\Users\sakha\Code` for dirty repos, unpushed work, standalone tools (ffmpeg, yt-dlp, etc.), AppData configs, installed programs, and generates a full report with a checklist.

Output goes to `reformat_audit_output/` (gitignored).

## After reformatting

1. Install Python from [python.org](https://www.python.org/downloads/) (or download from your backup)
2. Clone this repo:
   ```powershell
   git clone https://github.com/sakhaltai/reformat_helper.git
   cd reformat_helper
   ```
3. Run the setup script **as Administrator**:
   ```powershell
   python post_reformat_setup.py
   ```

### What the post-reformat script installs

| Tool | How | Why |
|------|-----|-----|
| Chocolatey | PowerShell installer | Package manager for Windows |
| Git + Git LFS | `choco install` | Version control (your repos use LFS) |
| ffmpeg | `choco install` | Audio/video processing |
| yt-dlp | `choco install` | Video downloader |
| Python + pip | `choco install` | Python dev |
| NVM for Windows | `choco install` | Manages Node.js versions |
| Node.js LTS | `nvm install lts` | JavaScript runtime |
| Yarn | `npm install -g` | Package manager (aeroja, aether use it) |
| VS Code extensions | `code --install-extension` | All 65 extensions from your current setup |
| .gitconfig | File copy | Your git user config + LFS setup |

### What it does NOT install

- **Anaconda** — 20GB and none of your projects use conda envs
- **pnpm** — no projects use it
- **Desktop apps** — the script prints a list of links for manual install (Discord, Figma, 1Password, etc.)

## Files

- `pre_reformat_audit.py` — Run before reformatting
- `post_reformat_setup.py` — Run after reformatting (as admin)
- `vscode_extensions.txt` — Snapshot of your VS Code extensions
- `gitconfig_template` — Your .gitconfig to restore
