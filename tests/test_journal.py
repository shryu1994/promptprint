import json
from wami.model import QuestionRecord
from wami.delta import build_delta
from wami.journal import read_journal, previous_entry, upsert_journal, journal_entry


def _rec(ts, text, session="s1"):
    return QuestionRecord(ts=ts, tool="claude", session_id=session,
                          project="p", text=text, turn_idx=0)


def test_journal_entry_is_privacy_safe_and_shaped():
    recs = [_rec("2026-06-20T10:00:00+00:00", "please verify this exact phrase")]
    entry = journal_entry(build_delta(recs, window_days=30))
    blob = json.dumps(entry, ensure_ascii=False)
    assert "verify this exact phrase" not in blob          # 원문 0
    assert set(entry) == {"as_of", "window_days", "metrics", "skill_candidates"}
    assert "metaskill_rate" in entry["metrics"]
    assert "verify" in entry["metrics"]["metaskill_rate"]


def test_journal_entry_tolerates_empty_delta():
    entry = journal_entry(build_delta([], window_days=30))
    assert entry["as_of"] is None
    assert entry["skill_candidates"] == []
    assert "metaskill_rate" in entry["metrics"]


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
