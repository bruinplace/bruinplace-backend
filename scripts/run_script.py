"""Run scripts modules with project imports configured.

Usage:
    uv run python scripts/run_script.py <filename>
    uv run python scripts/run_script.py scripts.<filename>
    uv run python scripts/run_script.py scripts/<filename>.py
"""

from __future__ import annotations

from pathlib import Path
import runpy
import sys


def normalize_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.endswith(".py"):
        target = target[:-3]
    target = target.replace("\\", ".").replace("/", ".")
    if target.startswith("scripts."):
        return target
    if target.startswith("."):
        target = target.lstrip(".")
    return f"scripts.{target}"


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: uv run python scripts/run_script.py <script-name|module|path> [args...]"
        )
        sys.exit(1)

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    module_name = normalize_target(sys.argv[1])
    script_args = sys.argv[2:]
    sys.argv = [module_name, *script_args]
    runpy.run_module(module_name, run_name="__main__")


if __name__ == "__main__":
    main()
