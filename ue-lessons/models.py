from __future__ import annotations

from dataclasses import dataclass


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
class Course:
    name: str
    lessons: list[Lesson]
    scale: list[PointScale]
    target_points: float = 1

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Course name cannot be empty.")
        if not self.scale:
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
    percentage: float
    grade_points: float
    required_raw_points: int
    status: str
