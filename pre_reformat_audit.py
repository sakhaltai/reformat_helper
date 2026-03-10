r"""
Pre-reformat audit script.
Scans C:\Users\sakha\Code for git repos (and non-git dirs), checks for
uncommitted changes, stashes, local-only branches, important local files,
and also captures installed programs and critical user config paths.

Usage:
    cd C:\Users\sakha\Code\python_tools
    python reformat_audit.py
"""

import json
import os
import subprocess
import winreg
from pathlib import Path
from datetime import datetime

CODE_ROOT = Path(r"C:\Users\sakha\Code")
OUTPUT_DIR = Path(__file__).parent / "reformat_audit_output"
MAX_UNTRACKED_TO_SHOW = 25

IMPORTANT_FILE_PATTERNS = {
    ".env",
    ".env.local",
    ".env.development.local",
    ".env.production",
    ".npmrc",
    ".yarnrc",
    ".yarnrc.yml",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "config.local.json",
    "config.local.js",
    "config.local.ts",
}

# Only extensions that are almost always meaningful on their own.
# .json/.yaml/.yml excluded to avoid noise from package.json, tsconfig, etc.
IMPORTANT_EXTENSIONS = {
    ".env",
    ".pem",
    ".key",
    ".p12",
    ".sqlite",
    ".db",
    ".ps1",
    ".sh",
    ".bat",
    ".cmd",
}

IGNORE_DIR_NAMES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".cache",
    "__pycache__",
    ".venv",
    "venv",
    "coverage",
}

CRITICAL_USER_PATHS = [
    Path.home() / ".ssh",
    Path.home() / ".gitconfig",
    Path.home() / ".npmrc",
    Path.home() / ".gnupg",
    Path.home() / ".aws",
    Path.home() / ".azure",
    Path.home() / ".docker",
    Path.home() / ".claude",
    Path.home() / ".claude.json",
    Path.home() / ".conda",
    Path.home() / ".condarc",
    Path.home() / ".cursor",
    Path.home() / ".gradle",
    Path.home() / ".nuget",
    Path.home() / ".vscode",
    Path.home() / ".yarnrc",
    Path.home() / ".config",
    Path.home() / ".bash_history",
    Path.home() / ".1password",
]

# Standalone tools/folders that live directly in the user profile and would be
# missed by Program Files / registry scans.  These are things like ffmpeg,
# yt-dlp, anaconda, etc. that you manually dropped into your home folder.
STANDALONE_USER_TOOLS = [
    "ffmpeg-master-latest-win64-gpl",
    "yt-dlp",
    "yt-dlp.bat",
    "anaconda3",
    "blenderkit_data",
    "FontBase",
    "input-overlay",
    "pyinstaller",
    "pip",               # sometimes a standalone folder
    "Proton Drive",
]

# Notable AppData directories whose configs/data you may want to back up or
# at least remember to reinstall.
NOTABLE_APPDATA_DIRS = {
    # AppData/Roaming
    "Roaming": [
        "1Password", "Code", "Cursor", "Discord", "Docker", "Figma",
        "FontBase", "GitHub Desktop", "HandBrake", "Mozilla", "Notion",
        "Obsidian", "Signal", "Slack", "Spotify", "Voicemod",
        "NuGet", "nvm", "Python",
    ],
    # AppData/Local
    "Local": [
        "1Password", "Battle.net", "Discord", "Docker", "Figma",
        "Google", "Jellyfin Media Player", "LGHUB", "MongoDB",
        "MongoDBCompass", "Obsidian", "Plex Media Server", "Steam",
        "Spotify", "Toggl Track", "Zoom", "deno", "pnpm", "pnpm-cache",
        "node", "npm-cache", "Yarn", "claude-cli-nodejs",
        "DaVinci Resolve", "Epic Games", "Unreal Engine",
    ],
}


def run(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=False,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, "", str(e)


def safe_lines(text):
    if not text:
        return []
    return [line for line in text.splitlines() if line.strip()]


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def find_git_repos(root: Path):
    repos = []
    if not root.exists():
        return repos
    for current_root, dirs, _files in os.walk(root):
        current_path = Path(current_root)
        if ".git" in dirs:
            repos.append(current_path)
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in IGNORE_DIR_NAMES]
    return sorted(repos, key=lambda p: str(p).lower())


def find_non_git_dirs(root: Path, git_repos: list):
    """Find top-level children of root that are NOT inside any discovered git repo."""
    repo_set = set(git_repos)
    non_git = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and child.name not in IGNORE_DIR_NAMES and child not in repo_set:
            # also skip if child is a parent *of* a repo (like sakhalteam/)
            is_parent_of_repo = any(str(r).startswith(str(child)) for r in repo_set)
            if not is_parent_of_repo:
                non_git.append(child)
    return non_git


def dir_summary(path: Path, max_files=50):
    """Quick summary of a non-git directory: total size and file listing."""
    files = []
    total_size = 0
    for current_root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIR_NAMES]
        for f in filenames:
            fp = Path(current_root) / f
            try:
                sz = fp.stat().st_size
            except OSError:
                sz = 0
            total_size += sz
            if len(files) < max_files:
                files.append({"path": str(fp.relative_to(path)), "size_bytes": sz})
    return {
        "path": str(path),
        "name": path.name,
        "total_size_bytes": total_size,
        "total_size_human": _human_size(total_size),
        "files_sample": files,
        "truncated": len(files) >= max_files,
    }


def _human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def git_output(repo: Path, *args):
    return run(["git", *args], cwd=repo)


def find_important_local_files(repo: Path, limit=50):
    hits = []
    for current_root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIR_NAMES]
        for file in files:
            p = Path(current_root) / file
            rel = p.relative_to(repo)
            name_lower = p.name.lower()

            if name_lower in IMPORTANT_FILE_PATTERNS:
                hits.append(str(rel))
                continue

            if p.suffix.lower() in IMPORTANT_EXTENSIONS:
                rel_str = str(rel).lower()
                if any(part in rel_str for part in ("node_modules", ".git", "dist", "build")):
                    continue
                hits.append(str(rel))

            if len(hits) >= limit:
                return hits
    return hits


def summarize_repo(repo: Path):
    data = {
        "name": repo.name,
        "path": str(repo),
        "branch": None,
        "remote_urls": [],
        "status_porcelain": [],
        "has_uncommitted_changes": False,
        "untracked_files": [],
        "local_only_commits": [],
        "local_only_branches": [],
        "stashes": [],
        "important_local_files": [],
        "package_hints": [],
        "errors": [],
    }

    # Current branch
    rc, out, err = git_output(repo, "branch", "--show-current")
    if rc == 0:
        data["branch"] = out.strip() or "(detached)"
    else:
        data["errors"].append(f"branch: {err or out}")

    # Remotes
    rc, out, err = git_output(repo, "remote", "-v")
    if rc == 0:
        seen = set()
        for line in safe_lines(out):
            remote_url = " ".join(line.split())
            if remote_url not in seen:
                seen.add(remote_url)
                data["remote_urls"].append(remote_url)
    else:
        data["errors"].append(f"remote -v: {err or out}")

    # Status
    rc, out, err = git_output(repo, "status", "--porcelain")
    if rc == 0:
        lines = safe_lines(out)
        data["status_porcelain"] = lines
        data["has_uncommitted_changes"] = len(lines) > 0
        data["untracked_files"] = [line[3:] for line in lines if line.startswith("?? ")]
    else:
        data["errors"].append(f"status: {err or out}")

    # Local-only commits (not pushed)
    rc, out, err = git_output(repo, "log", "--branches", "--not", "--remotes", "--oneline")
    if rc == 0:
        data["local_only_commits"] = safe_lines(out)
    elif err or out:
        data["errors"].append(f"local-only commits: {err or out}")

    # Local-only branches (no upstream tracking)
    rc, out, err = git_output(repo, "branch", "-vv")
    if rc == 0:
        for line in safe_lines(out):
            # Branches with a remote show [origin/...] — those without have no brackets
            stripped = line.lstrip("* ").strip()
            if stripped and "[" not in stripped:
                branch_name = stripped.split()[0]
                data["local_only_branches"].append(branch_name)

    # Stashes
    rc, out, err = git_output(repo, "stash", "list")
    if rc == 0:
        data["stashes"] = safe_lines(out)

    # Important local files
    data["important_local_files"] = find_important_local_files(repo)

    # Package manager hints
    for marker in [
        "package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json",
        "requirements.txt", "pyproject.toml", "Cargo.toml",
    ]:
        if (repo / marker).exists():
            data["package_hints"].append(marker)

    return data


# ---------------------------------------------------------------------------
# Installed programs (Windows registry)
# ---------------------------------------------------------------------------

def read_uninstall_key(root, path):
    apps = []
    try:
        key = winreg.OpenKey(root, path)
    except FileNotFoundError:
        return apps
    try:
        count = winreg.QueryInfoKey(key)[0]
        for i in range(count):
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
            except OSError:
                continue

            def get_value(name):
                try:
                    value, _ = winreg.QueryValueEx(subkey, name)
                    return value
                except FileNotFoundError:
                    return None

            display_name = get_value("DisplayName")
            if not display_name:
                continue
            apps.append({
                "name": display_name,
                "version": get_value("DisplayVersion"),
                "publisher": get_value("Publisher"),
                "install_location": get_value("InstallLocation"),
            })
    except OSError:
        pass
    return apps


def get_installed_programs():
    uninstall_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    programs = []
    for root, path in uninstall_paths:
        programs.extend(read_uninstall_key(root, path))

    seen = set()
    deduped = []
    for app in programs:
        key = (app["name"], app.get("version"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(app)
    return sorted(deduped, key=lambda x: x["name"].lower())


def get_winget_list():
    """Capture full winget list output as a string for the report."""
    rc, out, err = run(["winget", "list", "--disable-interactivity"])
    if rc == 0:
        return out
    return None


# ---------------------------------------------------------------------------
# Critical user paths
# ---------------------------------------------------------------------------

def check_critical_paths():
    found = []
    for p in CRITICAL_USER_PATHS:
        if p.exists():
            found.append(str(p))
    return found


# ---------------------------------------------------------------------------
# Standalone user-profile tools
# ---------------------------------------------------------------------------

def find_standalone_tools():
    """Find tools/folders dropped directly into the user home directory."""
    found = []
    home = Path.home()
    for name in STANDALONE_USER_TOOLS:
        p = home / name
        if p.exists():
            kind = "dir" if p.is_dir() else "file"
            size = 0
            if p.is_file():
                size = p.stat().st_size
            elif p.is_dir():
                try:
                    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                except OSError:
                    pass
            found.append({"name": name, "path": str(p), "type": kind, "size_human": _human_size(size)})
    return found


# ---------------------------------------------------------------------------
# Notable AppData directories
# ---------------------------------------------------------------------------

def find_notable_appdata():
    """Check which notable AppData dirs exist (things to reinstall/back up)."""
    appdata = Path.home() / "AppData"
    found = []
    for location, names in NOTABLE_APPDATA_DIRS.items():
        base = appdata / location
        for name in names:
            p = base / name
            if p.exists():
                found.append({"name": name, "location": location, "path": str(p)})
    return sorted(found, key=lambda x: x["name"].lower())


# ---------------------------------------------------------------------------
# Package manager snapshots
# ---------------------------------------------------------------------------

def get_choco_list():
    """Capture chocolatey package list."""
    rc, out, err = run(["choco", "list", "--local-only"])
    if rc == 0:
        return out
    return None


def get_conda_envs():
    """List conda environments."""
    rc, out, err = run(["conda", "env", "list"])
    if rc == 0:
        return out
    return None


def get_nvm_list():
    """List nvm-managed node versions."""
    rc, out, err = run(["nvm", "list"])
    if rc == 0:
        return out
    return None


def get_pip_global_packages():
    """Capture pip list for global Python."""
    rc, out, err = run(["pip", "list", "--format=columns"])
    if rc == 0:
        return out
    return None


def get_python_locations():
    """Find all python.exe on PATH."""
    rc, out, err = run(["where", "python"])
    if rc == 0:
        return safe_lines(out)
    return []


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def make_markdown(report):
    lines = []
    lines.append("# Reformat Audit Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")

    # ----- Summary -----
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Code root: `{report['code_root']}`")
    lines.append(f"- Git repos found: **{len(report['repos'])}**")
    lines.append(f"- Non-git directories: **{len(report['non_git_dirs'])}**")
    lines.append(f"- Installed programs found: **{len(report['installed_programs'])}**")
    lines.append("")

    # ----- Critical user config -----
    if report.get("critical_user_files"):
        lines.append("## Critical User Config (BACK THESE UP)")
        lines.append("")
        for p in report["critical_user_files"]:
            lines.append(f"- `{p}`")
        lines.append("")

    # ----- Attention items -----
    dirty = [r for r in report["repos"] if r["has_uncommitted_changes"]]
    local_only = [r for r in report["repos"] if r["local_only_commits"]]
    no_remote = [r for r in report["repos"] if not r["remote_urls"]]
    has_stashes = [r for r in report["repos"] if r["stashes"]]
    has_local_branches = [r for r in report["repos"] if r["local_only_branches"]]

    lines.append("## Immediate Attention")
    lines.append("")
    lines.append(f"- Repos with uncommitted changes: **{len(dirty)}**")
    lines.append(f"- Repos with local-only commits (not pushed): **{len(local_only)}**")
    lines.append(f"- Repos with local-only branches (no upstream): **{len(has_local_branches)}**")
    lines.append(f"- Repos with stashes: **{len(has_stashes)}**")
    lines.append(f"- Repos with no remote configured: **{len(no_remote)}**")
    lines.append(f"- Non-git directories (NO remote backup at all): **{len(report['non_git_dirs'])}**")
    lines.append("")

    if dirty:
        lines.append("### Dirty repos (uncommitted changes)")
        lines.append("")
        for repo in dirty:
            lines.append(f"- `{repo['name']}` — `{repo['path']}`")
        lines.append("")

    if has_stashes:
        lines.append("### Repos with stashes (WILL BE LOST)")
        lines.append("")
        for repo in has_stashes:
            lines.append(f"- `{repo['name']}`:")
            for s in repo["stashes"]:
                lines.append(f"  - {s}")
        lines.append("")

    if has_local_branches:
        lines.append("### Repos with local-only branches (no upstream)")
        lines.append("")
        for repo in has_local_branches:
            lines.append(f"- `{repo['name']}`:")
            for b in repo["local_only_branches"]:
                lines.append(f"  - `{b}`")
        lines.append("")

    if local_only:
        lines.append("### Repos with local-only commits (not pushed)")
        lines.append("")
        for repo in local_only:
            lines.append(f"- `{repo['name']}`:")
            for commit in repo["local_only_commits"][:10]:
                lines.append(f"  - {commit}")
        lines.append("")

    if no_remote:
        lines.append("### Repos with no remote")
        lines.append("")
        for repo in no_remote:
            lines.append(f"- `{repo['name']}` — `{repo['path']}`")
        lines.append("")

    # ----- Non-git directories -----
    if report["non_git_dirs"]:
        lines.append("## Non-Git Directories (NO remote backup)")
        lines.append("")
        for d in report["non_git_dirs"]:
            lines.append(f"### {d['name']}")
            lines.append(f"- Path: `{d['path']}`")
            lines.append(f"- Total size: **{d['total_size_human']}**")
            if d["files_sample"]:
                lines.append(f"- Files ({len(d['files_sample'])}{'+ truncated' if d['truncated'] else ''}):")
                for f in d["files_sample"]:
                    lines.append(f"  - `{f['path']}` ({_human_size(f['size_bytes'])})")
            lines.append("")

    # ----- Repo details -----
    lines.append("## Repo Details")
    lines.append("")
    for repo in report["repos"]:
        lines.append(f"### {repo['name']}")
        lines.append("")
        lines.append(f"- Path: `{repo['path']}`")
        lines.append(f"- Branch: `{repo['branch']}`")
        lines.append(f"- Has uncommitted changes: **{repo['has_uncommitted_changes']}**")
        lines.append(f"- Stashes: **{len(repo['stashes'])}**")
        lines.append(f"- Local-only branches: {', '.join(f'`{b}`' for b in repo['local_only_branches']) or 'none'}")
        lines.append(f"- Package hints: {', '.join(repo['package_hints']) if repo['package_hints'] else 'none'}")

        if repo["remote_urls"]:
            lines.append("- Remotes:")
            for r in repo["remote_urls"]:
                lines.append(f"  - `{r}`")
        else:
            lines.append("- Remotes: **NONE**")

        if repo["untracked_files"]:
            lines.append(f"- Untracked files ({len(repo['untracked_files'])}):")
            for item in repo["untracked_files"][:MAX_UNTRACKED_TO_SHOW]:
                lines.append(f"  - `{item}`")
            if len(repo["untracked_files"]) > MAX_UNTRACKED_TO_SHOW:
                lines.append(f"  - ... and {len(repo['untracked_files']) - MAX_UNTRACKED_TO_SHOW} more")

        if repo["important_local_files"]:
            lines.append(f"- Important-looking local files ({len(repo['important_local_files'])}):")
            for item in repo["important_local_files"][:MAX_UNTRACKED_TO_SHOW]:
                lines.append(f"  - `{item}`")
            if len(repo["important_local_files"]) > MAX_UNTRACKED_TO_SHOW:
                lines.append(f"  - ... and {len(repo['important_local_files']) - MAX_UNTRACKED_TO_SHOW} more")

        if repo["errors"]:
            lines.append("- Errors:")
            for e in repo["errors"]:
                lines.append(f"  - {e}")

        lines.append("")

    # ----- Installed programs -----
    lines.append("## Installed Programs")
    lines.append("")
    for app in report["installed_programs"]:
        version = f" ({app['version']})" if app.get("version") else ""
        publisher = f" — {app['publisher']}" if app.get("publisher") else ""
        lines.append(f"- {app['name']}{version}{publisher}")
    lines.append("")

    # ----- Standalone tools -----
    if report.get("standalone_tools"):
        lines.append("## Standalone Tools in User Profile")
        lines.append("")
        lines.append("These live directly in your home folder and won't show up in Program Files or registry scans.")
        lines.append("")
        for tool in report["standalone_tools"]:
            lines.append(f"- `{tool['name']}` — {tool['type']}, {tool['size_human']} — `{tool['path']}`")
        lines.append("")

    # ----- Notable AppData -----
    if report.get("notable_appdata"):
        lines.append("## Notable AppData Directories (apps to reinstall)")
        lines.append("")
        for item in report["notable_appdata"]:
            lines.append(f"- **{item['name']}** (`AppData\\{item['location']}`)")
        lines.append("")

    # ----- Python installs -----
    if report.get("python_locations"):
        lines.append("## Python Installations on PATH")
        lines.append("")
        for loc in report["python_locations"]:
            lines.append(f"- `{loc}`")
        lines.append("")

    # ----- Checklist -----
    lines.append("## Pre-Reformat Checklist")
    lines.append("")
    lines.append("### Git / Code")
    lines.append("- [ ] Commit and push all dirty repos")
    lines.append("- [ ] Apply/commit or accept loss of all stashes")
    lines.append("- [ ] Push all local-only branches")
    lines.append("- [ ] Back up non-git directories to external drive")
    lines.append("")
    lines.append("### Credentials & Config")
    lines.append("- [ ] Back up `C:\\Users\\sakha\\.ssh`")
    lines.append("- [ ] Back up `C:\\Users\\sakha\\.gitconfig`")
    lines.append("- [ ] Back up `C:\\Users\\sakha\\.aws`")
    lines.append("- [ ] Back up `C:\\Users\\sakha\\.azure`")
    lines.append("- [ ] Back up `C:\\Users\\sakha\\.claude` and `.claude.json`")
    lines.append("- [ ] Confirm password manager + 2FA recovery access")
    lines.append("")
    lines.append("### Browsers & Apps")
    lines.append("- [ ] Export browser bookmarks")
    lines.append("- [ ] Save/export VS Code settings & extensions list (`code --list-extensions`)")
    lines.append("- [ ] Save/export Cursor settings & extensions")
    lines.append("- [ ] Note any Figma local files / fonts")
    lines.append("- [ ] Export OBS / input-overlay configs if customized")
    lines.append("")
    lines.append("### Standalone Tools (easy to forget!)")
    lines.append("- [ ] Note ffmpeg location / version for reinstall")
    lines.append("- [ ] Note yt-dlp (reinstall via choco, pip, or standalone)")
    lines.append("- [ ] Reinstall Chocolatey + packages (see choco_list.txt)")
    lines.append("- [ ] Reinstall NVM + node versions (see nvm_list.txt)")
    lines.append("- [ ] Reinstall Anaconda / conda envs (see conda_envs.txt)")
    lines.append("- [ ] Reinstall global pip packages (see pip_global_packages.txt)")
    lines.append("- [ ] Note multiple Python install locations")
    lines.append("")
    lines.append("### Data & Media")
    lines.append("- [ ] Back up Desktop files")
    lines.append("- [ ] Back up Documents")
    lines.append("- [ ] Back up Downloads (anything you want to keep)")
    lines.append("- [ ] Back up Proton Drive local sync folder if needed")
    lines.append("- [ ] Back up any BlenderKit assets you want to keep")
    lines.append("- [ ] Back up FontBase custom font collections")
    lines.append("")
    lines.append("### Final Verification")
    lines.append("- [ ] Verify backup contents open correctly on external drive")
    lines.append("- [ ] Save this report to the external drive too")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Scanning git repos...")
    git_repos = find_git_repos(CODE_ROOT)
    repos = [summarize_repo(repo) for repo in git_repos]

    print("Scanning non-git directories...")
    non_git_paths = find_non_git_dirs(CODE_ROOT, git_repos)
    non_git_dirs = [dir_summary(p) for p in non_git_paths]

    print("Reading installed programs from registry...")
    installed_programs = get_installed_programs()

    print("Capturing winget list...")
    winget_output = get_winget_list()

    print("Checking critical user config paths...")
    critical_files = check_critical_paths()

    print("Scanning for standalone tools in user profile...")
    standalone_tools = find_standalone_tools()

    print("Scanning notable AppData directories...")
    notable_appdata = find_notable_appdata()

    print("Capturing chocolatey packages...")
    choco_output = get_choco_list()

    print("Capturing conda environments...")
    conda_output = get_conda_envs()

    print("Capturing nvm node versions...")
    nvm_output = get_nvm_list()

    print("Capturing global pip packages...")
    pip_output = get_pip_global_packages()

    print("Finding Python installations...")
    python_locations = get_python_locations()

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "code_root": str(CODE_ROOT),
        "repos": repos,
        "non_git_dirs": non_git_dirs,
        "installed_programs": installed_programs,
        "critical_user_files": critical_files,
        "standalone_tools": standalone_tools,
        "notable_appdata": notable_appdata,
        "python_locations": python_locations,
    }

    json_path = OUTPUT_DIR / "reformat_report.json"
    md_path = OUTPUT_DIR / "reformat_report.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(make_markdown(report), encoding="utf-8")

    if winget_output:
        winget_path = OUTPUT_DIR / "winget_list.txt"
        winget_path.write_text(winget_output, encoding="utf-8")
        print(f"Wrote: {winget_path}")

    if choco_output:
        choco_path = OUTPUT_DIR / "choco_list.txt"
        choco_path.write_text(choco_output, encoding="utf-8")
        print(f"Wrote: {choco_path}")

    if conda_output:
        conda_path = OUTPUT_DIR / "conda_envs.txt"
        conda_path.write_text(conda_output, encoding="utf-8")
        print(f"Wrote: {conda_path}")

    if nvm_output:
        nvm_path = OUTPUT_DIR / "nvm_list.txt"
        nvm_path.write_text(nvm_output, encoding="utf-8")
        print(f"Wrote: {nvm_path}")

    if pip_output:
        pip_path = OUTPUT_DIR / "pip_global_packages.txt"
        pip_path.write_text(pip_output, encoding="utf-8")
        print(f"Wrote: {pip_path}")

    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(f"\nDone! Open {md_path} for the full report.")


if __name__ == "__main__":
    main()
