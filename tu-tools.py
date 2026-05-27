from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parent


def load_command(name: str, entry_point: Path) -> ModuleType:
    command_dir = str(entry_point.parent)
    if command_dir not in sys.path:
        sys.path.insert(0, command_dir)

    spec = importlib.util.spec_from_file_location(f"tu_tools_{name}", entry_point)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load command: {name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tu-tools",
        description="Small utilities for TU coursework and administration.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    lessons = load_command("ue_lessons", PROJECT_ROOT / "ue-lessons" / "main.py")
    lessons_parser = commands.add_parser(
        "ue-lessons",
        help="Display lesson points and optionally create a PDF report.",
        description="Generate a report for courses listed in data/courses.json.",
    )
    lessons.add_arguments(lessons_parser)
    lessons_parser.set_defaults(handler=lessons.run)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
