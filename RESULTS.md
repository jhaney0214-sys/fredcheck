# FredCheck results by date

Written by `py rerun.py table` (and by `monthly`) from `runs/*/scores.jsonl` and
`checks/*.json`. Do not edit by hand.

## Scored runs

Numbers right out of the 50 questions. Each run's own `RESULTS.md` has the
period and source marks and every judgement call.

| Run | FRED connector | Web search | No tools | Note |
|---|---|---|---|---|
| [2026-10-06](runs/2026-10-06/RESULTS.md) | 49 | 48 | 30 | draft: run from a session opened outside the project, tool limits by instruction only |
| [2026-10-10](runs/2026-10-10/RESULTS.md) | 50 | 49 | 31 | the run WRITEUP.md reports |

## Monthly ground-truth checks

Each check rebuilds every answer from FRED's public data and compares it with
the key the last scored run was marked against. It does not put the questions
to any assistant. A latest-value question on a new period is expected; a
revision to any other answer means that question's ground truth moved after
it was scored.

| Checked | Against | Unchanged | Latest values on a new period | Revised answers | Errors | Connector |
|---|---|---|---|---|---|---|
| 2026-10-15 | 2026-10-10 key | 45 | 4 | A02 first_date 2016-10-10 → 2016-10-17 | none | no vintage option (5 tools) |
