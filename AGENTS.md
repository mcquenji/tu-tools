# Agent Notes

This repository is a multi-utility command-line project.

## Structure

- `tu-tools.py` is the top-level CLI dispatcher.
- Each utility owns an implementation directory and is exposed as a subcommand.
- `ue-lessons/` implements the `ue-lessons` subcommand.
- `data/` and `outputs/` are repository-level runtime directories.

## Conventions

- Keep personal/source input data under `data/`; its contents are gitignored.
- Write generated reports and similar artifacts under `outputs/`; its contents
  are gitignored.
- Retain `.gitkeep` files so fresh checkouts contain those directories.
- Add future tools as subcommands rather than standalone root scripts.
- Keep CLI modes usable non-interactively for automation.

## Verification

For changes to `ue-lessons`, run:

```bash
python tu-tools.py ue-lessons --no-pdf
python tu-tools.py ue-lessons --pdf
```
