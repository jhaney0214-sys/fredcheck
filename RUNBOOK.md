# Running FredCheck

For a Claude Code session opened in this folder when the author says "run FredCheck".
No API key: both arms run as subagents on the author's plan.

**Since 2026-10-12 `rerun.py` does the mechanical steps.** `python rerun.py prepare`
does steps 1 and 2 and writes the batches for step 3, and moves `key.json` out of
the project until the arms are done. `python rerun.py finish` puts it back and does
step 4; run it again after scoring for the table in step 6 and a redrawn `results.svg`.
Steps 3 and 5, and the words of `RESULTS.md`, still need the session.

**Between runs, `py rerun.py monthly`** (added 2026-10-15; `schedule/` sets it to
run on the 15th) rebuilds every answer in memory, compares it with `key.json`
and adds a row to `RESULTS.md`. It leaves `key.json` alone and runs no arm. A
latest value on a new period is expected. A revision to any other answer means
that question's ground truth moved after it was scored: before quoting the old
run, check whether the revision changes a mark. The first check (2026-10-15)
found one: A02, FRED's S&P 500 now starts 2016-10-17, not 2016-10-10. A start
that moves a week in a week fits FRED keeping a rolling ten years of that
series, so A02's answer likely moves every week. Commit `checks/` and `RESULTS.md` by hand.

1. **Check the FRED tools are loaded.** The `fred` server comes from `.mcp.json`
   (gitignored; written by `fred_auth.py`). Its token lasts an hour from when it
   was written. If the FRED tools fail with an auth error, ask the author to run
   `python fred_auth.py --refresh` and restart the session.
   Then check the write-up's headline still holds: `python fred_call.py list` and look
   for an as-of, realtime or vintage parameter on any tool. None on 2026-10-06 or
   2026-10-09 (five tools); if one has appeared, the V finding has to be re-tested, not reused.
2. **Rebuild the key on the day:** `python build_key.py`. It takes no options (`--help` runs a full build). Latest values move.
   **Never show key.json or its values to an arm agent**, and never put an answer in an agent's prompt.
   After the key is built, delete `.cache/`. FRED's terms bar storing its content, so keep only the values the key needs.
3. **Run the three arms.** Send the questions from `questions.json` in batches of 10
   (ids and question text only), one `fredcheck-web`, one `fredcheck-fred` and one
   `fredcheck-memory` agent per batch, all in parallel. Prompt each with just: today's
   date and the batch. `fredcheck-memory` has no tools (`tools: ""`, added 2026-10-06;
   check it loads with none). The connector returns intermittent HTTP 403s under rapid
   calls; agents recover by retrying one call at a time.
4. **Save** each agent's JSON lines to `runs/<date>/web.jsonl`, `fred.jsonl` and `memory.jsonl`
   (add `"arm"` to each row). Re-run any question an agent skipped.
5. **Score** each answer against `key.json` on three marks, recorded in
   `runs/<date>/scores.jsonl` with a one-line reason each:
   - **number**: within rounding of the key (one decimal for rates; ±1k for payroll
     changes in thousands; for `first_vs_now`, both the first-reported and current figures)
   - **period**: names the right month, week, quarter or date (for latest values,
     the latest period in the key)
   - **source**: names the original producer in the key's `source` (or, for questions
     with no metadata spec, the agency behind the series), not just "FRED"
6. **Summarise** in `runs/<date>/RESULTS.md`: the score per arm per category (L, H, C, V, A),
   and the five most telling misses quoted with the key's answer beside them.
   That file is the draft for the public write-up; don't publish anything.

Caveat for the write-up: this is Claude in Claude Code, not the claude.ai app.

## Pre-publish review, 2026-10-08 (publish-legal; not legal advice)

| Check | Finding | Severity | Done |
|---|---|---|---|
| 1 Data | A few values from copyrighted series (S&P, UMich) in key/answers; facts, cited | note; WRITEUP says FRED's terms apply | yes |
| 2 Statements about the St. Louis Fed's product | "No vintage parameter" is checkable: tool schemas listed via `fred_call.py list` | fix: dated "as of 8 October 2026" | yes |
| 2 | Launch date "1 October" taken from the 10-06 notes, not re-read from the Fed's announcement | fixed 2026-10-09: Waller's [FRED Con remarks](https://www.federalreserve.gov/newsevents/speech/waller20261001a.htm) say the connector was "introduced" and demonstrated that day. WRITEUP now says that and links it. The speech also says FRED is working on ALFRED links for AI, and the ask was reworded to match | yes |
| 1 Connector terms ([fred.stlouisfed.org/legal](https://fred.stlouisfed.org/legal/), read 2026-10-09) | "Requirements for FRED® MCP Connector": the notice "This product uses the FRED® MCP Connector but is not endorsed or certified by the Federal Reserve Bank of St. Louis." placed prominently | fix: added verbatim to README and WRITEUP | yes |
| 1 Connector terms | Prohibition (k): no using the connector "in connection with storing, caching, or archiving any portion of the FRED® Services". General (p): no storing, caching or archiving FRED Content without the Bank's prior written consent, with no research exception stated. The repo stores the connector arm's answers (`runs/*/fred.jsonl`, one or two values each). `build_key.py` keeps a 2.2 MB local `.cache/` of whole series (gitignored, fetched from fredgraph, not the connector) | **Author chose (c), 2026-10-09** (changed from (a) the same day): publish as is, about 100 cited values in a non-commercial test, and accept the risk. If the Bank asks for removal, remove the answer text and key values at once. No consent request sent. `.cache/` is still deleted after each key build (step 2) | yes |
| 6 Name | "FRED" is the St. Louis Fed's mark; "FredCheck" could read as official | fix: non-affiliation line in WRITEUP and README | yes |
| 7 Author | Real name; nothing employer-related; not advice | note | yes |
| Repo | Was a folder in a larger private repo | stop: own repo with fresh history | yes, 2026-10-08 |

**From a session opened elsewhere** (as on 2026-10-06), the agents and the `fred` server
do not load. Fallback: general-purpose agents whose prompts set the tool limits;
the FRED arm calls `python fred_call.py <tool> '<json>'` (same five tools, over JSON-RPC);
and `key.json` is moved out of the project while arms run. Tool limits are then
by instruction only, so treat that run as a draft and redo it here before publishing.
