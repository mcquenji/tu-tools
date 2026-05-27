from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ue-lessons"))

import main as lessons_main
from calculations import calculate_score_milestones, calculate_target
from models import Course, Lesson, PointScale


def course_with_lessons(lessons: list[Lesson]) -> Course:
    return Course(
        name="Test",
        target_points=1,
        lessons=lessons,
        scale=[
            PointScale(0.5, 1),
            PointScale(0.75, 1.5),
            PointScale(0.9, 2),
        ],
    )


class ScoreMilestoneTests(unittest.TestCase):
    def test_identifies_reached_reachable_and_unavailable_thresholds(self) -> None:
        course = course_with_lessons(
            [
                Lesson(max_points=20, achieved_points=15),
                Lesson(max_points=10, achieved_points=0, projection=True),
            ]
        )

        milestones = calculate_score_milestones(course)

        self.assertEqual(
            [milestone.status for milestone in milestones],
            ["reached", "reachable", "unavailable"],
        )
        self.assertEqual(
            [milestone.required_raw_points for milestone in milestones], [15, 23, 27]
        )


class TargetCalculationTests(unittest.TestCase):
    def test_possible_target_reports_skippable_lessons(self) -> None:
        course = Course(
            name="Possible",
            target_points=1,
            scale=[PointScale(0.5, 1)],
            lessons=[
                Lesson(max_points=10, achieved_points=5),
                Lesson(max_points=5, achieved_points=0, projection=True),
                Lesson(max_points=5, achieved_points=0, projection=True),
            ],
        )

        target = calculate_target(course)

        self.assertEqual(target.status, "possible")
        self.assertEqual(target.skippable_lessons, 1)
        self.assertEqual(target.lessons_still_needed, 1)

    def test_reached_target_allows_all_remaining_lessons_to_be_skipped(self) -> None:
        course = Course(
            name="Reached",
            target_points=1,
            scale=[PointScale(0.5, 1)],
            lessons=[
                Lesson(max_points=10, achieved_points=10),
                Lesson(max_points=5, achieved_points=0, projection=True),
            ],
        )

        target = calculate_target(course)

        self.assertEqual(target.status, "reached")
        self.assertEqual(target.skippable_lessons, 1)
        self.assertEqual(target.lessons_still_needed, 0)

    def test_impossible_target_reports_zero_skips(self) -> None:
        course = Course(
            name="Impossible",
            target_points=1,
            scale=[PointScale(0.8, 1)],
            lessons=[
                Lesson(max_points=10, achieved_points=0),
                Lesson(max_points=5, achieved_points=0, projection=True),
            ],
        )

        target = calculate_target(course)

        self.assertEqual(target.status, "not_possible")
        self.assertEqual(target.skippable_lessons, 0)
        self.assertGreater(target.shortage, 0)

    def test_no_remaining_lessons_reports_zero_skips(self) -> None:
        course = Course(
            name="No Future",
            target_points=1,
            scale=[PointScale(0.8, 1)],
            lessons=[Lesson(max_points=10, achieved_points=2)],
        )

        target = calculate_target(course)

        self.assertEqual(target.status, "not_possible")
        self.assertEqual(target.skippable_lessons, 0)
        self.assertEqual(target.reason, "No remaining lessons.")


class PdfStyleSelectionTests(unittest.TestCase):
    def args(self, **overrides) -> argparse.Namespace:
        values = {
            "data": Path("unused.json"),
            "output": Path("unused.pdf"),
            "pdf": True,
            "no_pdf": False,
            "style": None,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_pdf_generation_defaults_to_vivid_style(self) -> None:
        with (
            patch.object(lessons_main, "load_courses", return_value=[]),
            patch.object(lessons_main, "print_course"),
            patch.object(lessons_main, "create_pdf_report") as create,
        ):
            exit_code = lessons_main.run(self.args())

        self.assertEqual(exit_code, 0)
        self.assertEqual(create.call_args.kwargs["style"], "vivid")

    def test_explicit_formal_style_is_passed_to_renderer(self) -> None:
        with (
            patch.object(lessons_main, "load_courses", return_value=[]),
            patch.object(lessons_main, "print_course"),
            patch.object(lessons_main, "create_pdf_report") as create,
        ):
            lessons_main.run(self.args(style="formal"))

        self.assertEqual(create.call_args.kwargs["style"], "formal")

    def test_interactive_pdf_prompt_defaults_style_to_vivid(self) -> None:
        with (
            patch.object(lessons_main, "load_courses", return_value=[]),
            patch.object(lessons_main, "print_course"),
            patch.object(lessons_main.Confirm, "ask", return_value=True),
            patch.object(lessons_main.Prompt, "ask", return_value="vivid") as prompt,
            patch.object(lessons_main, "create_pdf_report") as create,
        ):
            lessons_main.run(self.args(pdf=False))

        prompt.assert_called_once_with(
            "PDF style", choices=["vivid", "formal"], default="vivid"
        )
        self.assertEqual(create.call_args.kwargs["style"], "vivid")


if __name__ == "__main__":
    unittest.main()
