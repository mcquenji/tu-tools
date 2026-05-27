from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from models import Course, Lesson, PointScale

DEFAULT_TOTAL_LESSONS = 12
DEFAULT_LESSON_POINTS = 6
DEFAULT_POINT_OVERRIDES = {6: 2, 11: 2}


@dataclass(frozen=True)
class LessonSchedule:
    lesson_count: int
    default_max_points: int
    point_overrides: dict[int, int]

    def max_points_for_lesson(self, lesson_number: int) -> int:
        return self.point_overrides.get(lesson_number, self.default_max_points)


DEFAULT_SCHEDULE = LessonSchedule(
    lesson_count=DEFAULT_TOTAL_LESSONS,
    default_max_points=DEFAULT_LESSON_POINTS,
    point_overrides=DEFAULT_POINT_OVERRIDES,
)


def parse_lesson_schedule(entry: dict) -> LessonSchedule:
    configured = entry.get("schedule")
    if configured is None:
        return DEFAULT_SCHEDULE
    if not isinstance(configured, dict):
        raise ValueError("'schedule' must be an object.")

    lesson_count = configured["lesson_count"]
    default_max_points = configured["default_max_points"]
    point_overrides = configured.get("point_overrides", [])
    if (
        not isinstance(lesson_count, int)
        or isinstance(lesson_count, bool)
        or lesson_count < 1
    ):
        raise ValueError("'schedule.lesson_count' must be a positive integer.")
    if (
        not isinstance(default_max_points, int)
        or isinstance(default_max_points, bool)
        or default_max_points < 0
    ):
        raise ValueError("'schedule.default_max_points' must be a non-negative integer.")
    if not isinstance(point_overrides, list):
        raise ValueError("'schedule.point_overrides' must be a list.")

    override_values = {}
    for point_override in point_overrides:
        if not isinstance(point_override, dict):
            raise ValueError("Each schedule point override must be an object.")
        lesson_id = point_override["lesson_number"]
        override_points = point_override["max_points"]
        if (
            not isinstance(lesson_id, int)
            or isinstance(lesson_id, bool)
            or not 1 <= lesson_id <= lesson_count
        ):
            raise ValueError(
                "'schedule.point_overrides[].lesson_number' must identify a "
                "configured lesson."
            )
        if lesson_id in override_values:
            raise ValueError(f"Lesson {lesson_id} has more than one point override.")
        if (
            not isinstance(override_points, int)
            or isinstance(override_points, bool)
            or override_points < 0
        ):
            raise ValueError(
                "'schedule.point_overrides[].max_points' must be a "
                "non-negative integer."
            )
        override_values[lesson_id] = override_points

    return LessonSchedule(
        lesson_count=lesson_count,
        default_max_points=default_max_points,
        point_overrides=override_values,
    )


def parse_lesson(entry: dict) -> Lesson:
    return Lesson(
        max_points=entry["max_points"],
        earned_points=entry["earned_points"],
        projected=entry.get("projected", False),
    )


def parse_grade_threshold(entry: dict) -> PointScale:
    return PointScale(
        minimum_percentage=entry["minimum_percentage"],
        grade_points=entry["grade_points"],
    )


def add_missing_projection_lessons(
    lessons: list[Lesson], schedule: LessonSchedule = DEFAULT_SCHEDULE
) -> None:
    if len(lessons) > schedule.lesson_count:
        raise ValueError(f"A course may contain at most {schedule.lesson_count} lessons.")

    for lesson_number, lesson in enumerate(lessons, start=1):
        expected_max_points = schedule.max_points_for_lesson(lesson_number)
        if lesson.max_points != expected_max_points:
            raise ValueError(
                f"Lesson {lesson_number} must have {expected_max_points} max points."
            )

    while len(lessons) < schedule.lesson_count:
        lesson_number = len(lessons) + 1
        max_points = schedule.max_points_for_lesson(lesson_number)
        lessons.append(
            Lesson(
                max_points=max_points,
                earned_points=max_points,
                projected=True,
            )
        )


def load_courses(path: Path) -> list[Course]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Course configuration not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error

    entries = document.get("courses")
    if not isinstance(entries, list):
        raise ValueError("Course configuration must have a 'courses' list.")

    try:
        courses = []
        for entry in entries:
            lessons = [parse_lesson(lesson) for lesson in entry["lessons"]]
            add_missing_projection_lessons(lessons, parse_lesson_schedule(entry))
            courses.append(
                Course(
                    name=entry["name"],
                    target_grade_points=entry.get("target_grade_points", 1),
                    lessons=lessons,
                    grade_scale=[
                        parse_grade_threshold(threshold)
                        for threshold in entry["grade_scale"]
                    ],
                )
            )
        return courses
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid course configuration in {path}: {error}") from error
