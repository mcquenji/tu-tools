from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

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


# Update this with real data as lessons are held.
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

    if not rows:
        return title

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


def get_target_rows(
    lessons: list[Lesson],
    scale: list[PointScale],
    target_points: float,
    distribute_points: bool = False,
) -> tuple[str, list[tuple[str, str]]]:
    matching_scales = [
        point_scale for point_scale in scale if point_scale.points >= target_points
    ]

    if not matching_scales:
        return (
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

    common_rows = [
        ("Target grade points", format_grade_points(target_points)),
        ("Required percentage", format_percentage(target_scale.percentage)),
        ("Required raw points", f"{required_points}/{total_max_points}"),
        ("Current raw points", f"{achieved_points}/{total_max_points}"),
    ]

    if distribute_points:
        if remaining_lessons_count == 0:
            if missing_points == 0:
                return (
                    "Target already reached",
                    common_rows
                    + [
                        ("Needed per lesson", "0 points"),
                    ],
                )

            return (
                "Not possible",
                common_rows
                + [
                    ("Reason", "No remaining lessons"),
                    ("Missing raw points", f"{missing_points}"),
                ],
            )

        if missing_points > available_projection_points:
            shortage = missing_points - available_projection_points

            return (
                "Not possible",
                common_rows
                + [
                    ("Missing raw points", f"{missing_points}"),
                    ("Available raw points", f"{available_projection_points}"),
                    ("Short by", f"{shortage} {plural(shortage, 'point')}"),
                ],
            )

        points_per_lesson = ceil(missing_points / remaining_lessons_count)

        return (
            "Points needed per remaining lesson",
            common_rows
            + [
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

        return (
            "Not possible",
            common_rows
            + [
                ("Missing raw points", f"{missing_points}"),
                ("Available raw points", f"{available_projection_points}"),
                ("Short by", f"{shortage} {plural(shortage, 'point')}"),
            ],
        )

    if missing_points == 0:
        return (
            "Lessons you can skip",
            common_rows
            + [
                ("Remaining lessons", f"{remaining_lessons_count}"),
                (
                    "You may skip",
                    f"{remaining_lessons_count} "
                    f"{plural(remaining_lessons_count, 'lesson')}",
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

    return (
        "Lessons you can skip",
        common_rows
        + [
            ("Missing raw points", f"{missing_points}"),
            ("Remaining lessons", f"{remaining_lessons_count}"),
            ("Available raw points", f"{available_projection_points}"),
            ("You may skip", f"{skipped_lessons} {plural(skipped_lessons, 'lesson')}"),
            ("You still need", f"{lessons_needed} {plural(lessons_needed, 'lesson')}"),
        ],
    )


def get_max_reachable_points_with_min_effort_rows(
    lessons: list[Lesson],
    scale: list[PointScale],
) -> tuple[str, list[tuple[str, str]]]:
    projection_lessons = [lesson for lesson in lessons if lesson.projection]

    total_max_points = sum(lesson.max_points for lesson in lessons)

    achieved_points = sum(
        lesson.achieved_points for lesson in lessons if not lesson.projection
    )

    available_projection_points = sum(
        lesson.max_points for lesson in projection_lessons
    )

    max_possible_raw_points = achieved_points + available_projection_points

    reachable_scales = [
        point_scale
        for point_scale in scale
        if max_possible_raw_points >= ceil(point_scale.percentage * total_max_points)
    ]

    if not reachable_scales:
        return (
            "Max reachable points with minimum effort",
            [
                ("Max reachable grade points", "0"),
                ("Current raw points", f"{achieved_points}/{total_max_points}"),
                (
                    "Max possible raw points",
                    f"{max_possible_raw_points}/{total_max_points}",
                ),
                ("Minimum extra effort", "0 points"),
                ("Lessons needed", "0 lessons"),
                (
                    "Lessons skippable",
                    f"{len(projection_lessons)} {plural(len(projection_lessons), 'lesson')}",
                ),
            ],
        )

    best_scale = max(reachable_scales, key=lambda x: x.points)

    required_points = ceil(best_scale.percentage * total_max_points)
    missing_points = max(0, required_points - achieved_points)

    lessons_by_effort = sorted(
        projection_lessons,
        key=lambda lesson: lesson.max_points,
        reverse=True,
    )

    used_lessons = 0
    gathered_points = 0

    for lesson in lessons_by_effort:
        if gathered_points >= missing_points:
            break

        gathered_points += lesson.max_points
        used_lessons += 1

    skippable_lessons = len(projection_lessons) - used_lessons

    return (
        "Max reachable points with minimum effort",
        [
            ("Max reachable grade points", format_grade_points(best_scale.points)),
            ("Required percentage", format_percentage(best_scale.percentage)),
            ("Required raw points", f"{required_points}/{total_max_points}"),
            ("Current raw points", f"{achieved_points}/{total_max_points}"),
            ("Missing raw points", f"{missing_points}"),
            ("Available raw points", f"{available_projection_points}"),
            (
                "Minimum extra effort",
                f"{missing_points} {plural(missing_points, 'point')}",
            ),
            ("Lessons needed", f"{used_lessons} {plural(used_lessons, 'lesson')}"),
            (
                "Lessons skippable",
                f"{skippable_lessons} {plural(skippable_lessons, 'lesson')}",
            ),
        ],
    )


def calculate_max_reachable_points_with_min_effort(
    lessons: list[Lesson],
    scale: list[PointScale],
) -> str:
    title, rows = get_max_reachable_points_with_min_effort_rows(
        lessons=lessons,
        scale=scale,
    )

    return make_result_box(title, rows)


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

    title, rows = get_target_rows(
        lessons=lessons,
        scale=scale,
        target_points=target_points,
        distribute_points=distribute_points,
    )

    return make_result_box(title, rows)


def get_summary_rows(
    lessons: list[Lesson],
    scale: list[PointScale],
) -> list[tuple[str, str]]:
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

    return [
        ("Confirmed raw points", f"{confirmed_points}/{total_max_points}"),
        ("Confirmed percentage", format_percentage(confirmed_percentage)),
        ("Confirmed grade points", format_grade_points(confirmed_grade_points)),
        ("", ""),
        ("Projected raw points", f"{projected_points}/{total_max_points}"),
        ("Projected percentage", format_percentage(projected_percentage)),
        ("Projected grade points", format_grade_points(projected_grade_points)),
    ]


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

    min_percentage = min(point_scale.percentage for point_scale in scale)

    table.add_row(f"< {format_percentage(min_percentage)}", "0", style="red")

    for point_scale in sorted(scale, key=lambda x: x.percentage):
        table.add_row(
            format_percentage(point_scale.percentage),
            format_grade_points(point_scale.points),
        )

    console.print(table)


def print_summary(lessons: list[Lesson], scale: list[PointScale]) -> None:
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column(justify="right")

    for label, value in get_summary_rows(lessons, scale):
        summary.add_row(label, value)

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


def create_pdf_report(
    lessons: list[Lesson],
    scale: list[PointScale],
    target_points: float,
    output_path: Path,
) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table as PdfTable,
            TableStyle,
        )
    except ImportError as error:
        raise RuntimeError(
            "Missing dependency: reportlab. Install it with: pip install reportlab"
        ) from error

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=20,
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceBefore=14,
        spaceAfter=8,
    )

    note_style = ParagraphStyle(
        "Note",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6b7280"),
        spaceAfter=12,
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    story = []

    story.append(Paragraph("Lesson Points Report", title_style))
    story.append(
        Paragraph(
            "Generated from the current lesson configuration. Raw points are treated "
            "as integers, so required values are rounded up where needed.",
            note_style,
        )
    )

    story.append(Paragraph("Summary", section_style))
    story.append(create_pdf_key_value_table(get_summary_rows(lessons, scale)))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Lessons", section_style))

    lesson_data = [["#", "Status", "Raw points", "Progress"]]

    for index, lesson in enumerate(lessons, start=1):
        status = "Projection" if lesson.projection else "Completed"
        progress = (
            "0%"
            if lesson.max_points == 0
            else format_percentage(lesson.achieved_points / lesson.max_points)
        )

        lesson_data.append(
            [
                str(index),
                status,
                f"{lesson.achieved_points}/{lesson.max_points}",
                progress,
            ]
        )

    lesson_table = PdfTable(
        lesson_data,
        colWidths=[1.2 * cm, 4.0 * cm, 4.0 * cm, 3.0 * cm],
        hAlign="LEFT",
    )

    lesson_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f9fafb")],
                ),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )

    story.append(lesson_table)

    story.append(Spacer(1, 10))
    story.append(Paragraph("Point Scale", section_style))

    sorted_scale = sorted(scale, key=lambda x: x.percentage)
    min_percentage = min(point_scale.percentage for point_scale in sorted_scale)

    scale_data = [["Required", "Grade points"]]
    scale_data.append([f"< {format_percentage(min_percentage)}", "0"])

    for point_scale in sorted_scale:
        scale_data.append(
            [
                format_percentage(point_scale.percentage),
                format_grade_points(point_scale.points),
            ]
        )

    scale_table = PdfTable(
        scale_data,
        colWidths=[5.0 * cm, 5.0 * cm],
        hAlign="LEFT",
    )

    scale_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f9fafb")],
                ),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#dc2626")),
            ]
        )
    )

    story.append(scale_table)

    story.append(Spacer(1, 10))
    story.append(Paragraph("Target Calculation: Distributed", section_style))

    distributed_title, distributed_rows = get_target_rows(
        lessons=lessons,
        scale=scale,
        target_points=target_points,
        distribute_points=True,
    )

    story.append(Paragraph(distributed_title, styles["Heading3"]))
    story.append(create_pdf_key_value_table(distributed_rows))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Target Calculation: Skippable Lessons", section_style))

    skippable_title, skippable_rows = get_target_rows(
        lessons=lessons,
        scale=scale,
        target_points=target_points,
        distribute_points=False,
    )

    story.append(Paragraph(skippable_title, styles["Heading3"]))
    story.append(create_pdf_key_value_table(skippable_rows))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Max Reachable With Minimum Effort", section_style))

    max_reachable_title, max_reachable_rows = (
        get_max_reachable_points_with_min_effort_rows(
            lessons=lessons,
            scale=scale,
        )
    )

    story.append(Paragraph(max_reachable_title, styles["Heading3"]))
    story.append(create_pdf_key_value_table(max_reachable_rows))

    doc.build(story)


def create_pdf_key_value_table(rows: list[tuple[str, str]]):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Table as PdfTable
    from reportlab.platypus import TableStyle

    cleaned_rows = [[label, value] for label, value in rows if label or value]

    table = PdfTable(
        cleaned_rows,
        colWidths=[6.0 * cm, 7.0 * cm],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    return table


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
    console.print(
        Panel(
            calculate_max_reachable_points_with_min_effort(
                LESSONS,
                scale,
            ),
            title="Max Reachable With Min Effort",
            border_style="magenta",
        )
    )

    wants_pdf = Confirm.ask("Create a PDF report?", default=False)

    if wants_pdf:
        output_path = Path.cwd() / "lesson_report.pdf"

        try:
            create_pdf_report(
                lessons=LESSONS,
                scale=scale,
                target_points=target_points,
                output_path=output_path,
            )

            console.print(
                Panel(
                    f"PDF written to:\n{output_path}",
                    title="Done",
                    border_style="green",
                )
            )
        except RuntimeError as error:
            console.print(
                Panel(
                    str(error),
                    title="PDF creation failed",
                    border_style="red",
                )
            )
