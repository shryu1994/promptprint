import json
from wami.model import QuestionRecord
from wami.delta import build_delta
from wami.journal import read_journal, previous_entry, upsert_journal, journal_entry, followup


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


def test_followup_metaskill_moves_up():
    prev = {"as_of": "2026-05-01",
            "metrics": {"metaskill_rate": {"verify": 0.0, "critique": 0.0,
                        "delegate": 0.0, "counter": 0.0},
                        "one_shot_rate": 0.4, "code_block_rate": 0.1,
                        "q_per_session": 2.0, "multistep_rate": 0.2, "avg_len": 100.0},
            "skill_candidates": []}
    delta = {"as_of": "2026-06-01",
             "recent": {"metaskill_rate": {"verify": 0.5, "critique": 0.0,
                        "delegate": 0.0, "counter": 0.0},
                        "one_shot_rate": 0.3, "code_block_rate": 0.2,
                        "q_per_session": 1.5, "multistep_rate": 0.3, "avg_len": 120.0},
             "skill_candidates": []}
    fu = followup(prev, delta)
    assert fu["since"] == "2026-05-01"
    assert fu["metaskill_moves"]["verify"] == {"prev": 0.0, "now": 0.5, "change": 0.5}
    assert fu["metric_moves"]["one_shot_rate"]["change"] == -0.1


def test_followup_toil_drop():
    prev = {"as_of": "2026-05-01", "metrics": {"metaskill_rate": {}},
            "skill_candidates": [{"term": "deploy", "recent_count": 4, "avg_len": 140.0}]}
    delta = {"as_of": "2026-06-01",
             "recent": {"metaskill_rate": {}, "one_shot_rate": 0, "code_block_rate": 0,
                        "q_per_session": 0, "multistep_rate": 0, "avg_len": 0},
             "skill_candidates": [{"term": "deploy", "recent_count": 1, "avg_len": 130.0}]}
    fu = followup(prev, delta)
    assert fu["toil_followup"][0] == {"term": "deploy", "prev_recent_count": 4,
                                      "now_recent_count": 1, "change": -3}


def test_two_checks_compounding_end_to_end(tmp_path):
    jpath = str(tmp_path / "checks.local.json")
    base = [_rec("2026-05-20T10:00:00+00:00", "just write it"),
            _rec("2026-05-22T10:00:00+00:00", "make a button")]
    d1 = build_delta(base, window_days=30)
    upsert_journal(jpath, journal_entry(d1))                       # check #1
    later = base + [_rec("2026-06-20T10:00:00+00:00", "please verify this is correct"),
                    _rec("2026-06-21T10:00:00+00:00", "verify it again please")]
    d2 = build_delta(later, window_days=30)
    prev = previous_entry(read_journal(jpath), d2["as_of"])        # check #2 reads #1
    assert prev["as_of"] == d1["as_of"]
    fu = followup(prev, d2)
    assert fu["metaskill_moves"]["verify"]["now"] > fu["metaskill_moves"]["verify"]["prev"]
