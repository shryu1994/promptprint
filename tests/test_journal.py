import json
from wami.journal import read_journal, previous_entry, upsert_journal


def test_read_journal_missing_returns_empty(tmp_path):
    assert read_journal(str(tmp_path / "nope.json")) == []


def test_upsert_replaces_same_as_of_and_sorts(tmp_path):
    jpath = str(tmp_path / "checks.local.json")
    upsert_journal(jpath, {"as_of": "2026-06-01", "metrics": {}, "skill_candidates": []})
    upsert_journal(jpath, {"as_of": "2026-06-01", "metrics": {"one_shot_rate": 0.5},
                           "skill_candidates": []})
    upsert_journal(jpath, {"as_of": "2026-07-01", "metrics": {}, "skill_candidates": []})
    j = read_journal(jpath)
    assert [e["as_of"] for e in j] == ["2026-06-01", "2026-07-01"]   # no dup, sorted
    assert j[0]["metrics"]["one_shot_rate"] == 0.5                    # last write wins


def test_previous_entry_strictly_earlier():
    j = [{"as_of": "2026-05-01"}, {"as_of": "2026-06-01"}]
    assert previous_entry(j, "2026-06-01")["as_of"] == "2026-05-01"   # same-day excluded
    assert previous_entry(j, "2026-04-01") is None


def test_previous_entry_skips_entry_without_as_of():
    j = [{"as_of": "2026-05-01"}, {"note": "no as_of"}, {"as_of": "2026-06-01"}]
    assert previous_entry(j, "2026-06-01")["as_of"] == "2026-05-01"
