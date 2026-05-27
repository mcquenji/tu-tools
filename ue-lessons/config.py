from __future__ import annotations

import json
from pathlib import Path

from models import Course, Lesson, PointScale


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
        return [
            Course(
                name=entry["name"],
                target_points=entry.get("target_points", 1),
                lessons=[Lesson(**lesson) for lesson in entry["lessons"]],
                scale=[PointScale(**point_scale) for point_scale in entry["scale"]],
            )
            for entry in entries
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid course configuration in {path}: {error}") from error
