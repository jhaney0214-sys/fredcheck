# Monthly check on Windows

Nothing here is installed. To run `py rerun.py monthly` on the 15th of every
month, open PowerShell in the FredCheck folder and run:

```powershell
(Get-Content schedule\fredcheck-monthly.xml -Raw).Replace('FREDCHECK_DIR', (Get-Location).Path).Replace('UTF-8', 'UTF-16') |
  Set-Content $env:TEMP\fredcheck-monthly.xml -Encoding Unicode
schtasks /Create /TN "FredCheck monthly" /XML $env:TEMP\fredcheck-monthly.xml
```

Run it once now with `schtasks /Run /TN "FredCheck monthly"` and read
`checks\monthly.log`. Remove it with `schtasks /Delete /TN "FredCheck monthly"`.

## What the task does and does not do

- **Does, unattended:** rebuilds every answer from FRED's public CSVs (no API
  key), compares it with `key.json`, writes `checks/<date>.json`, rewrites
  `RESULTS.md`, and deletes `.cache/`. It also lists the connector's tools to
  look for a vintage option, using the saved sign-in.
- **Needs the author:** the connector sign-in once its refresh token stops
  working (`py fred_auth.py` at a browser; the check then says "not checked
  (sign-in expired)" and carries on). Committing and pushing the new row.
- **Does not do at all:** put the questions to the three arms, or score them.
  The arms run as Claude Code subagents in a session opened in this folder, and
  scoring takes judgement (RUNBOOK.md steps 3 to 5). `run.py` could run the arms
  through the Anthropic API, but that is billed per call and is not wired in.

The task's last result in Task Scheduler is the check's exit code: 0 nothing
to look at, 3 a fixed answer was revised or the connector may have gained a
vintage option, 1 the key could not be rebuilt (usually no network).
