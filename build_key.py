"""Build the answer key for questions.json from FRED and ALFRED.

Every answer is computed from FRED's public CSV downloads (no API key), so
the key can be rebuilt on the day a run is scored. Latest-value answers move;
the key records when it was built.

    python build_key.py            # writes key.json
"""
import csv
import datetime as dt
import html
import io
import json
import re
import statistics
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / ".cache"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
ALFRED_CSV = "https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={sid}&vintage_date={vd}"
SERIES_PAGE = "https://fred.stlouisfed.org/series/{sid}"
UA = {"User-Agent": "FredCheck/0.1 (answer-key builder)"}


def fetch(url, cache_name=None):
    if cache_name:
        p = CACHE / cache_name
        if p.exists():
            return p.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8", "replace")
    time.sleep(0.3)
    if cache_name:
        CACHE.mkdir(exist_ok=True)
        (CACHE / cache_name).write_text(text, encoding="utf-8")
    return text


def parse_csv(text):
    """[(date, float)], skipping FRED's '.' for missing."""
    rows = list(csv.reader(io.StringIO(text)))
    out = []
    for r in rows[1:]:
        if len(r) < 2 or r[1] in (".", ""):
            continue
        out.append((r[0], float(r[1])))
    return out


_series = {}


def series(sid):
    if sid not in _series:
        _series[sid] = parse_csv(fetch(FRED_CSV.format(sid=sid)))
    return _series[sid]


def vintage(sid, vd):
    return parse_csv(fetch(ALFRED_CSV.format(sid=sid, vd=vd), "alfred_%s_%s.csv" % (sid, vd)))


def transform(obs, how):
    """Apply 'yoy' (percent change from 12 periods back, monthly) or 'diff'."""
    if not how:
        return obs
    vals = dict(obs)
    dates = [d for d, _ in obs]
    out = []
    for i, d in enumerate(dates):
        if how == "diff" and i >= 1:
            out.append((d, vals[d] - vals[dates[i - 1]]))
        elif how == "yoy":
            y, m, day = d.split("-")
            prev = "%04d-%s-%s" % (int(y) - 1, m, day)
            if prev in vals:
                out.append((d, (vals[d] / vals[prev] - 1) * 100))
    return out


def in_range(obs, start, end):
    return [(d, v) for d, v in obs if start <= d <= end]


def first_vintage_with(sid, date, how):
    """Walk forward day by day from the observation's period end until a
    vintage contains it (and, for diff/yoy, its comparison point)."""
    d0 = dt.date.fromisoformat(date)
    # Search from the end of the observation's period; quarterly can take ~30 days.
    start = (d0.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    if sid.endswith("Q225SBEA"):
        start = dt.date(d0.year + (d0.month + 2) // 12, (d0.month + 2) % 12 + 1, 1)
    for k in range(0, 60):
        vd = (start + dt.timedelta(days=k)).isoformat()
        obs = transform(vintage(sid, vd), how)
        hit = dict(obs).get(date)
        if hit is not None:
            return vd, hit
    raise RuntimeError("no vintage found for %s %s" % (sid, date))


def metadata(sid):
    # Not read: the page's "Data in this graph are copyrighted" banner. It shows
    # on public-domain Census series too (MSPUS, 2026-10-06), so it is no signal.
    page = fetch(SERIES_PAGE.format(sid=sid), "page_%s.html" % sid)
    page = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    labels = ["Source:", "Release:", "Units:", "Frequency:", "Notes:", "Suggested Citation:"]
    out = {}
    for lab in labels[:4]:
        found = []
        for m in re.finditer(re.escape(lab), text):
            rest = text[m.end():]
            ends = [rest.find(l) for l in labels + ["Fullscreen"] if rest.find(l) > 0]
            found.append(rest[: min(ends) if ends else 120].strip(" ,"))
        if found:
            # A series can list several sources (MSPUS: Census and HUD).
            out[lab[:-1].lower()] = "; ".join(dict.fromkeys(found))
    obs = series(sid)
    out["first_date"] = obs[0][0] if obs else None
    return out


def answer(spec):
    t, sid = spec["type"], spec["series"]
    how = spec.get("transform")
    if t == "latest":
        d, v = transform(series(sid), how)[-1]
        return {"value": v, "date": d}
    if t == "value_at":
        v = dict(transform(series(sid), how)).get(spec["date"])
        if v is None:
            raise RuntimeError("%s has no observation on %s" % (sid, spec["date"]))
        return {"value": v, "date": spec["date"]}
    if t in ("max", "min"):
        obs = in_range(transform(series(sid), how), spec["start"], spec["end"])
        d, v = (max if t == "max" else min)(obs, key=lambda x: x[1])
        return {"value": v, "date": d}
    if t == "mean":
        obs = in_range(series(sid), spec["start"], spec["end"])
        return {"value": statistics.mean(v for _, v in obs), "n": len(obs)}
    if t == "count":
        obs = in_range(transform(series(sid), how), spec["start"], spec["end"])
        test = (lambda v: v > spec["threshold"]) if spec["op"] == ">" else (lambda v: v < spec["threshold"])
        hits = [d for d, v in obs if test(v)]
        return {"value": len(hits), "dates": hits}
    if t == "change":
        vals = dict(series(sid))
        a, b = vals[spec["from"]], vals[spec["to"]]
        return {"value": b - a if spec["how"] == "diff" else (b / a - 1) * 100, "from": a, "to": b}
    if t == "first_vs_now":
        vd, first = first_vintage_with(sid, spec["date"], how)
        now = dict(transform(series(sid), how)).get(spec["date"])
        return {"first": first, "first_vintage": vd, "now": now, "revision": now - first}
    if t == "as_of":
        v = dict(transform(vintage(sid, spec["vintage"]), how)).get(spec["date"])
        return {"value": v, "vintage": spec["vintage"], "now": dict(series(sid)).get(spec["date"])}
    if t == "as_of_latest":
        d, v = transform(vintage(sid, spec["vintage"]), how)[-1]
        return {"value": v, "date": d, "vintage": spec["vintage"]}
    if t == "metadata":
        m = metadata(sid)
        return {f: m.get(f) for f in spec["fields"]}
    raise ValueError(t)


def main():
    qs = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))["questions"]
    key = {"built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "answers": {}}
    for q in qs:
        try:
            a = answer(q["spec"])
        except Exception as e:  # keep going; a broken spec is reported, not fatal
            a = {"error": str(e)}
        a["series"] = q["spec"]["series"]
        key["answers"][q["id"]] = a
        print(q["id"], json.dumps(a, default=str)[:150])
    (HERE / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
