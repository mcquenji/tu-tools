from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm
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


@dataclass
class TargetCalculation:
    status: str
    target_grade_points: float
    required_percentage: float | None
    required_raw_points: int | None
    total_raw_points: int
    current_raw_points: int
    missing_raw_points: int
    remaining_lessons: int
    available_raw_points: int
    average_needed_per_lesson: int | None
    skippable_lessons: int | None
    lessons_still_needed: int | None
    reason: str | None = None
    shortage: int | None = None


@dataclass
class MaxEffortCalculation:
    max_reachable_grade_points: float
    required_percentage: float | None
    required_raw_points: int | None
    total_raw_points: int
    current_raw_points: int
    missing_raw_points: int
    available_raw_points: int
    minimum_extra_effort: int
    lessons_needed: int
    lessons_skippable: int


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


def calculate_points(
    lessons: list[Lesson],
    scale: list[PointScale],
    include_projections: bool = True,
) -> float:
    sorted_scale = sorted(
        scale, key=lambda point_scale: point_scale.percentage, reverse=True
    )

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


def calculate_target(
    lessons: list[Lesson],
    scale: list[PointScale],
    target_points: float,
) -> TargetCalculation:
    matching_scales = [
        point_scale for point_scale in scale if point_scale.points >= target_points
    ]

    total_raw_points = sum(lesson.max_points for lesson in lessons)

    current_raw_points = sum(
        lesson.achieved_points for lesson in lessons if not lesson.projection
    )

    projection_lessons = [lesson for lesson in lessons if lesson.projection]

    remaining_lessons = len(projection_lessons)

    available_raw_points = sum(lesson.max_points for lesson in projection_lessons)

    if not matching_scales:
        return TargetCalculation(
            status="not_possible",
            target_grade_points=target_points,
            required_percentage=None,
            required_raw_points=None,
            total_raw_points=total_raw_points,
            current_raw_points=current_raw_points,
            missing_raw_points=0,
            remaining_lessons=remaining_lessons,
            available_raw_points=available_raw_points,
            average_needed_per_lesson=None,
            skippable_lessons=None,
            lessons_still_needed=None,
            reason="No matching point scale exists.",
        )

    target_scale = min(matching_scales, key=lambda point_scale: point_scale.percentage)

    required_raw_points = ceil(target_scale.percentage * total_raw_points)
    missing_raw_points = max(0, required_raw_points - current_raw_points)

    if missing_raw_points == 0:
        return TargetCalculation(
            status="reached",
            target_grade_points=target_points,
            required_percentage=target_scale.percentage,
            required_raw_points=required_raw_points,
            total_raw_points=total_raw_points,
            current_raw_points=current_raw_points,
            missing_raw_points=0,
            remaining_lessons=remaining_lessons,
            available_raw_points=available_raw_points,
            average_needed_per_lesson=0,
            skippable_lessons=remaining_lessons,
            lessons_still_needed=0,
            reason="Target already reached.",
        )

    if remaining_lessons == 0:
        return TargetCalculation(
            status="not_possible",
            target_grade_points=target_points,
            required_percentage=target_scale.percentage,
            required_raw_points=required_raw_points,
            total_raw_points=total_raw_points,
            current_raw_points=current_raw_points,
            missing_raw_points=missing_raw_points,
            remaining_lessons=0,
            available_raw_points=0,
            average_needed_per_lesson=None,
            skippable_lessons=0,
            lessons_still_needed=None,
            reason="No remaining lessons.",
        )

    if missing_raw_points > available_raw_points:
        shortage = missing_raw_points - available_raw_points

        return TargetCalculation(
            status="not_possible",
            target_grade_points=target_points,
            required_percentage=target_scale.percentage,
            required_raw_points=required_raw_points,
            total_raw_points=total_raw_points,
            current_raw_points=current_raw_points,
            missing_raw_points=missing_raw_points,
            remaining_lessons=remaining_lessons,
            available_raw_points=available_raw_points,
            average_needed_per_lesson=None,
            skippable_lessons=0,
            lessons_still_needed=None,
            reason="Not enough remaining raw points.",
            shortage=shortage,
        )

    average_needed_per_lesson = ceil(missing_raw_points / remaining_lessons)

    skippable_lessons = sorted(
        projection_lessons,
        key=lambda lesson: lesson.max_points,
    )

    skipped_lessons = 0
    skipped_points = 0

    for lesson in skippable_lessons:
        would_skip_points = skipped_points + lesson.max_points
        points_left_after_skip = available_raw_points - would_skip_points

        if points_left_after_skip >= missing_raw_points:
            skipped_points = would_skip_points
            skipped_lessons += 1
        else:
            break

    lessons_still_needed = remaining_lessons - skipped_lessons

    return TargetCalculation(
        status="possible",
        target_grade_points=target_points,
        required_percentage=target_scale.percentage,
        required_raw_points=required_raw_points,
        total_raw_points=total_raw_points,
        current_raw_points=current_raw_points,
        missing_raw_points=missing_raw_points,
        remaining_lessons=remaining_lessons,
        available_raw_points=available_raw_points,
        average_needed_per_lesson=average_needed_per_lesson,
        skippable_lessons=skipped_lessons,
        lessons_still_needed=lessons_still_needed,
    )


def calculate_max_reachable_with_min_effort(
    lessons: list[Lesson],
    scale: list[PointScale],
) -> MaxEffortCalculation:
    projection_lessons = [lesson for lesson in lessons if lesson.projection]

    total_raw_points = sum(lesson.max_points for lesson in lessons)

    current_raw_points = sum(
        lesson.achieved_points for lesson in lessons if not lesson.projection
    )

    available_raw_points = sum(lesson.max_points for lesson in projection_lessons)

    max_possible_raw_points = current_raw_points + available_raw_points

    reachable_scales = [
        point_scale
        for point_scale in scale
        if max_possible_raw_points >= ceil(point_scale.percentage * total_raw_points)
    ]

    if not reachable_scales:
        return MaxEffortCalculation(
            max_reachable_grade_points=0,
            required_percentage=None,
            required_raw_points=None,
            total_raw_points=total_raw_points,
            current_raw_points=current_raw_points,
            missing_raw_points=0,
            available_raw_points=available_raw_points,
            minimum_extra_effort=0,
            lessons_needed=0,
            lessons_skippable=len(projection_lessons),
        )

    best_scale = max(reachable_scales, key=lambda point_scale: point_scale.points)

    required_raw_points = ceil(best_scale.percentage * total_raw_points)
    missing_raw_points = max(0, required_raw_points - current_raw_points)

    lessons_by_effort = sorted(
        projection_lessons,
        key=lambda lesson: lesson.max_points,
        reverse=True,
    )

    used_lessons = 0
    gathered_points = 0

    for lesson in lessons_by_effort:
        if gathered_points >= missing_raw_points:
            break

        gathered_points += lesson.max_points
        used_lessons += 1

    skippable_lessons = len(projection_lessons) - used_lessons

    return MaxEffortCalculation(
        max_reachable_grade_points=best_scale.points,
        required_percentage=best_scale.percentage,
        required_raw_points=required_raw_points,
        total_raw_points=total_raw_points,
        current_raw_points=current_raw_points,
        missing_raw_points=missing_raw_points,
        available_raw_points=available_raw_points,
        minimum_extra_effort=missing_raw_points,
        lessons_needed=used_lessons,
        lessons_skippable=skippable_lessons,
    )


def get_summary_rows(
    lessons: list[Lesson],
    scale: list[PointScale],
) -> list[tuple[str, str]]:
    total_raw_points = sum(lesson.max_points for lesson in lessons)

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
        confirmed_points / total_raw_points if total_raw_points > 0 else 0
    )

    projected_percentage = (
        projected_points / total_raw_points if total_raw_points > 0 else 0
    )

    return [
        ("Confirmed raw points", f"{confirmed_points}/{total_raw_points}"),
        ("Confirmed percentage", format_percentage(confirmed_percentage)),
        ("Confirmed grade points", format_grade_points(confirmed_grade_points)),
        ("", ""),
        ("Projected raw points", f"{projected_points}/{total_raw_points}"),
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

        progress = (
            "0%"
            if lesson.max_points == 0
            else format_percentage(lesson.achieved_points / lesson.max_points)
        )

        status_style = "cyan" if lesson.projection else "green"

        table.add_row(
            str(index),
            f"[{status_style}]{status}[/{status_style}]",
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

    for point_scale in sorted(scale, key=lambda point_scale: point_scale.percentage):
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


def render_target_calculation(calculation: TargetCalculation) -> Panel:
    status_text = {
        "possible": "[green]Possible[/green]",
        "reached": "[green]Target already reached[/green]",
        "not_possible": "[red]Not possible[/red]",
    }.get(calculation.status, calculation.status)

    requirement = Table.grid(padding=(0, 2))
    requirement.add_column(style="bold")
    requirement.add_column(justify="right")

    requirement.add_row("Status", status_text)
    requirement.add_row(
        "Target",
        f"{format_grade_points(calculation.target_grade_points)} grade points",
    )

    if (
        calculation.required_percentage is not None
        and calculation.required_raw_points is not None
    ):
        requirement.add_row(
            "Requirement",
            f"{format_percentage(calculation.required_percentage)} → "
            f"{calculation.required_raw_points}/{calculation.total_raw_points} raw points",
        )

    requirement.add_row(
        "Current",
        f"{calculation.current_raw_points}/{calculation.total_raw_points} raw points",
    )

    requirement.add_row(
        "Missing",
        f"{calculation.missing_raw_points} "
        f"{plural(calculation.missing_raw_points, 'point')}",
    )

    if calculation.status == "not_possible":
        reason = calculation.reason or "Unknown reason."

        if calculation.shortage is not None:
            reason += (
                f" Short by {calculation.shortage} "
                f"{plural(calculation.shortage, 'point')}."
            )

        body = Group(
            requirement,
            Text(""),
            Text("Result", style="bold red"),
            Text(reason, style="red"),
        )

        return Panel(
            body,
            title="Target Calculation",
            border_style="red",
        )

    average_needed = (
        calculation.average_needed_per_lesson
        if calculation.average_needed_per_lesson is not None
        else 0
    )

    skippable_lessons = (
        calculation.skippable_lessons
        if calculation.skippable_lessons is not None
        else 0
    )

    lessons_still_needed = (
        calculation.lessons_still_needed
        if calculation.lessons_still_needed is not None
        else 0
    )

    average_section = Text()
    average_section.append("Average needed\n", style="bold")
    average_section.append(
        f"{average_needed} {plural(average_needed, 'point')} " f"per remaining lesson\n"
    )
    average_section.append(
        f"across {calculation.remaining_lessons} "
        f"{plural(calculation.remaining_lessons, 'lesson')}"
    )

    skip_section = Text()
    skip_section.append("Skippable lessons\n", style="bold")
    skip_section.append(
        f"You may skip {skippable_lessons} " f"{plural(skippable_lessons, 'lesson')}\n"
    )
    skip_section.append(
        f"You still need to complete {lessons_still_needed} "
        f"{plural(lessons_still_needed, 'lesson')}"
    )

    body = Group(
        requirement,
        Text(""),
        Panel(average_section, border_style="blue"),
        Panel(skip_section, border_style="cyan"),
    )

    return Panel(
        body,
        title="Target Calculation",
        border_style="blue",
    )


def render_max_effort_calculation(calculation: MaxEffortCalculation) -> Panel:
    overview = Table.grid(padding=(0, 2))
    overview.add_column(style="bold")
    overview.add_column(justify="right")

    overview.add_row(
        "Best reachable",
        f"{format_grade_points(calculation.max_reachable_grade_points)} grade points",
    )

    if (
        calculation.required_percentage is not None
        and calculation.required_raw_points is not None
    ):
        overview.add_row(
            "Requirement",
            f"{format_percentage(calculation.required_percentage)} → "
            f"{calculation.required_raw_points}/{calculation.total_raw_points} raw points",
        )

    overview.add_row(
        "Current",
        f"{calculation.current_raw_points}/{calculation.total_raw_points} raw points",
    )

    overview.add_row(
        "Missing",
        f"{calculation.missing_raw_points} "
        f"{plural(calculation.missing_raw_points, 'point')}",
    )

    effort_section = Text()
    effort_section.append("Minimum effort\n", style="bold")
    effort_section.append(
        f"Earn {calculation.minimum_extra_effort} "
        f"{plural(calculation.minimum_extra_effort, 'point')}\n"
    )
    effort_section.append(
        f"Complete {calculation.lessons_needed} "
        f"{plural(calculation.lessons_needed, 'lesson')}"
    )

    skip_section = Text()
    skip_section.append("Still skippable\n", style="bold")
    skip_section.append(
        f"{calculation.lessons_skippable} "
        f"{plural(calculation.lessons_skippable, 'lesson')}"
    )

    body = Group(
        overview,
        Text(""),
        Panel(effort_section, border_style="magenta"),
        Panel(skip_section, border_style="cyan"),
    )

    return Panel(
        body,
        title="Max Reachable With Minimum Effort",
        border_style="magenta",
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


def create_pdf_info_card(
    title: str,
    lines: list[str],
    border_color: str = "#2563eb",
):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table as PdfTable, TableStyle

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CardTitle",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#111827"),
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "CardBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#374151"),
    )

    content = [
        Paragraph(title, title_style),
        *[Paragraph(line, body_style) for line in lines],
    ]

    table = PdfTable(
        [[content]],
        colWidths=[13.2 * cm],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor(border_color)),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    return table


def target_calculation_pdf_elements(calculation: TargetCalculation) -> list:
    from reportlab.platypus import Spacer

    elements = []

    if calculation.status == "not_possible":
        lines = [
            f"Target: {format_grade_points(calculation.target_grade_points)} grade points",
            f"Current: {calculation.current_raw_points}/{calculation.total_raw_points} raw points",
            f"Missing: {calculation.missing_raw_points} raw points",
        ]

        if (
            calculation.required_percentage is not None
            and calculation.required_raw_points is not None
        ):
            lines.insert(
                1,
                f"Requirement: {format_percentage(calculation.required_percentage)} "
                f"→ {calculation.required_raw_points}/{calculation.total_raw_points} raw points",
            )

        if calculation.reason:
            lines.append(f"Reason: {calculation.reason}")

        if calculation.shortage is not None:
            lines.append(f"Short by: {calculation.shortage} raw points")

        elements.append(
            create_pdf_info_card(
                "Target Calculation — Not possible",
                lines,
                border_color="#dc2626",
            )
        )

        return elements

    average_needed = calculation.average_needed_per_lesson or 0
    skippable_lessons = calculation.skippable_lessons or 0
    lessons_still_needed = calculation.lessons_still_needed or 0

    elements.append(
        create_pdf_info_card(
            "Target Calculation",
            [
                f"Status: {'Target already reached' if calculation.status == 'reached' else 'Possible'}",
                f"Target: {format_grade_points(calculation.target_grade_points)} grade points",
                f"Requirement: {format_percentage(calculation.required_percentage or 0)} "
                f"→ {calculation.required_raw_points}/{calculation.total_raw_points} raw points",
                f"Current: {calculation.current_raw_points}/{calculation.total_raw_points} raw points",
                f"Missing: {calculation.missing_raw_points} raw points",
            ],
            border_color="#2563eb",
        )
    )

    elements.append(Spacer(1, 8))

    elements.append(
        create_pdf_info_card(
            "Average needed",
            [
                f"{average_needed} {plural(average_needed, 'point')} per remaining lesson",
                f"Across {calculation.remaining_lessons} "
                f"{plural(calculation.remaining_lessons, 'lesson')}",
            ],
            border_color="#2563eb",
        )
    )

    elements.append(Spacer(1, 8))

    elements.append(
        create_pdf_info_card(
            "Skippable lessons",
            [
                f"You may skip {skippable_lessons} {plural(skippable_lessons, 'lesson')}",
                f"You still need to complete {lessons_still_needed} "
                f"{plural(lessons_still_needed, 'lesson')}",
            ],
            border_color="#0891b2",
        )
    )

    return elements


def max_effort_pdf_elements(calculation: MaxEffortCalculation) -> list:
    from reportlab.platypus import Spacer

    elements = []

    overview_lines = [
        f"Best reachable: {format_grade_points(calculation.max_reachable_grade_points)} grade points",
        f"Current: {calculation.current_raw_points}/{calculation.total_raw_points} raw points",
        f"Missing: {calculation.missing_raw_points} raw points",
        f"Available remaining raw points: {calculation.available_raw_points}",
    ]

    if (
        calculation.required_percentage is not None
        and calculation.required_raw_points is not None
    ):
        overview_lines.insert(
            1,
            f"Requirement: {format_percentage(calculation.required_percentage)} "
            f"→ {calculation.required_raw_points}/{calculation.total_raw_points} raw points",
        )

    elements.append(
        create_pdf_info_card(
            "Max Reachable With Minimum Effort",
            overview_lines,
            border_color="#c026d3",
        )
    )

    elements.append(Spacer(1, 8))

    elements.append(
        create_pdf_info_card(
            "Minimum effort",
            [
                f"Earn {calculation.minimum_extra_effort} "
                f"{plural(calculation.minimum_extra_effort, 'point')}",
                f"Complete {calculation.lessons_needed} "
                f"{plural(calculation.lessons_needed, 'lesson')}",
            ],
            border_color="#c026d3",
        )
    )

    elements.append(Spacer(1, 8))

    elements.append(
        create_pdf_info_card(
            "Still skippable",
            [
                f"{calculation.lessons_skippable} "
                f"{plural(calculation.lessons_skippable, 'lesson')}",
            ],
            border_color="#0891b2",
        )
    )

    return elements


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

    sorted_scale = sorted(scale, key=lambda point_scale: point_scale.percentage)
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
    story.append(Paragraph("Target Calculation", section_style))

    target_calculation = calculate_target(
        lessons=lessons,
        scale=scale,
        target_points=target_points,
    )

    story.extend(target_calculation_pdf_elements(target_calculation))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Max Reachable With Minimum Effort", section_style))

    max_effort_calculation = calculate_max_reachable_with_min_effort(
        lessons=lessons,
        scale=scale,
    )

    story.extend(max_effort_pdf_elements(max_effort_calculation))

    doc.build(story)


if __name__ == "__main__":
    scale = [
        PointScale(0.60, 1),
        PointScale(0.75, 1.5),
        PointScale(0.85, 2),
    ]

    add_missing_projection_lessons(LESSONS)

    target_points = 1

    target_calculation = calculate_target(
        LESSONS,
        scale,
        target_points,
    )

    max_effort_calculation = calculate_max_reachable_with_min_effort(
        LESSONS,
        scale,
    )

    console.print()
    print_lessons(LESSONS)

    console.print()
    print_scale(scale)

    console.print()
    print_summary(LESSONS, scale)

    console.print()
    console.print(render_target_calculation(target_calculation))

    console.print()
    console.print(render_max_effort_calculation(max_effort_calculation))

    console.print()

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
