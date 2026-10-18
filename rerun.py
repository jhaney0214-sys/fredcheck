"""The mechanical half of a dated re-run. The arms and the scoring still need a
Claude Code session opened in this folder (RUNBOOK.md, steps 3 and 5); this
does everything before and after them.

    python rerun.py prepare            # today's date; or: prepare 2026-11-10
    ... run the three arms and score them in the session ...
    python rerun.py finish             # the run prepared last
    python rerun.py tally 2026-10-10   # just the table for a scored run

prepare: renews the FRED token, checks the connector's tools for a vintage or
as-of option, rebuilds key.json, deletes .cache/, writes the five question
batches (ids and text only) and moves key.json out of the project so no arm
can read it.

finish: puts key.json back, joins the agents' raw answers into one file per
arm, and, once scores.jsonl exists, prints the results table beside the
previous run's and redraws results.svg.

    py rerun.py monthly                # the unattended part, for a scheduled task
    py rerun.py table                  # just rewrite RESULTS.md

monthly: rebuilds the key in memory from FRED's public CSVs (no API key),
compares every answer with key.json (the key the last scored run was marked
against), checks the connector for a vintage option if its saved sign-in
still works, writes checks/<date>.json and rewrites RESULTS.md. It does not
touch key.json and does not run the arms: those need a Claude Code session
and the scoring needs judgement. Exit 0 when nothing needs a look, 3 when a
fixed answer was revised or the connector may have gained a vintage option,
1 when the key could not be rebuilt.
"""
import datetime
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import make_chart

HERE = pathlib.Path(__file__).resolve().parent
RUNS = HERE / "runs"
#: Where key.json waits while the arms run: outside the project, so an agent
#: whose tools were not withheld still cannot open it by a relative path.
HOLD = pathlib.Path(tempfile.gettempdir()) / "fredcheck-key"
ARMS = ["web", "fred", "memory"]
MARKS = ["number", "period", "source"]
#: Words that would mean the connector can now answer "what did we know then".
VINTAGE_WORDS = ["vintage", "realtime", "real_time", "real-time", "as_of", "as-of", "asof", "alfred"]


def run_py(*args):
    out = subprocess.run([sys.executable, *args], cwd=HERE, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("%s failed:\n%s%s" % (" ".join(args), out.stdout, out.stderr))
    return out.stdout


def questions():
    data = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    return data["questions"] if isinstance(data, dict) else data


def check_connector():
    """The write-up's headline rests on this, so it is re-read on every run."""
    tools = [json.loads(line) for line in run_py("fred_call.py", "list").splitlines()
             if line.strip().startswith("{")]
    hits = []
    for tool in tools:
        for name, spec in tool.get("input", {}).get("properties", {}).items():
            text = (name + " " + json.dumps(spec)).lower()
            found = [w for w in VINTAGE_WORDS if w in text]
            if found:
                hits.append("%s.%s (%s)" % (tool["name"], name, ", ".join(found)))
    print("connector: %d tools" % len(tools))
    if hits:
        print("  A VINTAGE OR AS-OF OPTION MAY HAVE APPEARED. Read these before the run;")
        print("  if it is real, the V finding has to be re-tested, not reused:")
        for hit in hits:
            print("   ", hit)
    else:
        print("  no vintage, realtime or as-of parameter on any tool: the V finding still holds")
    return tools, hits


def prepare(date):
    run = RUNS / date
    raw = run / "raw"
    if (run / "scores.jsonl").exists():
        sys.exit("runs/%s is already scored; pick another date" % date)
    print(run_py("fred_auth.py", "--refresh").strip().splitlines()[0])
    tools, hits = check_connector()
    print("building the key (a minute or two)...")
    run_py("build_key.py")
    shutil.rmtree(HERE / ".cache", ignore_errors=True)
    key = json.loads((HERE / "key.json").read_text(encoding="utf-8"))
    answers = key.get("answers", key)
    qs = questions()
    missing = [q["id"] for q in qs if q["id"] not in answers]
    print("key: %d of %d answers%s; .cache/ deleted" % (
        len(qs) - len(missing), len(qs), ", MISSING " + ", ".join(missing) if missing else ""))

    raw.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(qs), 10):
        batch = [{"id": q["id"], "question": q["q"]} for q in qs[i:i + 10]]
        (raw / ("batch%d.json" % (i // 10 + 1))).write_text(
            json.dumps(batch, indent=1), encoding="utf-8")
    (raw / "connector.json").write_text(json.dumps({
        "checked": date, "tools": [t["name"] for t in tools], "vintage_hits": hits}, indent=1),
        encoding="utf-8")

    HOLD.mkdir(exist_ok=True)
    shutil.move(str(HERE / "key.json"), str(HOLD / "key.json"))
    (HOLD / "run.txt").write_text(date, encoding="utf-8")
    print("key.json moved to %s until `rerun.py finish`" % HOLD)
    print()
    print("Next, in a Claude Code session opened in this folder (restart it if it was")
    print("open before the token was renewed):")
    print('  "Run FredCheck for %s: RUNBOOK steps 3 to 5. The batches are in' % date)
    print('   runs/%s/raw/batch1..5.json; save each agent\'s JSON lines to' % date)
    print('   runs/%s/raw/<arm>_b<n>.jsonl. Then run rerun.py finish, score, and' % date)
    print('   run rerun.py finish again."')


def restore_key():
    held = HOLD / "key.json"
    if held.exists():
        shutil.move(str(held), str(HERE / "key.json"))
        print("key.json restored")
    elif not (HERE / "key.json").exists():
        sys.exit("key.json is neither here nor in %s; rebuild it with build_key.py" % HOLD)


def collate(date):
    """One file per arm from the agents' batch files. Attempts kept for the
    record (anything with 'attempt' in its name) are not answers."""
    raw = RUNS / date / "raw"
    ids = [q["id"] for q in questions()]
    complete = True
    for arm in ARMS:
        rows = {}
        for path in sorted(raw.glob(arm + "_b*.jsonl")):
            if "attempt" in path.name:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("{"):
                    row = json.loads(line)
                    row["arm"] = arm
                    rows[row["id"]] = row
        gaps = [i for i in ids if i not in rows]
        if rows:
            out = RUNS / date / (arm + ".jsonl")
            out.write_text("".join(json.dumps(rows[i], ensure_ascii=False) + "\n"
                                   for i in ids if i in rows), encoding="utf-8")
        print("%-6s %d of %d answers%s" % (
            arm, len(rows), len(ids), "; re-run " + ", ".join(gaps) if gaps else ""))
        complete = complete and not gaps
    return complete


def marks(date):
    """(arm, category, mark) -> count, and how many rows were scored."""
    path = RUNS / date / "scores.jsonl"
    if not path.exists():
        return None, 0
    out = {}
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        n += 1
        for mark in MARKS:
            if row.get(mark) in (1, True):
                key = (row["arm"], row["id"][0], mark)
                out[key] = out.get(key, 0) + 1
    return out, n


def total(counts, arm):
    return sum(counts.get((arm, cat, "number"), 0) for cat, _, _ in make_chart.CATS)


def tally(date):
    counts, n = marks(date)
    if counts is None:
        print("runs/%s/scores.jsonl does not exist yet: score the run (RUNBOOK step 5)" % date)
        return False
    expected = len(questions()) * len(ARMS)
    if n != expected:
        print("WARNING: %d scored rows, expected %d" % (n, expected))
    names = {"web": "Web", "fred": "FRED connector", "memory": "Memory only"}
    print("| Category | " + " | ".join(names[a] + ": number / period / source" for a in ARMS) + " |")
    print("|---|---|---|---|")
    for cat, label, size in make_chart.CATS:
        cells = []
        for arm in ARMS:
            got = [counts.get((arm, cat, mark), 0) for mark in MARKS]
            # A-questions ask about metadata and have no period mark.
            cells.append("%d / %s / %d" % (got[0], "–" if cat == "A" else got[1], got[2]))
        print("| %s %s (%d) | %s |" % (cat, label.lower(), size, " | ".join(cells)))
    print("| **Total numbers right** | " + " | ".join(
        "**%d / 50**" % total(counts, a) for a in ARMS) + " |")

    earlier = sorted(p.name for p in RUNS.iterdir()
                     if p.name < date and (p / "scores.jsonl").exists())
    if earlier:
        before, _ = marks(earlier[-1])
        print()
        print("Against %s: %s." % (earlier[-1], ", ".join(
            "%s %d → %d" % (names[a].lower(), total(before, a), total(counts, a)) for a in ARMS)))
    return True


def finish(date):
    restore_key()
    complete = collate(date)
    print()
    if tally(date):
        print()
        print("results.svg redrawn:", make_chart.draw(date))
        write_results()
        print("RESULTS.md rewritten with this run's row")
        print("Now write runs/%s/RESULTS.md around that table, and update WRITEUP.md" % date)
        print("and the README's headline numbers by hand.")
    elif complete:
        print("All answers are in. Score them against key.json, then run finish again.")


CHECKS = HERE / "checks"
RESULTS = HERE / "RESULTS.md"
#: A word beside a scored run's row in RESULTS.md.
RUN_NOTES = {
    "2026-10-06": "draft: run from a session opened outside the project, tool limits by instruction only",
    "2026-10-10": "the run WRITEUP.md reports",
}
#: Fields of a key answer that follow from the others, so are not compared.
DERIVED = {"series", "revision", "n"}


def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    return a == b


def shows(a, b):
    """Whether a change shows at one decimal, the precision most marks use.
    A CPI ratio moving in its sixth decimal is a revision but not a new answer."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return round(a, 1) != round(b, 1)
    return True


def fmt(v):
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else ("%.3f" % v).rstrip("0").rstrip(".")
    text = str(v)
    return text if len(text) <= 40 else text[:37] + "..."


#: How far a rolling start may stray from the days between the two keys: FRED
#: trims a weekly series a week at a time, so the start lags by up to a week.
ROLLING_SLACK_DAYS = 8


def rolls(a, b, elapsed_days):
    """Whether a metadata `first_date` moved forward by about the time between
    the keys: a series FRED keeps as a rolling window (SP500 holds ten years),
    whose start moves every week and is not a revision. Found 2026-10-15 on A02."""
    if elapsed_days is None:
        return False
    try:
        shift = (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return False
    return shift > 0 and abs(shift - elapsed_days) <= ROLLING_SLACK_DAYS


def days_between(built_a, built_b):
    """Whole days between two key `built` stamps, or None if either is missing."""
    try:
        return (datetime.datetime.fromisoformat(built_b) - datetime.datetime.fromisoformat(built_a)).days
    except (TypeError, ValueError):
        return None


def compare(old, new, qs, elapsed_days=None):
    """Each question's answer in the fresh key against the baseline key.

    moved:   a latest-value question whose latest period has changed. Expected
             every month; the arms would be scored against the new period.
    revised: any other change to an answer, including a latest value whose
             period is the same but whose figure was revised. These are the
             questions whose ground truth moved under a scored run.
    rolling: a metadata start date that moved forward by the time between the
             keys (`elapsed_days`): a rolling window, expected, reported apart.
    errors:  answers the fresh key could not compute."""
    out = {"moved": [], "revised": [], "rolling": [], "errors": [], "unchanged": 0}
    for q in qs:
        qid = q["id"]
        a, b = old.get(qid), new.get(qid, {"error": "not built"})
        if "error" in b:
            out["errors"].append({"id": qid, "error": fmt(b["error"])})
            continue
        if a is None or "error" in a:
            out["revised"].append({"id": qid, "field": "(no baseline answer)",
                                   "old": None, "new": None, "shows": True})
            continue
        if q["spec"]["type"] == "latest" and a.get("date") != b.get("date"):
            out["moved"].append({"id": qid, "from": a.get("date"), "to": b.get("date")})
            continue
        changes = [{"id": qid, "field": f, "old": a.get(f), "new": b.get(f),
                    "shows": shows(a.get(f), b.get(f))}
                   for f in sorted((set(a) | set(b)) - DERIVED)
                   if not same(a.get(f), b.get(f))]
        rolled = [c for c in changes if q["spec"]["type"] == "metadata" and c["field"] == "first_date"
                  and rolls(c["old"], c["new"], elapsed_days)]
        out["rolling"].extend({"id": c["id"], "field": c["field"], "from": c["old"], "to": c["new"]}
                              for c in rolled)
        out["revised"].extend(c for c in changes if c not in rolled)
        if not changes:
            out["unchanged"] += 1
    return out


def connector_status():
    """The vintage check, if the saved sign-in still works. A refresh token
    that has expired needs the author at a browser, so that is reported,
    not fatal."""
    try:
        tools, hits = check_connector()
    except SystemExit:
        print("connector: not checked; the saved sign-in failed. Run `py fred_auth.py` at a browser.")
        return {"checked": False}
    return {"checked": True, "tools": len(tools), "vintage_hits": hits}


def monthly(date):
    if (HOLD / "run.txt").exists() and (HOLD / "key.json").exists():
        sys.exit("a run is between prepare and finish (key.json is in %s); finish it first" % HOLD)
    base_path = HERE / "key.json"
    if not base_path.exists():
        sys.exit("key.json is missing, so there is nothing to compare against")
    base = json.loads(base_path.read_text(encoding="utf-8"))
    qs = questions()
    import build_key
    print("rebuilding the key in memory from FRED's public CSVs (a minute or two)...")
    try:
        key = build_key.build(quiet=True)
    finally:
        # FRED's terms bar storing its content: keep only the values compared.
        shutil.rmtree(HERE / ".cache", ignore_errors=True)
    found = compare(base["answers"], key["answers"], qs,
                    elapsed_days=days_between(base.get("built"), key["built"]))
    connector = connector_status()
    record = {
        "checked": date,
        "baseline_run": make_chart.latest_run(),
        "baseline_built": base.get("built"),
        "key_built": key["built"],
        "questions": len(qs),
        "connector": connector,
        "arms": "not run: they need a Claude Code session (RUNBOOK steps 3 to 5)",
    }
    record.update(found)
    CHECKS.mkdir(exist_ok=True)
    (CHECKS / (date + ".json")).write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")

    print("key: %d answers unchanged, %d latest values on a new period, %d revisions, %d errors" % (
        found["unchanged"], len(found["moved"]), len(found["revised"]), len(found["errors"])))
    for r in found["rolling"]:
        print("  ROLLING %s %s: %s -> %s (moved with the calendar; a rolling window, not a revision)"
              % (r["id"], r["field"], r["from"], r["to"]))
    for r in found["revised"]:
        print("  REVISED %s %s: %s -> %s%s" % (r["id"], r["field"], fmt(r["old"]), fmt(r["new"]),
                                               "" if r["shows"] else " (below one decimal)"))
    for e in found["errors"]:
        print("  ERROR %s: %s" % (e["id"], e["error"]))
    write_results()
    print("wrote checks/%s.json and RESULTS.md (not committed)" % date)
    if found["errors"]:
        return 1
    if any(r["shows"] for r in found["revised"]) or connector.get("vintage_hits"):
        return 3
    return 0


def connector_cell(c):
    if not c.get("checked"):
        return "not checked (sign-in expired)"
    if c.get("vintage_hits"):
        return "**possible vintage option**: " + "; ".join(c["vintage_hits"])
    return "no vintage option (%d tools)" % c["tools"]


def revised_cell(rec):
    shown = [r for r in rec["revised"] if r["shows"]]
    quiet = len(rec["revised"]) - len(shown)
    parts = ["%s %s %s → %s" % (r["id"], r["field"], fmt(r["old"]), fmt(r["new"])) for r in shown]
    if quiet:
        parts.append("%d below one decimal" % quiet)
    rolled = ["%s %s rolls with the calendar (%s → %s)" % (r["id"], r["field"], r["from"], r["to"])
              for r in rec.get("rolling", [])]
    if not parts:
        return "none (%s)" % "; ".join(rolled) if rolled else "none"
    return "; ".join(parts + rolled)


def write_results():
    names = [("fred", "FRED connector"), ("web", "Web search"), ("memory", "No tools")]
    out = [
        "# FredCheck results by date",
        "",
        "Written by `py rerun.py table` (and by `monthly`) from `runs/*/scores.jsonl` and",
        "`checks/*.json`. Do not edit by hand.",
        "",
        "## Scored runs",
        "",
        "Numbers right out of the 50 questions. Each run's own `RESULTS.md` has the",
        "period and source marks and every judgement call.",
        "",
        "| Run | " + " | ".join(n for _, n in names) + " | Note |",
        "|---|---|---|---|---|",
    ]
    for run in sorted(p.name for p in RUNS.iterdir() if (p / "scores.jsonl").exists()):
        counts, _ = marks(run)
        out.append("| [%s](runs/%s/RESULTS.md) | %s | %s |" % (
            run, run, " | ".join(str(total(counts, a)) for a, _ in names), RUN_NOTES.get(run, "")))
    out += [
        "",
        "## Monthly ground-truth checks",
        "",
        "Each check rebuilds every answer from FRED's public data and compares it with",
        "the key the last scored run was marked against. It does not put the questions",
        "to any assistant. A latest-value question on a new period is expected; a",
        "revision to any other answer means that question's ground truth moved after",
        "it was scored.",
        "",
        "| Checked | Against | Unchanged | Latest values on a new period | Revised answers | Errors | Connector |",
        "|---|---|---|---|---|---|---|",
    ]
    checks = sorted(CHECKS.glob("*.json")) if CHECKS.exists() else []
    for path in checks:
        rec = json.loads(path.read_text(encoding="utf-8"))
        out.append("| %s | %s key | %d | %d | %s | %s | %s |" % (
            rec["checked"], rec["baseline_run"], rec["unchanged"], len(rec["moved"]),
            revised_cell(rec), ", ".join(e["id"] for e in rec["errors"]) or "none",
            connector_cell(rec["connector"])))
    if not checks:
        out.append("| (none yet) | | | | | | |")
    RESULTS.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


def main(argv):
    if len(argv) < 2 or argv[1] not in ("prepare", "finish", "tally", "monthly", "table"):
        sys.exit(__doc__)
    if argv[1] == "table":
        write_results()
        return
    if len(argv) > 2:
        date = argv[2]
        datetime.date.fromisoformat(date)
    elif argv[1] in ("prepare", "monthly"):
        date = datetime.date.today().isoformat()
    elif (HOLD / "run.txt").exists():
        date = (HOLD / "run.txt").read_text(encoding="utf-8").strip()
    else:
        date = make_chart.latest_run()
    if argv[1] == "monthly":
        sys.exit(monthly(date))
    {"prepare": prepare, "finish": finish, "tally": tally}[argv[1]](date)


if __name__ == "__main__":
    main(sys.argv)
