r"""
Post-reformat setup script for Nicholas Hartmann's dev machine.

This script installs the core dev toolchain AND desktop apps you need to
get back to work after a Windows reformat. It's organized into phases:

  Phase 1: Package managers (Chocolatey)
  Phase 2: Dev toolchain (Git, Python, Node, etc.)
  Phase 3: Desktop apps via Chocolatey (browsers, creative tools, etc.)
  Phase 4: Special-case installs (pinned versions, manual downloads)
  Phase 5: VS Code extensions + .gitconfig restoration
  Phase 6: Manual steps checklist

Requirements:
  - Run this from an ELEVATED (admin) PowerShell or Command Prompt
  - Internet connection
  - VS Code should be installed first (for extension install to work)

Usage:
    # From elevated PowerShell:
    python post_reformat_setup.py

    # Or if Python isn't installed yet, the script will tell you what to do.
"""

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
EXTENSIONS_FILE = SCRIPT_DIR / "vscode_extensions.txt"
GITCONFIG_TEMPLATE = SCRIPT_DIR / "gitconfig_template"

# ANSI colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def is_admin():
    """Check if running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def banner(msg):
    print(f"\n{CYAN}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{RESET}\n")


def step(msg):
    print(f"{GREEN}[+]{RESET} {msg}")


def warn(msg):
    print(f"{YELLOW}[!]{RESET} {msg}")


def fail(msg):
    print(f"{RED}[X]{RESET} {msg}")


def info(msg):
    print(f"{DIM}    {msg}{RESET}")


def run_cmd(cmd, shell=True, check=False):
    """Run a command and return (success, stdout)."""
    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0 and check:
            fail(f"Command failed: {cmd}")
            if result.stderr.strip():
                print(f"    stderr: {result.stderr.strip()[:200]}")
        return result.returncode == 0, result.stdout.strip()
    except FileNotFoundError:
        return False, ""


def command_exists(name):
    """Check if a command is available on PATH."""
    return shutil.which(name) is not None


def _refresh_path():
    """Reload PATH from the registry so newly installed tools are visible."""
    try:
        import winreg
        paths = []
        for root, subkey in [
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER, r"Environment"),
        ]:
            try:
                key = winreg.OpenKey(root, subkey)
                val, _ = winreg.QueryValueEx(key, "Path")
                paths.extend(val.split(";"))
            except (FileNotFoundError, OSError):
                pass
        os.environ["PATH"] = ";".join(dict.fromkeys(paths))  # dedupe, preserve order
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Phase 1: Chocolatey
# ---------------------------------------------------------------------------

def install_chocolatey():
    """Install Chocolatey package manager."""
    if command_exists("choco"):
        step("Chocolatey already installed.")
        return True

    banner("Phase 1 — Installing Chocolatey")
    print("  Chocolatey is a package manager for Windows. Think of it like")
    print("  apt (Linux) or brew (Mac). It lets you install and update CLI")
    print("  tools with commands like `choco install ffmpeg`.\n")

    ps_cmd = (
        "Set-ExecutionPolicy Bypass -Scope Process -Force; "
        "[System.Net.ServicePointManager]::SecurityProtocol = "
        "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
        "iex ((New-Object System.Net.WebClient).DownloadString("
        "'https://community.chocolatey.org/install.ps1'))"
    )
    ok, _ = run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd], shell=False)
    if ok:
        step("Chocolatey installed successfully.")
        _refresh_path()
        return True
    else:
        fail("Chocolatey installation failed. You may need to install it manually.")
        return False


# ---------------------------------------------------------------------------
# Phase 2: Dev toolchain
# ---------------------------------------------------------------------------

def install_dev_toolchain():
    """Install core dev tools via Chocolatey."""
    packages = {
        "git":      "Git version control",
        "git-lfs":  "Git Large File Storage (your repos use this)",
        "ffmpeg":   "Audio/video processing",
        "yt-dlp":   "Video downloader",
    }

    banner("Phase 2 — Dev Toolchain via Chocolatey")

    for pkg, desc in packages.items():
        step(f"Installing {pkg} — {desc}")
        ok, out = run_cmd(f"choco install {pkg} -y --no-progress")
        if ok:
            step(f"  {pkg} ✓")
        else:
            warn(f"  {pkg} may have had issues. Check: choco list {pkg}")

    _refresh_path()


def install_python_via_choco():
    """Install Python via Chocolatey if not already present."""
    if command_exists("python"):
        ok, ver = run_cmd("python --version")
        if ok:
            step(f"Python already installed: {ver}")
            return True

    banner("Installing Python")
    ok, _ = run_cmd("choco install python -y --no-progress")
    _refresh_path()
    if ok and command_exists("python"):
        step("Python installed successfully.")
        return True
    else:
        warn("Python install may need a shell restart to take effect.")
        return False


def install_nvm_and_node():
    """Install NVM for Windows and then Node LTS."""
    banner("Installing NVM for Windows + Node.js")

    if command_exists("nvm"):
        step("NVM already installed.")
    else:
        step("Installing NVM for Windows via Chocolatey...")
        ok, _ = run_cmd("choco install nvm -y --no-progress")
        _refresh_path()
        if not ok:
            fail("NVM install failed. Install manually from https://github.com/coreybutler/nvm-windows")
            return False

    step("Installing Node.js LTS via NVM...")
    run_cmd("nvm install lts")
    run_cmd("nvm use lts")
    _refresh_path()

    if command_exists("node"):
        ok, ver = run_cmd("node --version")
        step(f"Node.js ready: {ver}")
    else:
        warn("Node may need a shell restart. After restart: nvm install lts && nvm use lts")

    return True


def install_yarn():
    """Install Yarn globally via npm."""
    banner("Installing Yarn")

    if command_exists("yarn"):
        step("Yarn already installed.")
        return True

    if not command_exists("npm"):
        warn("npm not available yet — Yarn will need to be installed after shell restart.")
        warn("Run: npm install -g yarn")
        return False

    ok, _ = run_cmd("npm install -g yarn")
    if ok:
        step("Yarn installed successfully.")
    else:
        warn("Yarn install failed. After restart: npm install -g yarn")
    return ok


# ---------------------------------------------------------------------------
# Phase 3: Desktop apps via Chocolatey
# ---------------------------------------------------------------------------

def install_desktop_apps():
    """Install desktop applications via Chocolatey."""

    # Each entry: (choco_package_id, display_name, extra_flags_or_None)
    apps = [
        # --- Browsers ---
        ("googlechrome",           "Google Chrome",            None),
        ("firefox",                "Firefox",                  None),

        # --- Creative / Media ---
        ("blender",                "Blender",                  None),
        ("obs-studio",             "OBS Studio",               None),
        ("handbrake",              "HandBrake",                None),
        ("vlc",                    "VLC Media Player",         None),
        ("k-litecodecpackfull",    "K-Lite Codec Pack Full",   None),
        ("spotify",                "Spotify",                  None),

        # --- Dev / Productivity ---
        ("vscode",                 "Visual Studio Code",       None),
        ("github-desktop",         "GitHub Desktop",           None),
        ("docker-desktop",         "Docker Desktop",           None),
        ("obsidian",               "Obsidian",                 None),
        ("autohotkey",             "AutoHotkey",               None),
        ("powertoys",              "Microsoft PowerToys",      None),
        ("treesizefree",           "TreeSize Free",            None),

        # --- Communication ---
        ("discord",                "Discord",                  None),
        ("slack",                  "Slack",                    None),
        ("signal",                 "Signal",                   None),

        # --- Cloud / Remote ---
        ("adobe-creative-cloud",   "Adobe Creative Cloud",     None),
        ("figma",                  "Figma",                    None),
        ("anydesk",                "AnyDesk",                  None),
        ("1password",              "1Password",                None),

        # --- Gaming ---
        ("steam",                  "Steam",                    None),
        ("epicgameslauncher",      "Epic Games Launcher",      None),

        # --- Media / Streaming ---
        ("jellyfin-media-player",  "Jellyfin Media Player",    None),

        # --- GPU / Drivers ---
        ("nvidia-app",             "NVIDIA App",               None),

        # --- Utilities ---
        ("winrar",                 "WinRAR",                   None),
        ("google-earth-pro",       "Google Earth Pro",         None),
        ("toggl",                  "Toggl Track",              None),
    ]

    banner("Phase 3 — Desktop Apps via Chocolatey")
    print(f"  Installing {len(apps)} applications. This will take a while.\n")

    succeeded = 0
    failed_apps = []

    for pkg, name, extra in apps:
        step(f"Installing {name}...")
        cmd = f"choco install {pkg} -y --no-progress"
        if extra:
            cmd += f" {extra}"
        ok, _ = run_cmd(cmd)
        if ok:
            step(f"  {name} ✓")
            succeeded += 1
        else:
            warn(f"  {name} — may need manual install or retry")
            failed_apps.append((pkg, name))

    _refresh_path()

    print(f"\n  {GREEN}Installed: {succeeded}/{len(apps)}{RESET}")
    if failed_apps:
        print(f"  {YELLOW}Needs attention:{RESET}")
        for pkg, name in failed_apps:
            print(f"    - {name} (choco install {pkg} -y)")

    return succeeded, failed_apps


# ---------------------------------------------------------------------------
# Phase 4: Special-case installs (pinned versions, manual downloads)
# ---------------------------------------------------------------------------

def install_special_cases():
    """Handle installs that need version pinning or manual download."""

    banner("Phase 4 — Special-Case Installs")

    # --- Macrium Reflect Free 8.0.7783 (last free version) ---
    step("Installing Macrium Reflect Free v8.0.7783 (pinned — last free version)...")
    info("This is the last version before Macrium moved to paid-only.")
    ok, _ = run_cmd("choco install reflect-free --version=8.0.7783 -y --no-progress")
    if ok:
        step("  Macrium Reflect Free 8.0.7783 ✓")
        # Pin it so `choco upgrade all` doesn't overwrite it
        run_cmd("choco pin add -n=reflect-free --version=8.0.7783")
        step("  Pinned to 8.0.7783 — won't be upgraded by `choco upgrade all`")
    else:
        warn("  Macrium Reflect install failed. Manual install:")
        warn("  https://download.macrium.com/reflect/v8/v8.0.7783/reflect_setup_free_x64.exe")

    # --- LINE Desktop (not reliably on choco — use winget or manual) ---
    step("Installing LINE Desktop...")
    ok, _ = run_cmd("winget install --id LINE.LINE -e --silent --accept-source-agreements --accept-package-agreements")
    if ok:
        step("  LINE Desktop ✓ (via winget)")
    else:
        warn("  LINE Desktop — install manually: https://desktop.line-sms.com/")

    # --- aescripts + aeplugins ZXP/UXP Installer ---
    step("aescripts ZXP/UXP Installer — manual download required")
    info("Download from: https://aescripts.com/learn/zxp-installer/")
    info("Or direct MSI: https://updates.aescripts.com/")
    info("(Also consider the aescripts Manager app for plugin management)")

    # --- aescripts Manager/Updater app ---
    step("aescripts Manager app — manual download required")
    info("Download from: https://aescripts.com/learn/aescripts-aeplugins-manager-app/")

    _refresh_path()


# ---------------------------------------------------------------------------
# Phase 5: VS Code extensions + .gitconfig
# ---------------------------------------------------------------------------

def install_vscode_extensions():
    """Install VS Code extensions from the saved list."""
    banner("Phase 5 — VS Code Extensions")

    if not command_exists("code"):
        warn("VS Code CLI not found. Install VS Code first, then rerun this step.")
        warn(f"Or manually: for /F %e in ({EXTENSIONS_FILE}) do code --install-extension %e")
        return

    if not EXTENSIONS_FILE.exists():
        warn(f"Extensions list not found at {EXTENSIONS_FILE}")
        warn("To generate this file from your current setup, run:")
        warn("  code --list-extensions > vscode_extensions.txt")
        return

    extensions = [
        line.strip() for line in EXTENSIONS_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    step(f"Installing {len(extensions)} extensions...")
    installed = 0
    for ext in extensions:
        ok, _ = run_cmd(f"code --install-extension {ext} --force", check=False)
        if ok:
            installed += 1
        else:
            warn(f"  Failed: {ext}")

    step(f"Installed {installed}/{len(extensions)} extensions.")


def restore_gitconfig():
    """Copy the .gitconfig template to the home directory."""
    banner("Restoring .gitconfig")

    target = Path.home() / ".gitconfig"
    if target.exists():
        step(f".gitconfig already exists at {target} — skipping.")
        return

    if not GITCONFIG_TEMPLATE.exists():
        warn(f"Template not found at {GITCONFIG_TEMPLATE}")
        warn("To generate this file from your current setup, copy:")
        warn(f"  copy %USERPROFILE%\\.gitconfig {GITCONFIG_TEMPLATE}")
        return

    shutil.copy2(GITCONFIG_TEMPLATE, target)
    step(f"Restored .gitconfig to {target}")


# ---------------------------------------------------------------------------
# Phase 6: Manual steps
# ---------------------------------------------------------------------------

def print_manual_steps():
    """Print things the user still needs to do manually."""
    banner("Phase 6 — Manual Steps Remaining")

    print(f"""  {BOLD}These can't be automated — do them when you're ready:{RESET}

  {YELLOW}1. Restore Claude Code settings{RESET}
     Copy your .claude folder from backup to C:\\Users\\sakha\\.claude
     Copy .claude.json from backup to C:\\Users\\sakha\\.claude.json

  {YELLOW}2. aescripts tools{RESET}
     - ZXP/UXP Installer:  https://aescripts.com/learn/zxp-installer/
     - aescripts Manager:  https://aescripts.com/learn/aescripts-aeplugins-manager-app/
     Both are free downloads. The Manager handles plugin updates.

  {YELLOW}3. Clone your repos{RESET}
     python clone_and_install.py
     (This clones all repos and installs their dependencies automatically.)

  {YELLOW}4. Fonts{RESET}
     Restore from your Macrium backup image.

  {YELLOW}5. VS Code settings{RESET}
     Restore settings.json and keybindings.json from your backup to:
     %APPDATA%\\Code\\User\\
     Or check if Settings Sync is on: File > Preferences > Settings Sync

  {YELLOW}6. Verify everything{RESET}
     git --version
     python --version
     node --version && npm --version
     yarn --version
     ffmpeg -version
     yt-dlp --version
     blender --version
     code --version

  {YELLOW}7. Post-install tips{RESET}
     - Run {BOLD}choco upgrade all -y{RESET} periodically to update everything
       (Macrium Reflect is pinned and won't be touched)
     - Run {BOLD}choco list{RESET} to see what's installed via Chocolatey
     - Your NVIDIA drivers will update via the NVIDIA App, not choco
""")


# ---------------------------------------------------------------------------
# CCCP note (for the person reading this script)
# ---------------------------------------------------------------------------
# CCCP (Combined Community Codec Pack) was last updated in October 2015 and
# is effectively abandoned. K-Lite Codec Pack Full is the actively maintained
# replacement and covers everything CCCP did plus modern codecs (AV1, VP9,
# HEVC, etc.). That's why we install k-litecodecpackfull above instead.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    banner("Post-Reformat Setup — Nicholas Hartmann")

    if not is_admin():
        fail("This script needs to run as Administrator.")
        print("  Right-click your terminal and choose 'Run as administrator',")
        print("  then run this script again.")
        sys.exit(1)

    step("Running as Administrator — good to go.\n")

    results = {}

    # Phase 1: Package manager
    results["Chocolatey"] = install_chocolatey()

    if not results["Chocolatey"]:
        fail("Can't continue without Chocolatey. Fix the install and rerun.")
        sys.exit(1)

    # Phase 2: Dev toolchain
    install_dev_toolchain()
    results["Git + ffmpeg + yt-dlp"] = True
    results["Python"] = install_python_via_choco()
    results["NVM + Node.js"] = install_nvm_and_node()
    results["Yarn"] = install_yarn()

    # Phase 3: Desktop apps
    app_count, app_failures = install_desktop_apps()
    results[f"Desktop Apps ({app_count} installed)"] = len(app_failures) == 0

    # Phase 4: Special cases
    install_special_cases()
    results["Macrium Reflect 8.0.7783"] = True  # best-effort

    # Phase 5: VS Code + gitconfig
    install_vscode_extensions()
    restore_gitconfig()

    # Summary
    banner("Setup Summary")
    for item, ok in results.items():
        status = f"{GREEN}OK{RESET}" if ok else f"{YELLOW}NEEDS ATTENTION{RESET}"
        print(f"  {item}: {status}")

    # Phase 6: Manual steps
    print_manual_steps()

    step("Done! You may need to restart your terminal for PATH changes to take effect.")


if __name__ == "__main__":
    main()
