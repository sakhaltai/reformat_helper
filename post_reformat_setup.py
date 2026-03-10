r"""
Post-reformat setup script for Nicholas Hartmann's dev machine.

This script installs the core dev toolchain you need to get back to work
after a Windows reformat. It's intentionally conservative — it installs
only what your projects actually use, not a kitchen-sink of tools.

What it installs:
  1. Chocolatey (Windows package manager — like apt/brew, lets you install
     CLI tools with one command and keep them updated with `choco upgrade all`)
  2. Git + Git LFS (via choco)
  3. ffmpeg (via choco — no more manually downloading zip files)
  4. yt-dlp (via choco)
  5. Python (latest stable, via choco — includes pip)
  6. NVM for Windows (manages multiple Node.js versions)
  7. Node.js LTS (via nvm)
  8. Yarn (via npm, after node is installed)
  9. VS Code extensions (from vscode_extensions.txt)
  10. .gitconfig restoration

What it does NOT install (and why):
  - Anaconda/Conda — you have it but none of your projects use conda envs.
    If you need it later: `choco install anaconda3`
  - pnpm — none of your projects use it
  - Multiple Python versions — just need one; venvs handle isolation

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


# ---------------------------------------------------------------------------
# Install steps
# ---------------------------------------------------------------------------

def install_chocolatey():
    """Install Chocolatey package manager."""
    if command_exists("choco"):
        step("Chocolatey already installed.")
        return True

    banner("Installing Chocolatey")
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
        # Refresh PATH so choco is available in this session
        _refresh_path()
        return True
    else:
        fail("Chocolatey installation failed. You may need to install it manually.")
        return False


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


def install_choco_packages():
    """Install core tools via Chocolatey."""
    packages = {
        "git": "Git version control",
        "git-lfs": "Git Large File Storage (your repos use this)",
        "ffmpeg": "Audio/video processing (no more manual zip downloads!)",
        "yt-dlp": "Video downloader",
    }

    banner("Installing core tools via Chocolatey")

    for pkg, desc in packages.items():
        step(f"Installing {pkg} — {desc}")
        ok, out = run_cmd(f"choco install {pkg} -y --no-progress")
        if ok:
            step(f"  {pkg} installed.")
        else:
            # choco returns success even if already installed, so this is a real error
            warn(f"  {pkg} may have had issues. Check manually with: choco list {pkg}")

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

    # Install and use latest LTS node
    step("Installing Node.js LTS via NVM...")
    run_cmd("nvm install lts")
    run_cmd("nvm use lts")
    _refresh_path()

    if command_exists("node"):
        ok, ver = run_cmd("node --version")
        step(f"Node.js ready: {ver}")
    else:
        warn("Node may need a shell restart. After restart, run: nvm install lts && nvm use lts")

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
        warn("Yarn install failed. After restart, run: npm install -g yarn")
    return ok


def install_vscode_extensions():
    """Install VS Code extensions from the saved list."""
    banner("Installing VS Code Extensions")

    if not command_exists("code"):
        warn("VS Code CLI not found. Install VS Code first, then rerun this step.")
        warn(f"Or manually: for /F %e in ({EXTENSIONS_FILE}) do code --install-extension %e")
        return

    if not EXTENSIONS_FILE.exists():
        warn(f"Extensions list not found at {EXTENSIONS_FILE}")
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
        return

    shutil.copy2(GITCONFIG_TEMPLATE, target)
    step(f"Restored .gitconfig to {target}")


def print_manual_steps():
    """Print things the user still needs to do manually."""
    banner("Manual Steps Remaining")

    print(f"""  {BOLD}These can't be automated — do them when you're ready:{RESET}

  {YELLOW}1. Restore SSH keys{RESET}
     Copy your .ssh folder from your backup to C:\\Users\\sakha\\.ssh

  {YELLOW}2. Restore Claude Code settings{RESET}
     Copy your .claude folder from backup to C:\\Users\\sakha\\.claude

  {YELLOW}3. Install desktop apps{RESET}
     These are easier to install via their own installers:
     - VS Code:        https://code.visualstudio.com
     - Discord:        https://discord.com
     - Figma:          https://figma.com/downloads
     - 1Password:      https://1password.com/downloads
     - Slack:          https://slack.com/downloads
     - Spotify:        https://spotify.com/download
     - Docker Desktop: https://docker.com/products/docker-desktop
     - OBS Studio:     https://obsproject.com  (+ input-overlay plugin)

  {YELLOW}4. Clone your repos{RESET}
     cd C:\\Users\\sakha\\Code
     git clone https://github.com/sakhaltai/aeroja.git
     git clone https://github.com/sakhaltai/aether.git
     git clone https://github.com/sakhaltai/sakhaltai.github.io.git
     ... etc. (check your GitHub profile for the full list)

  {YELLOW}5. Install project dependencies{RESET}
     For each repo, run the appropriate install command:
       yarn install   (aeroja, aether)
       npm install    (sakhaltai.github.io)
       pip install -r requirements.txt   (rodeo2024)

  {YELLOW}6. Fonts{RESET}
     Restore from your Macrium backup image.

  {YELLOW}7. Verify everything{RESET}
     - git --version
     - python --version
     - node --version && npm --version
     - yarn --version
     - ffmpeg -version
     - yt-dlp --version
""")


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

    # Track what succeeded so we can give a summary
    results = {}

    results["Chocolatey"] = install_chocolatey()
    if results["Chocolatey"]:
        install_choco_packages()
        results["Git + ffmpeg + yt-dlp"] = True
        results["Python"] = install_python_via_choco()

    results["NVM + Node.js"] = install_nvm_and_node()
    results["Yarn"] = install_yarn()
    install_vscode_extensions()
    restore_gitconfig()

    # Summary
    banner("Setup Summary")
    for item, ok in results.items():
        status = f"{GREEN}OK{RESET}" if ok else f"{YELLOW}NEEDS ATTENTION{RESET}"
        print(f"  {item}: {status}")

    print_manual_steps()

    step("Done! You may need to restart your terminal for PATH changes to take effect.")


if __name__ == "__main__":
    main()
