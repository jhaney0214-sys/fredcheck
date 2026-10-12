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
        print("Now write runs/%s/RESULTS.md around that table, and update WRITEUP.md" % date)
        print("and the README's headline numbers by hand.")
    elif complete:
        print("All answers are in. Score them against key.json, then run finish again.")


def main(argv):
    if len(argv) < 2 or argv[1] not in ("prepare", "finish", "tally"):
        sys.exit(__doc__)
    if len(argv) > 2:
        date = argv[2]
        datetime.date.fromisoformat(date)
    elif argv[1] == "prepare":
        date = datetime.date.today().isoformat()
    elif (HOLD / "run.txt").exists():
        date = (HOLD / "run.txt").read_text(encoding="utf-8").strip()
    else:
        date = make_chart.latest_run()
    {"prepare": prepare, "finish": finish, "tally": tally}[argv[1]](date)


if __name__ == "__main__":
    main(sys.argv)
