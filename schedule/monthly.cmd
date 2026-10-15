@echo off
rem FredCheck's monthly ground-truth check, for Windows Task Scheduler.
rem Runs from the project folder whatever the task's start directory is, and
rem appends its output to checks\monthly.log (gitignored). It commits nothing.
cd /d "%~dp0.."
if not exist checks mkdir checks
set PYTHONUTF8=1
echo ==== %DATE% %TIME% >> checks\monthly.log
py rerun.py monthly >> checks\monthly.log 2>&1
