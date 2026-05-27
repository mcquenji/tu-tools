from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ue-lessons"))

import main as lessons_main
from config import add_missing_projection_lessons, load_courses
from calculations import calculate_points, calculate_score_milestones, calculate_target
from models import Course, Lesson, PointScale


class LessonProjectionCompletionTests(unittest.TestCase):
    def test_missing_lessons_are_added_as_full_score_projections_to_twelve(self) -> None:
        lessons = [
            Lesson(max_points=6, earned_points=4),
            Lesson(max_points=6, earned_points=5),
        ]

        add_missing_projection_lessons(lessons)

        self.assertEqual(len(lessons), 12)
        self.assertFalse(lessons[0].projected)
        self.assertEqual(
            [lesson.max_points for lesson in lessons],
            [6, 6, 6, 6, 6, 2, 6, 6, 6, 6, 2, 6],
        )
        self.assertTrue(all(lesson.projected for lesson in lessons[2:]))
        self.assertTrue(
            all(
                lesson.earned_points == lesson.max_points for lesson in lessons[2:]
            )
        )

    def test_existing_twelve_lessons_are_not_modified(self) -> None:
        lessons = [
            Lesson(max_points=2 if lesson_number in {6, 11} else 6, earned_points=0)
            for lesson_number in range(1, 13)
        ]

        add_missing_projection_lessons(lessons)

        self.assertEqual(len(lessons), 12)
        self.assertTrue(all(not lesson.projected for lesson in lessons))

    def test_invalid_fixed_schedule_points_are_rejected(self) -> None:
        lessons = [Lesson(max_points=6, earned_points=0) for _ in range(6)]

        with self.assertRaisesRegex(ValueError, "Lesson 6 must have 2 max points"):
            add_missing_projection_lessons(lessons)

    def test_course_loading_completes_the_schedule(self) -> None:
        document = {
            "courses": [
                {
                    "name": "Test",
                    "grade_scale": [
                        {"minimum_percentage": 0.6, "grade_points": 1}
                    ],
                    "lessons": [{"max_points": 6, "earned_points": 3}],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "courses.json"
            path.write_text(json.dumps(document), encoding="utf-8")

            course = load_courses(path)[0]

        self.assertEqual(len(course.lessons), 12)
        self.assertEqual(course.lessons[5].max_points, 2)
        self.assertTrue(course.lessons[-1].projected)

    def test_custom_schedule_controls_autofill(self) -> None:
        document = {
            "courses": [
                {
                    "name": "Custom",
                    "schedule": {
                        "lesson_count": 4,
                        "default_max_points": 8,
                        "point_overrides": [
                            {"lesson_number": 3, "max_points": 3}
                        ],
                    },
                    "grade_scale": [
                        {"minimum_percentage": 0.6, "grade_points": 1}
                    ],
                    "lessons": [{"max_points": 8, "earned_points": 5}],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "courses.json"
            path.write_text(json.dumps(document), encoding="utf-8")

            course = load_courses(path)[0]

        self.assertEqual([lesson.max_points for lesson in course.lessons], [8, 8, 3, 8])
        self.assertTrue(all(lesson.projected for lesson in course.lessons[1:]))

    def test_custom_schedule_rejects_override_outside_lesson_count(self) -> None:
        document = {
            "courses": [
                {
                    "name": "Invalid",
                    "schedule": {
                        "lesson_count": 4,
                        "default_max_points": 8,
                        "point_overrides": [
                            {"lesson_number": 5, "max_points": 3}
                        ],
                    },
                    "grade_scale": [
                        {"minimum_percentage": 0.6, "grade_points": 1}
                    ],
                    "lessons": [],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "courses.json"
            path.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "identify a configured lesson"):
                load_courses(path)

    def test_legacy_configuration_property_names_are_rejected(self) -> None:
        document = {
            "courses": [
                {
                    "name": "Old Names",
                    "scale": [{"percentage": 0.6, "points": 1}],
                    "lessons": [{"max_points": 6, "achieved_points": 3}],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "courses.json"
            path.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "earned_points"):
                load_courses(path)


def course_with_lessons(lessons: list[Lesson]) -> Course:
    return Course(
        name="Test",
        target_grade_points=1,
        lessons=lessons,
        grade_scale=[
            PointScale(0.5, 1),
            PointScale(0.75, 1.5),
            PointScale(0.9, 2),
        ],
    )


class ScoreMilestoneTests(unittest.TestCase):
    def test_identifies_reached_reachable_and_unavailable_thresholds(self) -> None:
        course = course_with_lessons(
            [
                Lesson(max_points=20, earned_points=15),
                Lesson(max_points=10, earned_points=0, projected=True),
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


class ScoreCalculationTests(unittest.TestCase):
    def test_confirmed_grade_uses_full_scheduled_points_total(self) -> None:
        course = Course(
            name="Scheduled",
            lessons=[
                Lesson(max_points=8, earned_points=4),
                Lesson(max_points=8, earned_points=8, projected=True),
                Lesson(max_points=3, earned_points=3, projected=True),
                Lesson(max_points=8, earned_points=8, projected=True),
            ],
            grade_scale=[PointScale(0.5, 1)],
        )

        self.assertEqual(calculate_points(course, include_projections=False), 0)
        self.assertEqual(calculate_points(course), 1)


class TargetCalculationTests(unittest.TestCase):
    def test_possible_target_reports_skippable_lessons(self) -> None:
        course = Course(
            name="Possible",
            target_grade_points=1,
            grade_scale=[PointScale(0.5, 1)],
            lessons=[
                Lesson(max_points=10, earned_points=5),
                Lesson(max_points=5, earned_points=0, projected=True),
                Lesson(max_points=5, earned_points=0, projected=True),
            ],
        )

        target = calculate_target(course)

        self.assertEqual(target.status, "possible")
        self.assertEqual(target.skippable_lessons, 1)
        self.assertEqual(target.lessons_still_needed, 1)

    def test_reached_target_allows_all_remaining_lessons_to_be_skipped(self) -> None:
        course = Course(
            name="Reached",
            target_grade_points=1,
            grade_scale=[PointScale(0.5, 1)],
            lessons=[
                Lesson(max_points=10, earned_points=10),
                Lesson(max_points=5, earned_points=0, projected=True),
            ],
        )

        target = calculate_target(course)

        self.assertEqual(target.status, "reached")
        self.assertEqual(target.skippable_lessons, 1)
        self.assertEqual(target.lessons_still_needed, 0)

    def test_impossible_target_reports_zero_skips(self) -> None:
        course = Course(
            name="Impossible",
            target_grade_points=1,
            grade_scale=[PointScale(0.8, 1)],
            lessons=[
                Lesson(max_points=10, earned_points=0),
                Lesson(max_points=5, earned_points=0, projected=True),
            ],
        )

        target = calculate_target(course)

        self.assertEqual(target.status, "not_possible")
        self.assertEqual(target.skippable_lessons, 0)
        self.assertGreater(target.shortage, 0)

    def test_no_remaining_lessons_reports_zero_skips(self) -> None:
        course = Course(
            name="No Future",
            target_grade_points=1,
            grade_scale=[PointScale(0.8, 1)],
            lessons=[Lesson(max_points=10, earned_points=2)],
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
