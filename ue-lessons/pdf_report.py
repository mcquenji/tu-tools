from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from calculations import (
    calculate_max_reachable_with_min_effort,
    calculate_target,
    format_grade_points,
    format_percentage,
    get_summary_rows,
)
from models import Course


def create_pdf_report(courses: list[Course], output_path: Path) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
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

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "report_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=20,
    )
    course_style = ParagraphStyle(
        "course_heading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=24,
        textColor=colors.HexColor("#111827"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "section_heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#111827"),
        spaceBefore=14,
        spaceAfter=8,
    )
    note_style = ParagraphStyle(
        "note",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6b7280"),
        spaceAfter=12,
    )
    toc_heading = ParagraphStyle("toc_heading", parent=course_style, spaceBefore=16)
    toc_level = [
        ParagraphStyle(
            "toc_course",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leftIndent=0,
            firstLineIndent=0,
            leading=16,
        ),
        ParagraphStyle(
            "toc_section",
            parent=styles["BodyText"],
            fontSize=9,
            leftIndent=18,
            firstLineIndent=0,
            leading=13,
        ),
    ]

    class ReportDocument(BaseDocTemplate):
        def afterFlowable(self, flowable) -> None:
            if not isinstance(flowable, Paragraph):
                return
            levels = {"course_heading": 0, "section_heading": 1}
            level = levels.get(flowable.style.name)
            if level is None:
                return
            text = flowable.getPlainText()
            key = f"heading-{self.seq.nextf('heading')}"
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (level, text, self.page, key))

    def page_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f"Page {doc.page}")
        canvas.restoreState()

    def data_table(rows: list[list[str]], widths: list[float]) -> Table:
        table = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f9fafb")],
                    ),
                ]
            )
        )
        return table

    def detail_table(rows: list[tuple[str, str]]) -> Table:
        table = Table([[label, value] for label, value in rows], colWidths=[6 * cm, 7 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = ReportDocument(
        str(output_path),
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=page_footer)])

    story = [
        Paragraph("Lesson Points Report", title_style),
        Paragraph(
            "Generated from the configured courses. Projected lessons are included "
            "in projected results and availability calculations.",
            note_style,
        ),
        Paragraph("Contents", toc_heading),
    ]
    toc = TableOfContents()
    toc.levelStyles = toc_level
    story.extend([toc, PageBreak()])

    for course_index, course in enumerate(courses):
        if course_index:
            story.append(PageBreak())
        story.append(Paragraph(escape(course.name), course_style))

        story.append(Paragraph("Summary", section_style))
        story.append(detail_table(get_summary_rows(course)))

        story.append(Paragraph("Lessons", section_style))
        lesson_rows = [["#", "Status", "Raw points", "Progress"]]
        for index, lesson in enumerate(course.lessons, start=1):
            status = "Projection" if lesson.projection else "Completed"
            progress = (
                format_percentage(lesson.achieved_points / lesson.max_points)
                if lesson.max_points
                else "0%"
            )
            lesson_rows.append(
                [str(index), status, f"{lesson.achieved_points}/{lesson.max_points}", progress]
            )
        story.append(data_table(lesson_rows, [1.2 * cm, 4 * cm, 4 * cm, 3 * cm]))

        story.append(Paragraph("Point Scale", section_style))
        scale_rows = [["Required", "Grade points"]]
        minimum = min(point_scale.percentage for point_scale in course.scale)
        scale_rows.append([f"< {format_percentage(minimum)}", "0"])
        for point_scale in sorted(course.scale, key=lambda item: item.percentage):
            scale_rows.append(
                [format_percentage(point_scale.percentage), format_grade_points(point_scale.points)]
            )
        story.append(data_table(scale_rows, [5 * cm, 5 * cm]))

        target = calculate_target(course)
        story.append(Paragraph("Target Calculation", section_style))
        target_rows = [
            ("Target", f"{format_grade_points(target.target_grade_points)} grade points"),
            ("Status", target.status.replace("_", " ").title()),
            ("Current", f"{target.current_raw_points}/{target.total_raw_points} raw points"),
            ("Missing", f"{target.missing_raw_points} raw points"),
        ]
        if target.required_percentage is not None and target.required_raw_points is not None:
            target_rows.insert(
                1,
                (
                    "Requirement",
                    f"{format_percentage(target.required_percentage)} - "
                    f"{target.required_raw_points}/{target.total_raw_points} raw points",
                ),
            )
        if target.lessons_still_needed is not None:
            target_rows.append(("Lessons still needed", str(target.lessons_still_needed)))
        if target.reason:
            target_rows.append(("Reason", target.reason))
        story.append(detail_table(target_rows))

        maximum = calculate_max_reachable_with_min_effort(course)
        story.append(Paragraph("Max Reachable With Minimum Effort", section_style))
        story.append(
            detail_table(
                [
                    (
                        "Best reachable",
                        f"{format_grade_points(maximum.max_reachable_grade_points)} grade points",
                    ),
                    ("Additional points needed", str(maximum.minimum_extra_effort)),
                    ("Lessons needed", str(maximum.lessons_needed)),
                    ("Lessons skippable", str(maximum.lessons_skippable)),
                ]
            )
        )

    doc.multiBuild(story)
