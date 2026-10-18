"""Offline tests for the monthly check: no network, no FRED sign-in.

    py -m unittest discover -s tests
"""
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import rerun  # noqa: E402

QS = [
    {"id": "L01", "spec": {"type": "latest", "series": "UNRATE"}},
    {"id": "L02", "spec": {"type": "latest", "series": "CPIAUCSL", "transform": "yoy"}},
    {"id": "H01", "spec": {"type": "value_at", "series": "UNRATE"}},
    {"id": "V01", "spec": {"type": "first_vs_now", "series": "PAYEMS"}},
    {"id": "A01", "spec": {"type": "metadata", "series": "MORTGAGE30US"}},
]
OLD = {
    "L01": {"value": 4.2, "date": "2026-09-01", "series": "UNRATE"},
    "L02": {"value": 3.353016322755642, "date": "2026-08-01", "series": "CPIAUCSL"},
    "H01": {"value": 14.8, "date": "2020-04-01", "series": "UNRATE"},
    "V01": {"first": 228.0, "first_vintage": "2025-04-04", "now": 67.0, "revision": -161.0, "series": "PAYEMS"},
    "A01": {"source": "Freddie Mac", "series": "MORTGAGE30US"},
}


def fresh(**changes):
    new = json.loads(json.dumps(OLD))
    for qid, fields in changes.items():
        new[qid].update(fields)
    return new


class Compare(unittest.TestCase):
    def test_nothing_changed(self):
        out = rerun.compare(OLD, fresh(), QS)
        self.assertEqual(out["unchanged"], 5)
        self.assertEqual((out["moved"], out["revised"], out["errors"]), ([], [], []))

    def test_latest_on_a_new_period_is_moved_not_revised(self):
        out = rerun.compare(OLD, fresh(L01={"value": 4.3, "date": "2026-10-01"}), QS)
        self.assertEqual(out["moved"], [{"id": "L01", "from": "2026-09-01", "to": "2026-10-01"}])
        self.assertEqual(out["revised"], [])

    def test_latest_revised_in_the_same_period_is_flagged(self):
        out = rerun.compare(OLD, fresh(L01={"value": 4.3}), QS)
        self.assertEqual([(r["id"], r["field"], r["shows"]) for r in out["revised"]],
                         [("L01", "value", True)])

    def test_a_revision_below_one_decimal_is_recorded_but_quiet(self):
        out = rerun.compare(OLD, fresh(L02={"value": 3.3531}), QS)
        self.assertEqual(len(out["revised"]), 1)
        self.assertFalse(out["revised"][0]["shows"])

    def test_float_noise_is_not_a_revision(self):
        out = rerun.compare(OLD, fresh(L02={"value": 3.353016322755642 + 1e-13}), QS)
        self.assertEqual(out["revised"], [])

    def test_vintage_now_revised_and_derived_field_ignored(self):
        out = rerun.compare(OLD, fresh(V01={"now": 70.0, "revision": -158.0}), QS)
        self.assertEqual([(r["id"], r["field"]) for r in out["revised"]], [("V01", "now")])

    def test_metadata_change_is_flagged(self):
        out = rerun.compare(OLD, fresh(A01={"source": "Freddie Mac; HUD"}), QS)
        self.assertEqual([(r["id"], r["field"]) for r in out["revised"]], [("A01", "source")])

    def test_a_start_that_moves_with_the_calendar_is_rolling_not_revised(self):
        # A02 on 2026-10-15: FRED's SP500 keeps ten years, so its start moved a week in five days.
        old = dict(OLD, A01={"source": "S&P", "first_date": "2016-10-10", "series": "SP500"})
        new = dict(OLD, A01={"source": "S&P", "first_date": "2016-10-17", "series": "SP500"})
        out = rerun.compare(old, new, QS, elapsed_days=5)
        self.assertEqual(out["revised"], [])
        self.assertEqual(out["rolling"], [{"id": "A01", "field": "first_date",
                                           "from": "2016-10-10", "to": "2016-10-17"}])
        self.assertEqual(rerun.revised_cell(out), "none (A01 first_date rolls with the calendar "
                                                  "(2016-10-10 → 2016-10-17))")

    def test_a_start_that_moves_by_far_more_than_the_time_between_is_a_revision(self):
        old = dict(OLD, A01={"source": "S&P", "first_date": "2016-10-10", "series": "SP500"})
        new = dict(OLD, A01={"source": "S&P", "first_date": "2018-01-02", "series": "SP500"})
        for elapsed in (5, None):
            out = rerun.compare(old, new, QS, elapsed_days=elapsed)
            self.assertEqual([r["field"] for r in out["revised"]], ["first_date"])
            self.assertEqual(out["rolling"], [])

    def test_days_between_two_key_stamps(self):
        self.assertEqual(rerun.days_between("2026-10-10T20:49:10+00:00", "2026-10-15T23:12:07+00:00"), 5)
        self.assertIsNone(rerun.days_between(None, "2026-10-15T23:12:07+00:00"))

    def test_historical_value_revised(self):
        out = rerun.compare(OLD, fresh(H01={"value": 14.7}), QS)
        self.assertEqual([r["id"] for r in out["revised"]], ["H01"])

    def test_errors_are_reported(self):
        new = fresh()
        new["H01"] = {"error": "HTTP Error 503", "series": "UNRATE"}
        del new["A01"]
        out = rerun.compare(OLD, new, QS)
        self.assertEqual([e["id"] for e in out["errors"]], ["H01", "A01"])
        self.assertEqual(out["unchanged"], 3)


class Results(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.saved = rerun.RUNS, rerun.CHECKS, rerun.RESULTS
        rerun.RUNS, rerun.CHECKS, rerun.RESULTS = root / "runs", root / "checks", root / "RESULTS.md"
        run = rerun.RUNS / "2026-10-10"
        run.mkdir(parents=True)
        rows = [{"arm": arm, "id": "L%02d" % i, "number": int(i <= good), "period": 1, "source": 1}
                for arm, good in (("web", 9), ("fred", 10), ("memory", 0)) for i in range(1, 11)]
        (run / "scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (rerun.RUNS / "2026-11-01").mkdir()  # prepared, not scored: no row

    def tearDown(self):
        rerun.RUNS, rerun.CHECKS, rerun.RESULTS = self.saved
        self.tmp.cleanup()

    def table(self):
        rerun.write_results()
        return rerun.RESULTS.read_text(encoding="utf-8")

    def test_one_row_per_scored_run(self):
        text = self.table()
        self.assertIn("| [2026-10-10](runs/2026-10-10/RESULTS.md) | 10 | 9 | 0 | the run WRITEUP.md reports |", text)
        self.assertNotIn("2026-11-01", text)
        self.assertIn("| (none yet) |", text)

    def test_one_row_per_check(self):
        rerun.CHECKS.mkdir()
        found = rerun.compare(OLD, fresh(L01={"date": "2026-10-01"}, V01={"now": 70.0},
                                         L02={"value": 3.3531}), QS)
        rec = {"checked": "2026-11-15", "baseline_run": "2026-10-10",
               "connector": {"checked": True, "tools": 5, "vintage_hits": []}}
        rec.update(found)
        (rerun.CHECKS / "2026-11-15.json").write_text(json.dumps(rec), encoding="utf-8")
        rec2 = dict(rec, checked="2026-12-15", connector={"checked": False}, revised=[], moved=[])
        (rerun.CHECKS / "2026-12-15.json").write_text(json.dumps(rec2), encoding="utf-8")
        text = self.table()
        self.assertIn("| 2026-11-15 | 2026-10-10 key | 2 | 1 | V01 now 67 → 70; 1 below one decimal | none "
                      "| no vintage option (5 tools) |", text)
        self.assertIn("| 2026-12-15 | 2026-10-10 key | 2 | 0 | none | none | not checked (sign-in expired) |", text)
        self.assertLess(text.index("2026-11-15"), text.index("2026-12-15"))


class Repo(unittest.TestCase):
    def test_committed_results_match_the_data(self):
        """RESULTS.md is generated; it must equal what `rerun.py table` writes."""
        committed = (HERE / "RESULTS.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            saved = rerun.RESULTS
            rerun.RESULTS = pathlib.Path(tmp) / "RESULTS.md"
            try:
                rerun.write_results()
                self.assertEqual(rerun.RESULTS.read_text(encoding="utf-8"), committed)
            finally:
                rerun.RESULTS = saved


if __name__ == "__main__":
    unittest.main()
