"""
Clone all repos and install their dependencies.

Run this AFTER post_reformat_setup.py has installed Git, Node, Python, Yarn, etc.

Usage (from PowerShell):
    cd C:\Users\sakha\Code\reformat_helper
    python clone_and_install.py
"""

import os
import subprocess
import sys

CODE_DIR = os.path.expanduser("~/code")

# (folder_relative_to_CODE_DIR, clone_url, install_command)
REPOS = [
    # ── sakhalteam org ──
    ("sakhalteam/bird-bingo",           "https://github.com/sakhalteam/bird-bingo.git",           "npm install"),
    ("sakhalteam/japanese-articles",    "https://github.com/sakhalteam/japanese-articles.git",    "npm install"),
    ("sakhalteam/nikbeat",              "https://github.com/sakhalteam/nikbeat.git",              "npm install"),
    ("sakhalteam/sakhalteam.github.io", "https://github.com/sakhalteam/sakhalteam.github.io.git", "npm install"),
    ("sakhalteam/adhdo",                "https://github.com/sakhalteam/adhdo.git",                None),

    # ── personal repos ──
    ("aeroja",                "https://github.com/sakhaltai/aeroja.git",                "yarn install"),
    ("aether",                "https://github.com/sakhaltai/aether.git",                "yarn install"),
    ("sakhaltai.github.io",   "https://github.com/sakhaltai/sakhaltai.github.io.git",   "npm install"),
    ("rodeo2024",             "https://github.com/sakhaltai/rodeo2024.git",             "pip install -r requirements.txt"),
    ("adobe-scripts",         "https://github.com/sakhaltai/adobe-scripts.git",         None),
    ("ae_expressions",        "https://github.com/sakhaltai/ae_expressions.git",        None),
    ("python_tools",          "https://github.com/sakhaltai/python_tools.git",          None),
]


def run(cmd, cwd=None):
    """Run a shell command, print output, return success bool."""
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode == 0


def main():
    os.makedirs(CODE_DIR, exist_ok=True)

    # Make sure sakhalteam folder exists
    os.makedirs(os.path.join(CODE_DIR, "sakhalteam"), exist_ok=True)

    successes = []
    failures = []

    for folder, url, install_cmd in REPOS:
        repo_path = os.path.join(CODE_DIR, folder)
        print(f"\n{'='*60}")
        print(f"  {folder}")
        print(f"{'='*60}")

        # Clone if not already present
        if os.path.isdir(repo_path):
            print(f"  Already exists, skipping clone.")
        else:
            if not run(f'git clone "{url}" "{repo_path}"'):
                print(f"  FAILED to clone {url}")
                failures.append(folder)
                continue

        # Install dependencies
        if install_cmd:
            print(f"  Installing dependencies...")
            if not run(install_cmd, cwd=repo_path):
                print(f"  FAILED: {install_cmd}")
                failures.append(folder)
                continue

        successes.append(folder)

    # Summary
    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"{'='*60}")
    print(f"\n  Cloned & installed: {len(successes)}/{len(REPOS)}")
    if failures:
        print(f"  Failed: {', '.join(failures)}")
    else:
        print(f"  All repos ready!")


if __name__ == "__main__":
    main()
