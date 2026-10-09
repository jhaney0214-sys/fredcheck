# The FRED connector can't tell you what we knew then

*Draft, 2026-10-08. Numbers are from a first run on 2026-10-06 and get replaced by the clean re-run before this goes anywhere.*

On 1 October, at FRED Con, the St. Louis Fed showed off its new official MCP connector for FRED, so AI assistants can pull economic data straight from the source. In his [opening remarks](https://www.federalreserve.gov/newsevents/speech/waller20261001a.htm), Governor Waller said that about half of FRED's visits now come from AI agents, and that FRED's managers don't know whether those agents attribute the data to its original source. I wanted to know whether it makes their answers more accurate, so I wrote 50 questions with answers computed from FRED itself and put them to Claude three ways: with the connector, with web search, and with no tools at all.

Each answer was scored on three things: the right number, the right period, and the right source (the agency that produces the figure, not just "FRED").

| | Connector | Web search | No tools |
|---|---|---|---|
| Latest values (10) | 10 | 8 | 0 |
| Historical values (12) | 12 | 12 | 11 |
| Computed from a series (8) | 8 | 8 | 5 |
| First-reported vs revised (10) | 9 | 10 | 4 |
| Source and units (10) | 10 | 10 | 10 |
| **Numbers right, of 50** | **49** | **48** | **30** |

## What the connector adds

Current numbers. Without tools the model knew it couldn't see this month's jobs report or this week's mortgage rate, and said so. With the connector it got all ten latest values right, with the period and the source.

## What it can't do

The connector only returns today's data. As of 8 October 2026, none of its five tools takes a vintage or as-of date, though FRED's own API has had those (`realtime_start`, `realtime_end`, `vintage_dates`) for years, and ALFRED, the St. Louis Fed's archive of past vintages, is free on the web.

That matters for economic data because the first number is often not the final one. March 2025 payrolls were first reported as +228,000; today the figure is +67,000. June 2025 went from +147,000 to −20,000. Q2 2022 GDP was first reported at −0.9% and is now +0.6%.

Asked about those revisions, the connector arm got 9 of 10. But the first-reported half of every one of those answers came from the model's memory, and it said so. It was right because these revisions are famous. The one it missed (December 2024 payrolls as published on 1 February 2025) is the kind nobody remembers.

The web arm got all ten from the data, by reading ALFRED's public download files. On these questions an assistant with a browser beat the official connector.

## Smaller things

- The web arm made the run's only plain error: a 10-year Treasury yield of 3.85% when FRED shows 5.28%.
- FRED posts the University of Michigan sentiment index a month late, at the university's request. The web arm gave the newer figure from Michigan's own site; the connector gave FRED's. Both are defensible, and a user should know which one they're getting.
- The connector returned intermittent HTTP 403 errors under rapid calls. Retrying one call at a time worked.
- History and attribution questions didn't separate the arms. Even without tools the model knew who publishes the mortgage rate and what WTI did on 20 April 2020. A harder set needs less famous series.

## Method and limits

- One model (Claude, in Claude Code), one day, 50 questions. This is a spot check, not a benchmark.
- Answers were scored against values computed from FRED and ALFRED on the morning of the run. Latest values move, so the key was rebuilt that day.
- Questions, answer key, every answer and every score are in the repo: [link].
- The repo holds only the few data values the questions need, each cited to its FRED series. Some series belong to their producers (S&P Dow Jones Indices, the University of Michigan), and FRED's terms apply to them.
- FRED is a trademark of the Federal Reserve Bank of St. Louis. This project is independent and not affiliated with or endorsed by the St. Louis Fed or Anthropic.
- This product uses the FRED® MCP Connector but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

## The ask

If the connector gained an as-of date, the "what did we know then" question would come from data instead of memory. Governor Waller said FRED is working to link to ALFRED "for AI inquiries to include how data have evolved," so it looks planned. If you work on FRED, I'd like to know whether these 10 vintage questions would make a useful test for it. If you've hit this yourself, tell me your example.
