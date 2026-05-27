from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from config import load_courses
from console_report import print_course
from pdf_report import create_pdf_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "courses.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "lesson_report.pdf"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--pdf", action="store_true", help="Create the PDF without prompting."
    )
    output.add_argument(
        "--no-pdf", action="store_true", help="Only display the console report."
    )
    parser.add_argument(
        "--style",
        choices=("vivid", "formal"),
        default=None,
        help="PDF visual style. Defaults to vivid for non-interactive generation.",
    )


def run(args: argparse.Namespace) -> int:
    console = Console()

    try:
        courses = load_courses(args.data)
    except ValueError as error:
        console.print(Panel(str(error), title="Configuration error", border_style="red"))
        return 1

    console.print()
    for course in courses:
        print_course(console, course)
        console.print()

    wants_pdf = args.pdf or (
        not args.no_pdf and Confirm.ask("Create a PDF report?", default=False)
    )
    if not wants_pdf:
        return 0

    style = args.style
    if style is None:
        style = (
            "vivid"
            if args.pdf
            else Prompt.ask("PDF style", choices=["vivid", "formal"], default="vivid")
        )

    try:
        create_pdf_report(courses, args.output, style=style)
    except RuntimeError as error:
        console.print(Panel(str(error), title="PDF creation failed", border_style="red"))
        return 1

    console.print(
        Panel(f"PDF written to:\n{args.output}", title="Done", border_style="green")
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate lesson point reports.")
    add_arguments(parser)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
