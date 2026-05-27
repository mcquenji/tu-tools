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
      "target_points": 1,
      "scale": [
        {"percentage": 0.6, "points": 1},
        {"percentage": 0.75, "points": 1.5},
        {"percentage": 0.85, "points": 2}
      ],
      "lessons": [
        {"max_points": 6, "achieved_points": 4},
        {"max_points": 6, "achieved_points": 6, "projection": true}
      ]
    }
  ]
}
```

Run the utility interactively:

```bash
python tu-tools.py ue-lessons
```

Create the PDF without being prompted:

```bash
python tu-tools.py ue-lessons --pdf
```

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
