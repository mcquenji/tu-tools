from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PointScale:
    minimum_percentage: float
    grade_points: float

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_percentage <= 1:
            raise ValueError("Percentage must be between 0 and 1.")


@dataclass
class Lesson:
    max_points: int
    earned_points: int
    projected: bool = False

    def __post_init__(self) -> None:
        if self.max_points < 0:
            raise ValueError("Max points cannot be negative.")
        if self.earned_points < 0:
            raise ValueError("Achieved points cannot be negative.")
        if self.earned_points > self.max_points:
            raise ValueError(
                f"Earned points ({self.earned_points}) cannot exceed "
                f"max points ({self.max_points})."
            )


@dataclass
class Course:
    name: str
    lessons: list[Lesson]
    grade_scale: list[PointScale]
    target_grade_points: float = 1

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Course name cannot be empty.")
        if not self.grade_scale:
            raise ValueError(f"Course {self.name!r} must define a point scale.")


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


@dataclass
class ScoreMilestone:
    minimum_percentage: float
    grade_points: float
    required_raw_points: int
    status: str
