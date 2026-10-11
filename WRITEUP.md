# The FRED connector can't tell you what we knew then

*11 October 2026. Numbers are from the run of 10 October 2026 (`runs/2026-10-10/`). A first, rougher run on 6 October is in `runs/2026-10-06/`.*

On 1 October, at FRED Con, the St. Louis Fed showed off its new official MCP connector for FRED, so AI assistants can pull economic data straight from the source. In his [opening remarks](https://www.federalreserve.gov/newsevents/speech/waller20261001a.htm), Governor Waller said that about half of FRED's visits now come from AI agents, and that FRED's managers don't know whether those agents attribute the data to its original source. I wanted to know whether it makes their answers more accurate, so I wrote 50 questions with answers computed from FRED itself and put them to Claude three ways: with the connector, with web search, and with no tools at all.

Each answer was scored on three things: the right number, the right period, and the right source (the agency that produces the figure, not just "FRED").

| | Connector | Web search | No tools |
|---|---|---|---|
| Latest values (10) | 10 | 9 | 0 |
| Historical values (12) | 12 | 12 | 11 |
| Computed from a series (8) | 8 | 8 | 6 |
| First-reported vs revised (10) | 10 | 10 | 4 |
| Source and units (10) | 10 | 10 | 10 |
| **Numbers right, of 50** | **50** | **49** | **31** |

## What the connector adds

Current numbers. Without tools the model knew it couldn't see this month's jobs report or this week's mortgage rate, and said so. Its guesses were stale: a 30-year mortgage rate "around 6-6.5%" when FRED shows 7.40%, and a 10-year Treasury yield "in the low 4% range" when it is 5.22%. With the connector it got all ten latest values right, with the period and the source.

## What it can't do

The connector only returns today's data. As of 10 October 2026, none of its five tools takes a vintage or as-of date, though FRED's own API has had those (`realtime_start`, `realtime_end`, `vintage_dates`) for years, and ALFRED, the St. Louis Fed's archive of past vintages, is free on the web.

That matters for economic data because the first number is often not the final one. March 2025 payrolls were first reported as +228,000; today the figure is +67,000. June 2025 went from +147,000 to −20,000. Q2 2022 GDP was first reported at −0.9% and is now +0.6%.

Asked about those revisions, the connector arm got 10 of 10. But that score is not the connector's. The first-reported half of every one of those answers came from the model's memory, and it said so each time ("NOT from FRED"). Only the current figures came from the connector. The no-tools arm recalled the same first-reported figures just as well; it missed on the current ones.

Memory is not a source. In the 6 October run the same recall failed once, on December 2024 payrolls as published on 1 February 2025, the kind of figure nobody remembers. These ten revisions are famous ones. A user asking about a less famous one gets a confident number with nothing behind it.

The web arm got all ten from the data, both times, by reading ALFRED's public download files. On these questions an assistant with a browser can show its work and the official connector can't.

## Smaller things

- Neither tool arm made a plain error. The web arm's one lost mark is the University of Michigan sentiment index, which FRED posts a month late at the university's request. The web arm gave the newer figure from Michigan's own site (and FRED's as well); the connector gave FRED's. Both are defensible, and a user should know which one they're getting.
- The web arm mostly read FRED anyway. Every one of its answers cites fred.stlouisfed.org or alfred.stlouisfed.org.
- The connector refused one batch outright. One of five agents calling it in parallel got "Access Denied" on all 13 calls and answered its ten questions from memory, saying so. Re-run alone, the batch went through, and the table counts the re-run. The failed attempt is kept in the repo, unscored.
- History and attribution questions didn't separate the arms. Even without tools the model knew who publishes the mortgage rate and what WTI did on 20 April 2020. A harder set needs less famous series.
- The revision traps caught no one. All three arms gave Q2 2020 GDP as −28.0%, not the −31.4% published in 2020, and the revised peak for 2020 jobless claims.

## Method and limits

- One model (Claude Opus 5.5, in Claude Code, not the claude.ai app), one day, 50 questions. This is a spot check, not a benchmark.
- Answers were scored against values computed from FRED and ALFRED on the day of the run. Latest values move, so the key was rebuilt that day.
- The no-tools arm was not locked out of tools. It was told to answer from memory, and each of its agents made one tool call, the one that hands back its report. The answer key was moved out of the project while the arms ran.
- The no-tools arm lost marks for rounding ("roughly 32%" against 31.8%) and for giving a range. Counting the two rounded answers would make it 33 of 50.
- Questions, answer key, every answer and every score are in the repo: [github.com/jhaney0214-sys/fredcheck](https://github.com/jhaney0214-sys/fredcheck).
- The repo holds only the few data values the questions need, each cited to its FRED series. Some series belong to their producers (S&P Dow Jones Indices, the University of Michigan), and FRED's terms apply to them.
- FRED is a trademark of the Federal Reserve Bank of St. Louis. This project is independent and not affiliated with or endorsed by the St. Louis Fed or Anthropic.
- This product uses the FRED® MCP Connector but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

## The ask

If the connector gained an as-of date, the "what did we know then" question would come from data instead of memory. Governor Waller said FRED is working to link to ALFRED "for AI inquiries to include how data have evolved," so it looks planned. If you work on FRED, I'd like to know whether these 10 vintage questions would make a useful test for it. If you've hit this yourself, tell me your example.
