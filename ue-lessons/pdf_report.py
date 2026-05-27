from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from calculations import (
    calculate_max_reachable_with_min_effort,
    calculate_points,
    calculate_score_milestones,
    calculate_target,
    format_grade_points,
    format_percentage,
)
from models import Course, ScoreMilestone


@dataclass(frozen=True)
class ReportTheme:
    name: str
    accent: str
    heading: str
    muted: str
    border: str
    panel: str
    table_header: str
    projected_row: str
    reached: str
    reachable: str
    unavailable: str
    target: str


THEMES = {
    "vivid": ReportTheme(
        name="Vivid",
        accent="#7c3aed",
        heading="#111827",
        muted="#64748b",
        border="#e9d5ff",
        panel="#faf5ff",
        table_header="#7c3aed",
        projected_row="#f5f3ff",
        reached="#dcfce7",
        reachable="#ede9fe",
        unavailable="#f1f5f9",
        target="#ede9fe",
    ),
    "formal": ReportTheme(
        name="Formal",
        accent="#334155",
        heading="#172033",
        muted="#64748b",
        border="#cbd5e1",
        panel="#f8fafc",
        table_header="#334155",
        projected_row="#f1f5f9",
        reached="#f1f5f9",
        reachable="#f8fafc",
        unavailable="#f8fafc",
        target="#f1f5f9",
    ),
}


def create_pdf_report(
    courses: list[Course], output_path: Path, style: str = "vivid"
) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.graphics.shapes import Circle, Drawing, Line
        from reportlab.platypus import (
            BaseDocTemplate,
            Frame,
            PageBreak,
            PageTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.platypus.tableofcontents import TableOfContents
    except ImportError as error:
        raise RuntimeError(
            "Missing dependency: reportlab. Install it with: pip install reportlab"
        ) from error

    if style not in THEMES:
        raise ValueError(f"Unknown PDF style: {style!r}")
    theme = THEMES[style]
    color = colors.HexColor
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "report_title",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=27 if style == "vivid" else 25,
        leading=32,
        alignment=TA_LEFT,
        textColor=color(theme.heading),
        spaceAfter=6,
    )
    eyebrow_style = ParagraphStyle(
        "eyebrow",
        parent=base["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=color(theme.accent),
        spaceAfter=7,
    )
    course_style = ParagraphStyle(
        "course_heading",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        textColor=color(theme.heading),
        spaceAfter=5,
    )
    section_style = ParagraphStyle(
        "section_heading",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=color(theme.heading),
        spaceBefore=14,
        spaceAfter=7,
    )
    body_style = ParagraphStyle(
        "body",
        parent=base["BodyText"],
        fontSize=9,
        leading=13,
        textColor=color("#334155"),
    )
    note_style = ParagraphStyle(
        "note",
        parent=body_style,
        textColor=color(theme.muted),
        spaceAfter=13,
    )
    card_label_style = ParagraphStyle(
        "card_label",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=color(theme.muted),
    )
    card_value_style = ParagraphStyle(
        "card_value",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=color(theme.heading),
    )
    card_note_style = ParagraphStyle(
        "card_note",
        parent=body_style,
        fontSize=8,
        leading=10,
        textColor=color(theme.muted),
    )
    callout_style = ParagraphStyle(
        "callout",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=color(theme.heading),
    )
    toc_heading = ParagraphStyle("toc_heading", parent=course_style, spaceBefore=25)
    toc_level = [
        ParagraphStyle(
            "toc_course",
            parent=body_style,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=17,
        ),
        ParagraphStyle(
            "toc_section",
            parent=body_style,
            fontSize=9,
            leftIndent=18,
            leading=13,
        ),
    ]

    class ReportDocument(BaseDocTemplate):
        def afterFlowable(self, flowable) -> None:
            if not isinstance(flowable, Paragraph):
                return
            level = {"course_heading": 0, "section_heading": 1}.get(flowable.style.name)
            if level is None:
                return
            text = flowable.getPlainText()
            key = f"heading-{self.seq.nextf('heading')}"
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (level, text, self.page, key))

    def paragraph(value: object, paragraph_style=body_style) -> Paragraph:
        return Paragraph(escape(str(value)), paragraph_style)

    def page_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(color(theme.border))
        canvas.line(doc.leftMargin, 1.15 * cm, A4[0] - doc.rightMargin, 1.15 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(color(theme.muted))
        canvas.drawString(doc.leftMargin, 0.78 * cm, f"{theme.name} report")
        canvas.drawRightString(A4[0] - doc.rightMargin, 0.78 * cm, f"Page {doc.page}")
        canvas.restoreState()

    def kpi_card(label: str, value: str, note: object, background: str) -> Table:
        note_flowable = (
            paragraph(note, card_note_style) if isinstance(note, str) else note
        )
        table = Table(
            [
                [paragraph(label.upper(), card_label_style)],
                [paragraph(value, card_value_style)],
                [note_flowable],
            ],
            colWidths=[4.1 * cm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color(background)),
                    ("BOX", (0, 0), (-1, -1), 0.5, color(theme.border)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("TOPPADDING", (0, 1), (-1, 1), 1),
                    ("BOTTOMPADDING", (0, 2), (-1, 2), 8),
                ]
            )
        )
        return table

    def shrug_seven_note() -> Table:
        icon = Drawing(13, 11)
        ink = color(theme.muted)
        face = color("#facc15")
        icon.add(Circle(7, 7, 3.3, fillColor=face, strokeColor=ink, strokeWidth=0.45))
        icon.add(Circle(5.9, 7.6, 0.35, fillColor=ink, strokeColor=None))
        icon.add(Circle(8.1, 7.6, 0.35, fillColor=ink, strokeColor=None))
        icon.add(Line(6.1, 6.2, 7.9, 6.2, strokeColor=ink, strokeWidth=0.45))
        icon.add(Line(4, 4.6, 1.4, 6.1, strokeColor=ink, strokeWidth=0.7))
        icon.add(Line(1.4, 6.1, 0.3, 5.3, strokeColor=ink, strokeWidth=0.7))
        icon.add(Line(10, 4.6, 12.2, 6.1, strokeColor=ink, strokeWidth=0.7))
        icon.add(Line(12.2, 6.1, 13, 5.3, strokeColor=ink, strokeWidth=0.7))
        table = Table(
            [
                [
                    Paragraph("67%&nbsp;&nbsp;<super>6</super>", card_note_style),
                    icon,
                    Paragraph("<super>7</super>", card_note_style),
                ]
            ],
            colWidths=[1.12 * cm, 13, 0.25 * cm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return table

    def details_table(rows: list[tuple[str, str]]) -> Table:
        data = [
            [paragraph(label, card_label_style), paragraph(value, body_style)]
            for label, value in rows
        ]
        table = Table(data, colWidths=[5.5 * cm, 11.3 * cm], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color(theme.panel)),
                    ("BOX", (0, 0), (-1, -1), 0.5, color(theme.border)),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.25, color(theme.border)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    def lesson_table(course: Course) -> Table:
        rows = [["#", "Status", "Raw points", "Progress"]]
        for index, lesson in enumerate(course.lessons, start=1):
            progress = (
                format_percentage(lesson.earned_points / lesson.max_points)
                if lesson.max_points
                else "0%"
            )
            rows.append(
                [
                    str(index),
                    "Projection" if lesson.projected else "Completed",
                    f"{lesson.earned_points}/{lesson.max_points}",
                    progress,
                ]
            )
        table = Table(
            rows,
            colWidths=[1.1 * cm, 5.4 * cm, 4.3 * cm, 3.5 * cm],
            repeatRows=1,
            hAlign="LEFT",
        )
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), color(theme.table_header)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 1), (-1, -1), color("#334155")),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, color(theme.border)),
            ("TOPPADDING", (0, 0), (-1, -1), 5.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ]
        for index, lesson in enumerate(course.lessons, start=1):
            if lesson.projected:
                table_style.append(
                    ("BACKGROUND", (0, index), (-1, index), color(theme.projected_row))
                )
        table.setStyle(TableStyle(table_style))
        return table

    def milestone_card(milestone: ScoreMilestone, width: float) -> Table:
        unavailable = milestone.status == "unavailable"
        label = f"{format_grade_points(milestone.grade_points)} grade points"
        requirement = (
            f"{format_percentage(milestone.minimum_percentage)} / "
            f"{milestone.required_raw_points} raw points"
        )
        status = milestone.status.title()
        if unavailable:
            label = f"<strike>{escape(label)}</strike>"
            requirement = f"<strike>{escape(requirement)}</strike>"
            value_flowable = Paragraph(label, callout_style)
            requirement_flowable = Paragraph(requirement, card_note_style)
        else:
            value_flowable = paragraph(label, callout_style)
            requirement_flowable = paragraph(requirement, card_note_style)
        background = getattr(theme, milestone.status)
        table = Table(
            [
                [paragraph(status.upper(), card_label_style)],
                [value_flowable],
                [requirement_flowable],
            ],
            colWidths=[width],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color(background)),
                    ("BOX", (0, 0), (-1, -1), 0.5, color(theme.border)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ]
            )
        )
        return table

    def milestones(course: Course) -> list:
        result = []
        items = calculate_score_milestones(course)
        for start in range(0, len(items), 4):
            batch = items[start : start + 4]
            width = 16.8 * cm / len(batch)
            result.append(
                Table(
                    [[milestone_card(item, width - 0.12 * cm) for item in batch]],
                    colWidths=[width] * len(batch),
                    hAlign="LEFT",
                )
            )
            if start + 4 < len(items):
                result.append(Spacer(1, 5))
        return result

    def target_block(course: Course) -> list:
        target = calculate_target(course)
        if target.status == "reached":
            headline = "Target already reached"
        elif target.status == "possible":
            headline = "Target is within reach"
        else:
            headline = "Target is not reachable"
        skip_value = (
            f"{target.skippable_lessons} of {target.remaining_lessons}"
            if target.skippable_lessons is not None
            else "Not applicable"
        )
        hero = Table(
            [
                [
                    paragraph(
                        target.status.replace("_", " ").upper(), card_label_style
                    ),
                    paragraph("LESSONS YOU MAY SKIP", card_label_style),
                ],
                [
                    paragraph(headline, callout_style),
                    paragraph(skip_value, callout_style),
                ],
                [
                    paragraph(
                        f"Target: {format_grade_points(target.target_grade_points)} grade points",
                        card_note_style,
                    ),
                    paragraph(
                        "Based on remaining maximum point capacity", card_note_style
                    ),
                ],
            ],
            colWidths=[10.7 * cm, 6.1 * cm],
        )
        hero.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color(theme.target)),
                    ("BOX", (0, 0), (-1, -1), 0.6, color(theme.border)),
                    ("LINEBEFORE", (1, 0), (1, -1), 0.5, color(theme.border)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 11),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                    ("TOPPADDING", (0, 0), (-1, 0), 9),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
                ]
            )
        )
        requirement = (
            f"{format_percentage(target.required_percentage)} - "
            f"{target.required_raw_points}/{target.total_raw_points} raw points"
            if target.required_percentage is not None
            and target.required_raw_points is not None
            else "No matching threshold is configured"
        )
        rows = [
            ("Requirement", requirement),
            (
                "Confirmed raw points",
                f"{target.current_raw_points}/{target.total_raw_points}",
            ),
            ("Missing raw points", str(target.missing_raw_points)),
            ("Remaining lessons", str(target.remaining_lessons)),
            ("Available remaining raw points", str(target.available_raw_points)),
            (
                "Average needed per remaining lesson",
                (
                    str(target.average_needed_per_lesson)
                    if target.average_needed_per_lesson is not None
                    else "Not applicable"
                ),
            ),
            (
                "Lessons still needed",
                (
                    str(target.lessons_still_needed)
                    if target.lessons_still_needed is not None
                    else "Not applicable"
                ),
            ),
            ("Lessons you may skip", skip_value),
        ]
        if target.shortage is not None:
            rows.append(("Raw-point shortage", str(target.shortage)))
        if target.reason:
            rows.append(("Status detail", target.reason))
        return [hero, Spacer(1, 7), details_table(rows)]

    def maximum_block(course: Course) -> Table:
        maximum = calculate_max_reachable_with_min_effort(course)
        threshold = (
            f"{format_percentage(maximum.required_percentage)} - "
            f"{maximum.required_raw_points}/{maximum.total_raw_points} raw points"
            if maximum.required_percentage is not None
            and maximum.required_raw_points is not None
            else "No configured grade threshold remains reachable"
        )
        return details_table(
            [
                (
                    "Best reachable result",
                    f"{format_grade_points(maximum.max_reachable_grade_points)} grade points",
                ),
                ("Required threshold", threshold),
                ("Confirmed raw points", str(maximum.current_raw_points)),
                ("Available remaining raw points", str(maximum.available_raw_points)),
                ("Additional points needed", str(maximum.minimum_extra_effort)),
                ("Lessons needed", str(maximum.lessons_needed)),
                ("Lessons skippable", str(maximum.lessons_skippable)),
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = ReportDocument(
        str(output_path),
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.55 * cm,
        bottomMargin=1.55 * cm,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates(
        [PageTemplate(id="report", frames=[frame], onPage=page_footer)]
    )

    story = [
        paragraph(f"UE LESSONS / {theme.name.upper()} REPORT", eyebrow_style),
        paragraph("Lesson Points Report", title_style),
        paragraph(
            "Confirmed results, future projections, target feasibility, and "
            "maximum attainable outcomes for configured courses.",
            note_style,
        ),
        paragraph("Contents", toc_heading),
    ]
    toc = TableOfContents()
    toc.levelStyles = toc_level
    story.extend([toc, PageBreak()])

    for course_index, course in enumerate(courses):
        if course_index:
            story.append(PageBreak())
        total = sum(lesson.max_points for lesson in course.lessons)
        confirmed = sum(
            lesson.earned_points for lesson in course.lessons if not lesson.projected
        )
        projected = sum(lesson.earned_points for lesson in course.lessons)
        target = calculate_target(course)
        story.extend(
            [
                paragraph(course.name, course_style),
                paragraph(
                    "Projected lessons affect forecast results and attainable-capacity calculations.",
                    note_style,
                ),
                paragraph("Overview", section_style),
                Table(
                    [
                        [
                            kpi_card(
                                "Confirmed score",
                                f"{confirmed}/{total}",
                                f"{format_percentage(confirmed / total if total else 0)} / "
                                f"{format_grade_points(calculate_points(course, False))} grade points",
                                theme.panel,
                            ),
                            kpi_card(
                                "Projected score",
                                f"{projected}/{total}",
                                (
                                    shrug_seven_note()
                                    if theme.name == "Vivid"
                                    and format_percentage(
                                        projected / total if total else 0
                                    )
                                    == "67%"
                                    else (
                                        "69% (nice)"
                                        if theme.name == "Vivid"
                                        and format_percentage(
                                            projected / total if total else 0
                                        )
                                        == "69%"
                                        else format_percentage(
                                            projected / total if total else 0
                                        )
                                    )
                                ),
                                theme.projected_row,
                            ),
                            kpi_card(
                                "Projected grade",
                                format_grade_points(calculate_points(course)),
                                "grade points",
                                theme.reached,
                            ),
                            kpi_card(
                                "Target status",
                                target.status.replace("_", " ").title(),
                                f"{format_grade_points(target.target_grade_points)} grade points",
                                theme.target,
                            ),
                        ]
                    ],
                    colWidths=[4.25 * cm] * 4,
                    hAlign="LEFT",
                ),
                paragraph("Target Calculation", section_style),
            ]
        )
        story.extend(target_block(course))
        story.extend(
            [
                paragraph("Score Milestones", section_style),
                paragraph(
                    "Milestones are unavailable only when even maximum remaining points "
                    "cannot achieve their threshold. Scores below the first milestone earn 0 grade points.",
                    note_style,
                ),
            ]
        )
        story.extend(milestones(course))
        story.extend(
            [
                paragraph("Lessons", section_style),
                lesson_table(course),
                paragraph("Max Reachable With Minimum Effort", section_style),
                maximum_block(course),
            ]
        )

    doc.multiBuild(story)
