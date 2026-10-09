# FredCheck results, 6 October 2026

Draft for the write-up. Nothing has been published.

50 questions, two arms. Each answer is scored on three marks: number, period and source. A-questions ask about metadata, so they have no period mark; for them the number mark means the asked-for field (units, frequency or start date).

| Category | Web: number / period / source | FRED connector: number / period / source | Memory only, no tools: number / period / source |
|---|---|---|---|
| L latest (10) | 8 / 9 / 10 | 10 / 10 / 10 | 0 / 0 / 10 |
| H historical (12) | 12 / 12 / 12 | 12 / 12 / 12 | 11 / 12 / 12 |
| C computed (8) | 8 / 8 / 8 | 8 / 8 / 8 | 5 / 7 / 8 |
| V vintage (10) | 10 / 10 / 10 | 9 / 10 / 10 | 4 / 10 / 10 |
| A attribution (10) | 10 / – / 10 | 10 / – / 10 | 10 / – / 10 |
| **Total numbers right** | **48 / 50** | **49 / 50** | **30 / 50** |

The memory arm was added after the first two, the same day, with the same questions and key.

## What each tool adds over memory

- **Latest values (L): everything.** Without tools the model got 0 of 10. It said so each time and gave a range, which is the honest failure.
- **History and attribution (H, A): almost nothing.** Memory got 21 of 22, and the one miss was a rounding (saving rate "about 32%" against 31.8%). These questions are too well known to separate the arms. The next question set should use less famous series and dates.
- **Computed (C): some.** Memory missed three of eight. One miss is the revision trap the set was built for: it counted Q2 2022 as a negative quarter, but current data has it at +0.6.
- **Vintages (V): split.** Memory got every *first-reported* figure right (228k, 139k, 147k, 73k, -1.4, -0.9, 2.3) but most *current* figures wrong. The connector supplies today's value and nothing older. So on the V questions, the connector arm's correct answers are memory for the first print plus the connector for today's value.

## What the scores hide

1. **The FRED connector cannot read vintages.** Its tools return only today's data (realtime_start = realtime_end = 2026-10-06). For 9 of the 10 V questions, the FRED arm got the first-reported figure right *from memory* and said so. On the one where memory failed (V09), it was wrong. The connector's 9/10 on vintages is really the model's recall plus today's data. The web arm reached ALFRED's vintage CSVs directly and got all 10 from the data itself.
2. **The web arm mostly read FRED anyway.** Almost every web answer cites fred.stlouisfed.org or alfred.stlouisfed.org files. In practice "web vs FRED" here means "FRED's public files vs FRED's MCP tools", not FRED against the open web.
3. **The revision traps all failed to catch anyone.** Both arms gave Q2 2020 GDP as -28.0, 2020 peak claims as 6.137M in the week of 4 April, the 2022 Q2 GDP flip and every payroll revision correctly.

## The misses, with the key beside them

| Arm | Q | Answer given | Key |
|---|---|---|---|
| Web | L05: latest 10-year Treasury yield | 3.85% on 2026-10-02 | **5.28%** on 2026-10-02 (FRED DGS10; checked against fredgraph after scoring) |
| Web | L10: latest UMich sentiment | 48.1, September 2026 (UMich's own site) | **51.7, August 2026** (FRED's latest; FRED posts it a month late at the source's request) |
| FRED | V09: Dec 2024 payrolls as of 1 Feb 2025 | ~159,222k, "from memory, not from FRED" | **159,536k** (ALFRED vintage) |

Notes on the misses:

- **L05 is the only plain error in the run.** The 3.85% matches no recent value in the series, which ran from 5.17 to 5.29 over the last week of September. The web agent cited FRED's DGS10.txt; it most likely misread that file or never got its contents and filled the gap.
- **L10 is the key's limit, not the web arm's.** The web answer is the more current one. In the write-up, say that FRED lags UMich by a month rather than counting this as a web mistake.
- **V09 is the connector's real gap.** No as-of-date parameter means a vintage question falls back on memory.

## Run conditions (put these in the write-up)

- Claude Opus 5.5 in Claude Code on the author's plan, not the claude.ai app. Each arm ran as five parallel general-purpose subagents of ten questions each.
- Not the runbook's setup. The session was opened outside `FredCheck/`, so the `fredcheck-web`/`fredcheck-fred` agents and the `fred` MCP server could not load. Instead:
  - The web arm was told to use only WebSearch/WebFetch.
  - The FRED arm was told to use only `python fred_call.py`, a thin JSON-RPC client calling the same five tools on `mcp.stlouisfed.org`.
  - The tool limits were set in the prompts, not enforced. `key.json` was moved out of the project during both arms and restored before scoring.
- The FRED connector returned intermittent HTTP 403s under rapid calls. Two agents reported this; both recovered by retrying one call at a time.
- The key was rebuilt the same morning (`build_key.py`).

- **Memory arm:** five general-purpose subagents told to call no tools. Each recorded exactly one tool call. That is most likely the report hand-back, but not verified: the clean re-run's `fredcheck-memory` agent has no tools at all, and that run settles it. Its cutoff sits in early to mid 2026, so it knows the 2025 revisions but not the latest 2026 releases.
- **The connector's tools:** checked directly. None takes `realtime_start`, `realtime_end` or `vintage_dates`, the parameters FRED's own API uses for vintages.

## Scoring judgement calls

- **Memory arm, L questions:** a range or an "about" for a period the model said it could not see gets no number or period mark, even when the range contains the key.
- **Memory arm, V07:** "2.4 to 2.5" for the current figure is a range, so no mark.

- **A10 (effective fed funds source):** both arms named the NY Fed for EFFR and the Board of Governors for FEDFUNDS/DFF. Both got the source mark, since the key's answer (Board) is named.
- **C06:** T10Y2Y is a St. Louis Fed calculation from Board H.15 yields, so either name counts.
