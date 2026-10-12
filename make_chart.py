"""Draw results.svg from a run's scores.

    python make_chart.py              # the latest run under runs/
    python make_chart.py 2026-10-10   # a named run
"""
import collections
import datetime
import io
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

CATS = [("L", "Latest values", 10), ("H", "Historical values", 12),
        ("C", "Computed from a series", 8), ("V", "First-reported vs revised", 10),
        ("A", "Source and units", 10)]
ARMS = [("fred", "FRED connector", "#2a78d6"), ("web", "Web search", "#eb6834"),
        ("memory", "No tools", "#1baf7a")]

# True while the connector has no vintage or as-of option. If rerun.py's
# prepare step reports one, re-test the V questions and rewrite this line.
NOTE = ("Unlabelled bars are full marks. The connector's first-reported figures "
        "came from the model's memory, not from FRED: see WRITEUP.md.")


def latest_run():
    runs = sorted(p.name for p in (HERE / "runs").iterdir()
                  if (p / "scores.jsonl").exists())
    return runs[-1]


def counts(run):
    """Number marks by (arm, category letter)."""
    c = collections.Counter()
    path = HERE / "runs" / run / "scores.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("number") in (1, True):
                c[(r["arm"], r["id"][0])] += 1
    return c


def draw(run):
    c = counts(run)
    d = datetime.date.fromisoformat(run)
    when = "%d %s" % (d.day, d.strftime("%B %Y"))
    W, H = 860, 512
    left, right, top = 210, 40, 92
    plot = W - left - right
    bar, gap = 14, 2
    group = 3 * bar + 2 * gap
    step = group + 24
    tot = {a: sum(c[(a, k)] for k, _, _ in CATS) for a, _, _ in ARMS}
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             f'role="img" aria-label="FredCheck, {when}: numbers right by question category '
             f'for the FRED connector, web search and no tools">')
    o.append('<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}</style>')
    o.append(f'<rect width="{W}" height="{H}" fill="#fcfcfb"/>')
    o.append('<text x="24" y="34" font-size="18" font-weight="600" fill="#0b0b0b">Numbers right, by kind of question</text>')
    o.append(f'<text x="24" y="56" font-size="13" fill="#52514e">50 questions about U.S. economic data, '
             f'run {when}. Bars show the share answered correctly.</text>')
    x = 24
    for a, name, col in ARMS:
        o.append(f'<rect x="{x}" y="68" width="12" height="12" rx="2" fill="{col}"/>')
        label = f"{name}: {tot[a]} of 50"
        o.append(f'<text x="{x + 18}" y="79" font-size="13" fill="#0b0b0b">{label}</text>')
        x += 18 + len(label) * 7.1 + 22
    for t in (0, 25, 50, 75, 100):
        gx = left + plot * t / 100
        o.append(f'<line x1="{gx:.1f}" y1="{top + 12}" x2="{gx:.1f}" y2="{top + 12 + 5 * step - 14}" stroke="#e4e3df" stroke-width="1"/>')
        o.append(f'<text x="{gx:.1f}" y="{top + 12 + 5 * step + 4}" font-size="11" fill="#52514e" text-anchor="middle">{t}%</text>')
    y = top + 18
    for k, name, n in CATS:
        o.append(f'<text x="{left - 12}" y="{y + group / 2 - 2}" font-size="13" fill="#0b0b0b" text-anchor="end">{name}</text>')
        o.append(f'<text x="{left - 12}" y="{y + group / 2 + 14}" font-size="11" fill="#52514e" text-anchor="end">{n} questions</text>')
        for i, (a, _, col) in enumerate(ARMS):
            v = c[(a, k)]
            w = plot * v / n
            by = y + i * (bar + gap)
            if v > 0:
                o.append(f'<path d="M{left},{by} h{w - 4:.1f} a4,4 0 0 1 4,4 v{bar - 8} a4,4 0 0 1 -4,4 h-{w - 4:.1f} z" fill="{col}"/>')
            else:
                o.append(f'<rect x="{left}" y="{by}" width="2" height="{bar}" fill="{col}"/>')
            if v < n:
                o.append(f'<text x="{left + max(w, 2) + 6:.1f}" y="{by + bar - 3}" font-size="11" fill="#0b0b0b">{v} of {n}</text>')
        y += step
    o.append(f'<line x1="{left}" y1="{top + 12}" x2="{left}" y2="{top + 12 + 5 * step - 14}" stroke="#52514e" stroke-width="1"/>')
    o.append(f'<text x="24" y="{H - 14}" font-size="11" fill="#52514e">{NOTE}</text>')
    o.append("</svg>")
    io.open(HERE / "results.svg", "w", encoding="utf-8", newline="\n").write("\n".join(o))
    return tot


if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else latest_run()
    print(run, draw(run))
