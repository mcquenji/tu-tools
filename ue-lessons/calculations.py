from __future__ import annotations

from math import ceil

from models import (
    Course,
    MaxEffortCalculation,
    ScoreMilestone,
    TargetCalculation,
)


def format_grade_points(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:.1f}"


def format_percentage(value: float) -> str:
    return f"{value * 100:.0f}%"


def plural(value: int, singular: str, plural_form: str | None = None) -> str:
    return singular if value == 1 else (plural_form or f"{singular}s")


def calculate_points(course: Course, include_projections: bool = True) -> float:
    total = sum(lesson.max_points for lesson in course.lessons)
    if total == 0:
        return 0

    achieved = sum(
        lesson.earned_points
        for lesson in course.lessons
        if include_projections or not lesson.projected
    )
    percentage = achieved / total
    for point_scale in sorted(
        course.grade_scale,
        key=lambda point_scale: point_scale.minimum_percentage,
        reverse=True,
    ):
        if percentage >= point_scale.minimum_percentage:
            return point_scale.grade_points
    return 0


def calculate_target(course: Course) -> TargetCalculation:
    lessons = course.lessons
    matching_scales = [
        point_scale
        for point_scale in course.grade_scale
        if point_scale.grade_points >= course.target_grade_points
    ]
    total_raw_points = sum(lesson.max_points for lesson in lessons)
    current_raw_points = sum(
        lesson.earned_points for lesson in lessons if not lesson.projected
    )
    projection_lessons = [lesson for lesson in lessons if lesson.projected]
    remaining_lessons = len(projection_lessons)
    available_raw_points = sum(lesson.max_points for lesson in projection_lessons)
    common = {
        "target_grade_points": course.target_grade_points,
        "total_raw_points": total_raw_points,
        "current_raw_points": current_raw_points,
        "remaining_lessons": remaining_lessons,
        "available_raw_points": available_raw_points,
    }

    if not matching_scales:
        return TargetCalculation(
            status="not_possible",
            required_percentage=None,
            required_raw_points=None,
            missing_raw_points=0,
            average_needed_per_lesson=None,
            skippable_lessons=None,
            lessons_still_needed=None,
            reason="No matching point scale exists.",
            **common,
        )

    target_scale = min(
        matching_scales, key=lambda point_scale: point_scale.minimum_percentage
    )
    required_raw_points = ceil(target_scale.minimum_percentage * total_raw_points)
    missing_raw_points = max(0, required_raw_points - current_raw_points)
    required = {
        "required_percentage": target_scale.minimum_percentage,
        "required_raw_points": required_raw_points,
        "missing_raw_points": missing_raw_points,
    }

    if missing_raw_points == 0:
        return TargetCalculation(
            status="reached",
            average_needed_per_lesson=0,
            skippable_lessons=remaining_lessons,
            lessons_still_needed=0,
            reason="Target already reached.",
            **required,
            **common,
        )
    if remaining_lessons == 0:
        return TargetCalculation(
            status="not_possible",
            average_needed_per_lesson=None,
            skippable_lessons=0,
            lessons_still_needed=None,
            reason="No remaining lessons.",
            **required,
            **common,
        )
    if missing_raw_points > available_raw_points:
        return TargetCalculation(
            status="not_possible",
            average_needed_per_lesson=None,
            skippable_lessons=0,
            lessons_still_needed=None,
            reason="Not enough remaining raw points.",
            shortage=missing_raw_points - available_raw_points,
            **required,
            **common,
        )

    skipped_points = 0
    skipped_lessons = 0
    for lesson in sorted(projection_lessons, key=lambda lesson: lesson.max_points):
        if available_raw_points - skipped_points - lesson.max_points >= missing_raw_points:
            skipped_points += lesson.max_points
            skipped_lessons += 1
        else:
            break

    return TargetCalculation(
        status="possible",
        average_needed_per_lesson=ceil(missing_raw_points / remaining_lessons),
        skippable_lessons=skipped_lessons,
        lessons_still_needed=remaining_lessons - skipped_lessons,
        **required,
        **common,
    )


def calculate_max_reachable_with_min_effort(course: Course) -> MaxEffortCalculation:
    projection_lessons = [lesson for lesson in course.lessons if lesson.projected]
    total_raw_points = sum(lesson.max_points for lesson in course.lessons)
    current_raw_points = sum(
        lesson.earned_points for lesson in course.lessons if not lesson.projected
    )
    available_raw_points = sum(lesson.max_points for lesson in projection_lessons)
    max_possible_raw_points = current_raw_points + available_raw_points
    reachable_scales = [
        point_scale
        for point_scale in course.grade_scale
        if max_possible_raw_points
        >= ceil(point_scale.minimum_percentage * total_raw_points)
    ]
    common = {
        "total_raw_points": total_raw_points,
        "current_raw_points": current_raw_points,
        "available_raw_points": available_raw_points,
    }

    if not reachable_scales:
        return MaxEffortCalculation(
            max_reachable_grade_points=0,
            required_percentage=None,
            required_raw_points=None,
            missing_raw_points=0,
            minimum_extra_effort=0,
            lessons_needed=0,
            lessons_skippable=len(projection_lessons),
            **common,
        )

    best_scale = max(reachable_scales, key=lambda point_scale: point_scale.grade_points)
    required_raw_points = ceil(best_scale.minimum_percentage * total_raw_points)
    missing_raw_points = max(0, required_raw_points - current_raw_points)
    used_lessons = 0
    gathered_points = 0
    for lesson in sorted(
        projection_lessons, key=lambda lesson: lesson.max_points, reverse=True
    ):
        if gathered_points >= missing_raw_points:
            break
        gathered_points += lesson.max_points
        used_lessons += 1

    return MaxEffortCalculation(
        max_reachable_grade_points=best_scale.grade_points,
        required_percentage=best_scale.minimum_percentage,
        required_raw_points=required_raw_points,
        missing_raw_points=missing_raw_points,
        minimum_extra_effort=missing_raw_points,
        lessons_needed=used_lessons,
        lessons_skippable=len(projection_lessons) - used_lessons,
        **common,
    )


def calculate_score_milestones(course: Course) -> list[ScoreMilestone]:
    total_raw_points = sum(lesson.max_points for lesson in course.lessons)
    confirmed_raw_points = sum(
        lesson.earned_points for lesson in course.lessons if not lesson.projected
    )
    maximum_raw_points = confirmed_raw_points + sum(
        lesson.max_points for lesson in course.lessons if lesson.projected
    )
    milestones = []
    for point_scale in sorted(
        course.grade_scale, key=lambda item: item.minimum_percentage
    ):
        required_raw_points = ceil(point_scale.minimum_percentage * total_raw_points)
        if confirmed_raw_points >= required_raw_points:
            status = "reached"
        elif maximum_raw_points >= required_raw_points:
            status = "reachable"
        else:
            status = "unavailable"
        milestones.append(
            ScoreMilestone(
                minimum_percentage=point_scale.minimum_percentage,
                grade_points=point_scale.grade_points,
                required_raw_points=required_raw_points,
                status=status,
            )
        )
    return milestones


def get_summary_rows(course: Course) -> list[tuple[str, str]]:
    total = sum(lesson.max_points for lesson in course.lessons)
    confirmed = sum(
        lesson.earned_points for lesson in course.lessons if not lesson.projected
    )
    projected = sum(lesson.earned_points for lesson in course.lessons)
    return [
        ("Confirmed raw points", f"{confirmed}/{total}"),
        ("Confirmed percentage", format_percentage(confirmed / total if total else 0)),
        ("Confirmed grade points", format_grade_points(calculate_points(course, False))),
        ("Projected raw points", f"{projected}/{total}"),
        ("Projected percentage", format_percentage(projected / total if total else 0)),
        ("Projected grade points", format_grade_points(calculate_points(course))),
    ]
