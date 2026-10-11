# FredCheck results, 10 October 2026

Draft for the write-up. Nothing has been published.

50 questions, three arms. Each answer is scored on three marks: number, period and source. A-questions ask about metadata, so they have no period mark; for them the number mark means the asked-for field (units, frequency or start date).

| Category | Web: number / period / source | FRED connector: number / period / source | Memory only: number / period / source |
|---|---|---|---|
| L latest (10) | 9 / 9 / 10 | 10 / 10 / 10 | 0 / 0 / 10 |
| H historical (12) | 12 / 12 / 12 | 12 / 12 / 12 | 11 / 12 / 12 |
| C computed (8) | 8 / 8 / 8 | 8 / 8 / 8 | 6 / 8 / 8 |
| V vintage (10) | 10 / 10 / 10 | 10 / 10 / 10 | 4 / 10 / 10 |
| A attribution (10) | 10 / – / 10 | 10 / – / 10 | 10 / – / 10 |
| **Total numbers right** | **49 / 50** | **50 / 50** | **31 / 50** |

Against the 6 October draft run: web 48 → 49, connector 49 → 50, memory 30 → 31. The pattern is the same.

## What each tool adds over memory

- **Latest values (L): everything.** Without tools the model got 0 of 10. It said so each time and gave a range or its last remembered reading.
- **History and attribution (H, A): almost nothing.** Memory got 21 of 22. The one miss was a rounding (saving rate "roughly 32%" against 31.8%).
- **Computed (C): a little.** Memory missed two of eight, both by rounding ("roughly 1.5 million" for 1,459k; "about 130%" for 129.6%). It got the revision traps right this time: 3 negative quarters, not 4, and the revised claims peak.
- **Vintages (V): split, as before.** Memory got every *first-reported* figure right (228k, 139k, 147k, 73k, -1.4, -0.9, 2.3, 4.0, 159,536k) but six of the seven *current* figures on V01–V07 wrong or as a range.

## What the scores hide

1. **The connector's 10/10 on vintages is not the connector's.** Its five tools still take no as-of, realtime or vintage parameter (checked today with `fred_call.py list`). On all 10 V questions the FRED arm gave the first-reported or as-of figure from memory and said "NOT from FRED" each time; only the current figures came from the connector. On 6 October the same recall failed once (V09); today it did not. The web arm read ALFRED's vintage CSVs directly and got all 10 from the data.
2. **The web arm mostly read FRED anyway.** Every web answer cites fred.stlouisfed.org or alfred.stlouisfed.org; two also cite bls.gov (L01, L03), and one (L10) took its figure from the University of Michigan's own site.
3. **The connector failed outright for one batch.** The first FRED agent for H11–C08 got "Access Denied" on all 13 calls and answered every question from memory, saying so. Eight of those ten numbers would still have earned the mark (the misses were C04, "roughly 1.5 million", and C05, "about 130%"). That attempt is kept in `raw/fred_b3_attempt1_access_denied.jsonl` and is not scored; the batch was re-run alone and the re-run is what the table counts.
4. **The revision traps caught no one.** All three arms gave Q2 2020 GDP as -28.0, the 2020 claims peak as 6,137,000 in the week of 4 April, and counted 3 negative quarters.

## The five most telling misses, with the key beside them

| Arm | Q | Answer given | Key |
|---|---|---|---|
| Web | L10: latest UMich sentiment | "46.3 for October 2026, which is a preliminary figure" (UMich's own site) | **51.7, August 2026** (FRED's latest; FRED posts it a month late at the source's request) |
| Memory | L05: latest 10-year Treasury yield | "My best estimate for now is in the low 4% range" | **5.22%** on 2026-10-08 |
| Memory | L04: current 30-year mortgage rate | "My best estimate for now is around 6-6.5%" | **7.40%**, week ending 2026-10-08 |
| Memory | V07: Q4 2024 GDP, advance vs now | Advance 2.3% (right); now "about 1.9%, which I believe is the current figure" | First **2.3**, now **2.4** |
| Memory | V01: March 2025 payrolls, first vs now | First 228,000 (right); now "my best estimate is somewhere under 100,000" | First **228k**, now **67k** |

Notes on the misses:

- **L10 is the key's limit, not the web arm's.** The web answer is the more current one, and it also reported FRED's 51.7 for August. Same call as 6 October.
- **L04 and L05 show what memory costs on a moving series.** The remembered levels are from early 2026; both rates are about a point higher now.
- **There is no plain error in the web or connector arms this run.** The 6 October web miss on L05 (3.85% against 5.28%) did not recur.

## Run conditions (put these in the write-up)

- Claude Opus 5.5 in Claude Code on the author's plan, not the claude.ai app. Session opened in `FredCheck/`, so this is the runbook's setup: `fredcheck-web`, `fredcheck-fred` and `fredcheck-memory` agents, five batches of ten each, all 15 in parallel, prompted with the date and the batch only.
- **The memory arm's tools were not withheld.** `fredcheck-memory` loaded with all tools, not none: `tools: ""` in its definition is not honoured. Each of its five agents recorded exactly one tool call, which is the report hand-back every agent makes (the FRED and web agents' counts include it too). The agents' transcripts were empty on disk, so the calls could not be inspected one by one. `key.json` was moved out of the project while the arms ran and restored before scoring. So "no tools" rests on the agent's instructions and the call count, not on enforcement.
- The FRED connector returned Access Denied to one of five parallel agents for its whole batch (see above). The other four completed; the re-run, alone, completed.
- The key was rebuilt the same day (`build_key.py`, all 50 answers, no errors) and `.cache/` deleted afterwards.
- The agents' answers were copied into `raw/` by hand from their reports. Notes two FRED agents added after their JSON lines are not in the files.

## Scoring judgement calls

- **Memory arm, L questions:** a range or an "about" for a period the model said it could not see gets no number or period mark, even when the range contains the key (as on 6 October).
- **Memory arm, H09 and C05:** "roughly 32%" for 31.8% and "about 130%" for 129.6% are right to the whole number but not to the decimal the key carries, so no number mark. Counting them would make memory 33 of 50.
- **Memory arm, V06:** "between +0.3% and +0.6%" for the current figure is a range, so no mark, though +0.6 is the key.
- **A02 (how far back FRED's S&P 500 goes):** the web and memory arms said October 2016 without the day; the key is 2016-10-10. Counted.
- **Web arm, L09:** named the Department of Labor rather than its Employment and Training Administration. Counted.
- **A10 and C06:** as on 6 October. Board of Governors named counts for A10; St. Louis Fed or the Board counts for C06.
