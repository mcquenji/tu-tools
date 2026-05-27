from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from calculations import (
    calculate_max_reachable_with_min_effort,
    calculate_target,
    format_grade_points,
    format_percentage,
    get_summary_rows,
)
from models import Course


def print_course(console: Console, course: Course) -> None:
    console.rule(f"[bold]{course.name}[/bold]")

    lessons = Table(title="Lessons", show_header=True, header_style="bold")
    lessons.add_column("#", justify="right")
    lessons.add_column("Status")
    lessons.add_column("Raw points", justify="right")
    lessons.add_column("Progress", justify="right")
    for index, lesson in enumerate(course.lessons, start=1):
        status = "Projection" if lesson.projected else "Completed"
        style = "cyan" if lesson.projected else "green"
        progress = (
            format_percentage(lesson.earned_points / lesson.max_points)
            if lesson.max_points
            else "0%"
        )
        lessons.add_row(
            str(index),
            f"[{style}]{status}[/{style}]",
            f"{lesson.earned_points}/{lesson.max_points}",
            progress,
        )
    console.print(lessons)

    scale = Table(title="Point Scale", show_header=True, header_style="bold")
    scale.add_column("Required", justify="right")
    scale.add_column("Grade points", justify="right")
    minimum = min(
        point_scale.minimum_percentage for point_scale in course.grade_scale
    )
    scale.add_row(f"< {format_percentage(minimum)}", "0", style="red")
    for point_scale in sorted(
        course.grade_scale, key=lambda point_scale: point_scale.minimum_percentage
    ):
        scale.add_row(
            format_percentage(point_scale.minimum_percentage),
            format_grade_points(point_scale.grade_points),
        )
    console.print(scale)

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column(justify="right")
    for label, value in get_summary_rows(course):
        summary.add_row(label, value)
    console.print(Panel(summary, title="Summary", border_style="green"))

    target = calculate_target(course)
    target_rows = Table.grid(padding=(0, 2))
    target_rows.add_column(style="bold")
    target_rows.add_column(justify="right")
    target_rows.add_row("Status", target.status.replace("_", " ").title())
    target_rows.add_row("Target", format_grade_points(target.target_grade_points))
    target_rows.add_row("Current", f"{target.current_raw_points}/{target.total_raw_points}")
    target_rows.add_row("Missing", str(target.missing_raw_points))
    if target.lessons_still_needed is not None:
        target_rows.add_row("Lessons still needed", str(target.lessons_still_needed))
    if target.reason:
        target_rows.add_row("Reason", target.reason)
    console.print(Panel(target_rows, title="Target Calculation", border_style="blue"))

    maximum = calculate_max_reachable_with_min_effort(course)
    max_rows = Table.grid(padding=(0, 2))
    max_rows.add_column(style="bold")
    max_rows.add_column(justify="right")
    max_rows.add_row(
        "Best reachable", format_grade_points(maximum.max_reachable_grade_points)
    )
    max_rows.add_row("Additional points needed", str(maximum.minimum_extra_effort))
    max_rows.add_row("Lessons needed", str(maximum.lessons_needed))
    max_rows.add_row("Lessons skippable", str(maximum.lessons_skippable))
    console.print(
        Panel(max_rows, title="Max Reachable With Minimum Effort", border_style="magenta")
    )
