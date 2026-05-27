from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


@dataclass
class PointScale:
    percentage: float
    points: float

    def __post_init__(self) -> None:
        if not 0 <= self.percentage <= 1:
            raise ValueError("Percentage must be between 0 and 1.")


@dataclass
class Lesson:
    max_points: int
    achieved_points: int
    projection: bool = False

    def __post_init__(self) -> None:
        if self.max_points < 0:
            raise ValueError("Max points cannot be negative.")

        if self.achieved_points < 0:
            raise ValueError("Achieved points cannot be negative.")

        if self.achieved_points > self.max_points:
            raise ValueError(
                f"Achieved points ({self.achieved_points}) cannot exceed "
                f"max points ({self.max_points})."
            )


# Example lessons data. Update this with real data as you complete lessons.
LESSONS = [
    Lesson(6, 1),
    Lesson(6, 0),
    Lesson(6, 6),
    Lesson(6, 0),
    Lesson(6, 4),
    Lesson(2, 0),
    Lesson(6, 6),
    Lesson(6, 6),
    Lesson(6, 6),
]
"""
This script calculates the current and projected grade points based on completed and projected lessons, and determines the minimum points needed from remaining lessons to reach a target grade point total.
"""


def format_grade_points(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:.1f}"


def format_percentage(value: float) -> str:
    return f"{value * 100:.0f}%"


def plural(value: int, singular: str, plural_form: str | None = None) -> str:
    if value == 1:
        return singular

    return plural_form or f"{singular}s"


def make_result_box(title: str, rows: Iterable[tuple[str, str]]) -> str:
    rows = list(rows)

    label_width = max(len(label) for label, _ in rows)
    value_width = max(len(value) for _, value in rows)
    content_width = label_width + value_width + 3
    title_width = len(title) + 2

    width = max(content_width, title_width)

    lines = [
        f"╭─ {title}{'─' * (width - len(title) - 1)}╮",
    ]

    for label, value in rows:
        line = f"{label:<{label_width}} : {value:<{value_width}}"
        lines.append(f"│ {line:<{width}} │")

    lines.append(f"╰{'─' * (width + 2)}╯")

    return "\n".join(lines)


def calculate_points(
    lessons: list[Lesson],
    scale: list[PointScale],
    include_projections: bool = True,
) -> float:
    sorted_scale = sorted(scale, key=lambda x: x.percentage, reverse=True)

    relevant_lessons = [
        lesson for lesson in lessons if include_projections or not lesson.projection
    ]

    total = sum(lesson.max_points for lesson in relevant_lessons)

    if total == 0:
        return 0

    completed = sum(lesson.achieved_points for lesson in relevant_lessons)
    percentage = completed / total

    for point_scale in sorted_scale:
        if percentage >= point_scale.percentage:
            return point_scale.points

    return 0


def calculate_min_points_for_target(
    lessons: list[Lesson],
    scale: list[PointScale],
    target_points: float,
    distribute_points: bool = False,
) -> str:
    """
    Calculate the minimum points needed from remaining lessons to reach a target point total.

    If distribute_points is True, return the integer points needed per remaining lesson.
    If distribute_points is False, return how many remaining lessons can be skipped.
    If reaching the target is impossible, return "Not possible".
    """

    matching_scales = [
        point_scale for point_scale in scale if point_scale.points >= target_points
    ]

    if not matching_scales:
        return make_result_box(
            "Not possible",
            [
                ("Target grade points", format_grade_points(target_points)),
                ("Reason", "No matching point scale exists"),
            ],
        )

    target_scale = min(matching_scales, key=lambda x: x.percentage)

    total_max_points = sum(lesson.max_points for lesson in lessons)

    achieved_points = sum(
        lesson.achieved_points for lesson in lessons if not lesson.projection
    )

    projection_lessons = [lesson for lesson in lessons if lesson.projection]

    remaining_lessons_count = len(projection_lessons)

    available_projection_points = sum(
        lesson.max_points for lesson in projection_lessons
    )

    required_points = ceil(target_scale.percentage * total_max_points)
    missing_points = max(0, required_points - achieved_points)

    if distribute_points:
        if remaining_lessons_count == 0:
            if missing_points == 0:
                return make_result_box(
                    "Target already reached",
                    [
                        ("Target grade points", format_grade_points(target_points)),
                        (
                            "Required percentage",
                            format_percentage(target_scale.percentage),
                        ),
                        (
                            "Required raw points",
                            f"{required_points}/{total_max_points}",
                        ),
                        ("Current raw points", f"{achieved_points}/{total_max_points}"),
                        ("Needed per lesson", "0 points"),
                    ],
                )

            return make_result_box(
                "Not possible",
                [
                    ("Target grade points", format_grade_points(target_points)),
                    ("Reason", "No remaining lessons"),
                    ("Missing raw points", f"{missing_points}"),
                ],
            )

        if missing_points > available_projection_points:
            shortage = missing_points - available_projection_points

            return make_result_box(
                "Not possible",
                [
                    ("Target grade points", format_grade_points(target_points)),
                    ("Required percentage", format_percentage(target_scale.percentage)),
                    ("Required raw points", f"{required_points}/{total_max_points}"),
                    ("Current raw points", f"{achieved_points}/{total_max_points}"),
                    ("Missing raw points", f"{missing_points}"),
                    ("Available raw points", f"{available_projection_points}"),
                    ("Short by", f"{shortage} {plural(shortage, 'point')}"),
                ],
            )

        points_per_lesson = ceil(missing_points / remaining_lessons_count)

        return make_result_box(
            "Points needed per remaining lesson",
            [
                ("Target grade points", format_grade_points(target_points)),
                ("Required percentage", format_percentage(target_scale.percentage)),
                ("Required raw points", f"{required_points}/{total_max_points}"),
                ("Current raw points", f"{achieved_points}/{total_max_points}"),
                ("Missing raw points", f"{missing_points}"),
                ("Remaining lessons", f"{remaining_lessons_count}"),
                ("Available raw points", f"{available_projection_points}"),
                (
                    "Needed per lesson",
                    f"{points_per_lesson} {plural(points_per_lesson, 'point')}",
                ),
            ],
        )

    if missing_points > available_projection_points:
        shortage = missing_points - available_projection_points

        return make_result_box(
            "Not possible",
            [
                ("Target grade points", format_grade_points(target_points)),
                ("Required percentage", format_percentage(target_scale.percentage)),
                ("Required raw points", f"{required_points}/{total_max_points}"),
                ("Current raw points", f"{achieved_points}/{total_max_points}"),
                ("Missing raw points", f"{missing_points}"),
                ("Available raw points", f"{available_projection_points}"),
                ("Short by", f"{shortage} {plural(shortage, 'point')}"),
            ],
        )

    if missing_points == 0:
        return make_result_box(
            "Lessons you can skip",
            [
                ("Target grade points", format_grade_points(target_points)),
                ("Required percentage", format_percentage(target_scale.percentage)),
                ("Required raw points", f"{required_points}/{total_max_points}"),
                ("Current raw points", f"{achieved_points}/{total_max_points}"),
                ("Remaining lessons", f"{remaining_lessons_count}"),
                (
                    "You may skip",
                    f"{remaining_lessons_count} {plural(remaining_lessons_count, 'lesson')}",
                ),
                ("Reason", "Target already reached"),
            ],
        )

    skippable_lessons = sorted(
        projection_lessons,
        key=lambda lesson: lesson.max_points,
    )

    skipped_lessons = 0
    skipped_points = 0

    for lesson in skippable_lessons:
        would_skip_points = skipped_points + lesson.max_points
        points_left_after_skip = available_projection_points - would_skip_points

        if points_left_after_skip >= missing_points:
            skipped_points = would_skip_points
            skipped_lessons += 1
        else:
            break

    lessons_needed = remaining_lessons_count - skipped_lessons

    return make_result_box(
        "Lessons you can skip",
        [
            ("Target grade points", format_grade_points(target_points)),
            ("Required percentage", format_percentage(target_scale.percentage)),
            ("Required raw points", f"{required_points}/{total_max_points}"),
            ("Current raw points", f"{achieved_points}/{total_max_points}"),
            ("Missing raw points", f"{missing_points}"),
            ("Remaining lessons", f"{remaining_lessons_count}"),
            ("Available raw points", f"{available_projection_points}"),
            ("You may skip", f"{skipped_lessons} {plural(skipped_lessons, 'lesson')}"),
            ("You still need", f"{lessons_needed} {plural(lessons_needed, 'lesson')}"),
        ],
    )


def print_lessons(lessons: list[Lesson]) -> None:
    table = Table(title="Lessons", show_header=True, header_style="bold")
    table.add_column("#", justify="right")
    table.add_column("Status")
    table.add_column("Raw points", justify="right")
    table.add_column("Progress", justify="right")

    for index, lesson in enumerate(lessons, start=1):
        status = "Projection" if lesson.projection else "Completed"

        if lesson.max_points == 0:
            progress = "0%"
        else:
            progress = format_percentage(lesson.achieved_points / lesson.max_points)

        table.add_row(
            str(index),
            status,
            f"{lesson.achieved_points}/{lesson.max_points}",
            progress,
        )

    console.print(table)


def print_scale(scale: list[PointScale]) -> None:
    table = Table(title="Point Scale", show_header=True, header_style="bold")
    table.add_column("Required", justify="right")
    table.add_column("Grade points", justify="right")

    # get smallest percentage and add a row for < that with 0 points
    min_percentage = min(point_scale.percentage for point_scale in scale)

    table.add_row(f"< {format_percentage(min_percentage)}", "0", style="red")

    for point_scale in sorted(scale, key=lambda x: x.percentage):
        table.add_row(
            format_percentage(point_scale.percentage),
            format_grade_points(point_scale.points),
        )

    console.print(table)


def print_summary(lessons: list[Lesson], scale: list[PointScale]) -> None:
    total_max_points = sum(lesson.max_points for lesson in lessons)

    confirmed_points = sum(
        lesson.achieved_points for lesson in lessons if not lesson.projection
    )

    projected_points = sum(lesson.achieved_points for lesson in lessons)

    confirmed_grade_points = calculate_points(
        lessons,
        scale,
        include_projections=False,
    )

    projected_grade_points = calculate_points(
        lessons,
        scale,
        include_projections=True,
    )

    confirmed_percentage = (
        confirmed_points / total_max_points if total_max_points > 0 else 0
    )

    projected_percentage = (
        projected_points / total_max_points if total_max_points > 0 else 0
    )

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column(justify="right")

    summary.add_row("Confirmed raw points", f"{confirmed_points}/{total_max_points}")
    summary.add_row("Confirmed percentage", format_percentage(confirmed_percentage))
    summary.add_row(
        "Confirmed grade points", format_grade_points(confirmed_grade_points)
    )
    summary.add_row("", "")
    summary.add_row("Projected raw points", f"{projected_points}/{total_max_points}")
    summary.add_row("Projected percentage", format_percentage(projected_percentage))
    summary.add_row(
        "Projected grade points", format_grade_points(projected_grade_points)
    )

    console.print(
        Panel(
            summary,
            title="Summary",
            border_style="green",
        )
    )


def add_missing_projection_lessons(
    lessons: list[Lesson],
    target_lesson_count: int = 12,
) -> None:
    """
    Fill missing future lessons with projections.

    This is intentionally based on the current length of the lessons list,
    so the script stays reusable as real lessons are completed over time.
    """

    while len(lessons) < target_lesson_count:
        lesson_number = len(lessons) + 1

        if lesson_number in {6, 11}:
            max_points = 2
        else:
            max_points = 6

        lessons.append(
            Lesson(
                max_points=max_points,
                achieved_points=max_points,
                projection=True,
            )
        )


if __name__ == "__main__":
    scale = [
        PointScale(0.60, 1),
        PointScale(0.75, 1.5),
        PointScale(0.85, 2),
    ]

    add_missing_projection_lessons(LESSONS)

    target_points = 1

    console.print()
    print_lessons(LESSONS)

    console.print()
    print_scale(scale)

    console.print()
    print_summary(LESSONS, scale)

    console.print()
    console.print(
        Panel(
            calculate_min_points_for_target(
                LESSONS,
                scale,
                target_points,
                distribute_points=True,
            ),
            title="Target Calculation: Distributed",
            border_style="blue",
        )
    )

    console.print()
    console.print(
        Panel(
            calculate_min_points_for_target(
                LESSONS,
                scale,
                target_points,
                distribute_points=False,
            ),
            title="Target Calculation: Skippable Lessons",
            border_style="cyan",
        )
    )

    console.print()
