"""拉取 chan.py 框架并安装本地数据源适配器。

用法:
    python scripts/setup_framework.py [--force]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "framework"
VENDOR = ROOT / "vendor" / "LocalStore.py"
UPSTREAM = "https://github.com/Vespa314/chan.py.git"
# 与论文/报告口径一致的固定版本（2026-10-28）
COMMIT = "f8ca3b5e44d7166e2abd756a8e7fa816c79faebe"


def run(*args, cwd=None):
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="已存在时仍然重置到固定 commit")
    args = ap.parse_args()

    if not FRAMEWORK.exists():
        run("git", "clone", UPSTREAM, str(FRAMEWORK))
    elif args.force:
        run("git", "-C", str(FRAMEWORK), "fetch", "--all", "--tags")
    if not (FRAMEWORK / ".git").exists():
        raise SystemExit(f"{FRAMEWORK} 存在但不是 git 仓库，请先移走")
    run("git", "-C", str(FRAMEWORK), "checkout", "--quiet", COMMIT)

    dst = FRAMEWORK / "DataAPI" / "LocalStore.py"
    shutil.copyfile(VENDOR, dst)
    print(f"copied {VENDOR} -> {dst}")
    print("done. 下一步: python scripts/fetch.py")


if __name__ == "__main__":
    main()
