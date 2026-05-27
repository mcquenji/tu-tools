# TU Tools

`tu-tools` is a small command-line collection for university workflows. The
first utility, `ue-lessons`, calculates course lesson points and can generate
a multi-course PDF report with a table of contents.

## Setup

Install dependencies into an environment of your choice:

```bash
python -m pip install -r requirements.txt
```

The repository uses global runtime folders:

- `data/` contains local input files and is gitignored.
- `outputs/` contains generated output files and is gitignored.
- `ue-lessons/` contains the implementation of the lesson reporting utility.

## UE Lessons

The local configuration is read from `data/courses.json`. Create it from this
empty starter document; its `$schema` reference enables JSON validation and
editor completions from [`ue-lessons/schema.json`](ue-lessons/schema.json):

```json
{
  "$schema": "../ue-lessons/schema.json",
  "courses": []
}
```

Add course entries to generate a report. A configured file can support
multiple courses:

```json
{
  "$schema": "../ue-lessons/schema.json",
  "courses": [
    {
      "name": "Analysis",
      "target_grade_points": 1,
      "grade_scale": [
        {"minimum_percentage": 0.6, "grade_points": 1},
        {"minimum_percentage": 0.75, "grade_points": 1.5},
        {"minimum_percentage": 0.85, "grade_points": 2}
      ],
      "lessons": [
        {"max_points": 6, "earned_points": 4},
        {"max_points": 6, "earned_points": 5}
      ]
    }
  ]
}
```

### Filling In Course Data

Add one object in `courses` for each course you want to report on:

- `name` is the course title shown in the terminal report, PDF heading, and
  PDF contents list.
- `target_grade_points` is the grade-point outcome you want the target calculation
  to evaluate. It is optional and defaults to `1`.
- `grade_scale` lists the grade thresholds for the course. Write
  `minimum_percentage` values as
  decimals: `0.6` means 60%, `0.75` means 75%, and so on. The matching
  `grade_points` value is awarded once that threshold is reached.
- `lessons` lists lesson results in chronological order, starting with lesson
  1. You normally only need to enter lessons that have already taken place.

By default, every course is treated as a twelve-lesson schedule. If the
configured list is shorter than twelve lessons, `ue-lessons` fills the missing
trailing lessons as full-score projections:

- Lessons `6` and `11` have `2` maximum points.
- All other lessons have `6` maximum points.
- Enter no more than `12` lessons; explicitly entered `max_points` must follow
  this same schedule.
- An automatically appended lesson has `projected: true` and `earned_points`
  equal to its `max_points`.

This twelve-lesson layout is the default. To use a different course schedule,
add optional `schedule` settings inside that course:

```json
"schedule": {
  "lesson_count": 8,
  "default_max_points": 5,
  "point_overrides": [
    {"lesson_number": 4, "max_points": 2}
  ]
}
```

- `lesson_count` is the total number of lessons to include and auto-fill.
- `default_max_points` is the normal maximum value for each lesson.
- `point_overrides` optionally changes the maximum for specific one-based
  `lesson_number` values; here lesson 4 is worth 2 points instead of 5.

With `schedule`, explicitly entered lessons must use its point pattern and
the remaining trailing positions are projected at their configured maximum.
When `schedule` is omitted, the twelve-lesson default described above is
used.

For each lesson:

- `max_points` is the number of raw points available in that lesson.
- `earned_points` is the number of points actually earned, or the number you
  expect to earn when the lesson is a projection. It cannot be greater than
  `max_points`.
- `projected` is optional. Omit it or set it to `false` for completed,
  confirmed lessons. Set it to `true` when you want to enter your own future
  estimate instead of relying on the automatically added full-score forecast.

For example, after completing the first two lessons, this course input is
enough. Lessons 3 through 12 will be appended automatically as projections:

```json
{
  "name": "Statistics",
  "target_grade_points": 1.5,
  "grade_scale": [
    {"minimum_percentage": 0.6, "grade_points": 1},
    {"minimum_percentage": 0.75, "grade_points": 1.5},
    {"minimum_percentage": 0.85, "grade_points": 2}
  ],
  "lessons": [
    {"max_points": 6, "earned_points": 4},
    {"max_points": 6, "earned_points": 5}
  ]
}
```

Here is a course that uses its own eight-lesson schedule:

```json
{
  "name": "Programming Lab",
  "target_grade_points": 1,
  "schedule": {
    "lesson_count": 8,
    "default_max_points": 5,
    "point_overrides": [
      {"lesson_number": 4, "max_points": 2}
    ]
  },
  "grade_scale": [
    {"minimum_percentage": 0.6, "grade_points": 1},
    {"minimum_percentage": 0.8, "grade_points": 2}
  ],
  "lessons": [
    {"max_points": 5, "earned_points": 4},
    {"max_points": 5, "earned_points": 3}
  ]
}
```

In this example lessons 3 through 8 are auto-filled projections, including
lesson 4 with its overridden `2` maximum points.

To use a more conservative forecast for the next lesson, add it explicitly in
the next chronological position:

```json
"lessons": [
  {"max_points": 6, "earned_points": 4},
  {"max_points": 6, "earned_points": 5},
  {"max_points": 6, "earned_points": 3, "projected": true}
]
```

The generator then auto-fills lessons 4 through 12 using the fixed schedule
above. Because lessons are positional, include projected entries in order when
you want to override forecasts for later future lessons.

### Projections

`projected: true` separates an expected future result from points you have
already confirmed:

- Confirmed results and confirmed grade points use only lessons without
  `projected: true`.
- Projected results and projected grade points include both completed lessons
  and the expected `earned_points` entered for projected lessons, including
  the automatically added full-score projections.
- The target calculation treats projected lessons as the lessons still
  available to complete. It reports how many additional raw points are needed,
  how many remaining lessons are required, and how many may be skipped.
- Skip allowance and milestone reachability are based on the maximum points
  available in remaining projected lessons, not on the estimated
  `earned_points`. This shows what remains mathematically attainable even if
  your current forecast is lower.

As soon as a future lesson has a real result, update `earned_points` with the
earned score and remove `projected` (or set it to `false`) so it becomes part
of the confirmed totals.

Run the utility interactively:

```bash
python tu-tools.py ue-lessons
```

Create the PDF without being prompted:

```bash
python tu-tools.py ue-lessons --pdf
```

PDF reports use the vivid dashboard style by default. Generate the restrained
formal variant explicitly:

```bash
python tu-tools.py ue-lessons --pdf --style formal
```

When you create a PDF through the interactive prompt, the command also asks
which style to use and defaults to `vivid`.

Display results without creating or prompting for a PDF:

```bash
python tu-tools.py ue-lessons --no-pdf
```

By default, the PDF is written to `outputs/lesson_report.pdf`. Use `--data`
or `--output` to override either path.

## Adding Utilities

New utilities should keep their implementation in their own directory and
register a subcommand in `tu-tools.py`. Local inputs and generated artifacts
belong in the shared `data/` and `outputs/` directories.
