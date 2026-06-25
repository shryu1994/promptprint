from wami.model import QuestionRecord
from wami.delta import build_delta


def rec(ts, text, session="s1", tool="claude", project="p", turn=0):
    return QuestionRecord(ts=ts, tool=tool, session_id=session,
                          project=project, text=text, turn_idx=turn)


def test_window_split_and_as_of():
    recs = [
        rec("2026-06-20T10:00:00+00:00", "recent one"),
        rec("2026-06-24T10:00:00+00:00", "recent two"),
        rec("2026-05-20T10:00:00+00:00", "prior one"),
        rec("2026-03-01T10:00:00+00:00", "way old excluded"),
    ]
    d = build_delta(recs, window_days=30)
    assert d["as_of"] == "2026-06-24"
    assert d["recent"]["total"] == 2
    assert d["prior"]["total"] == 1
    assert d["deltas"]["total"] == 1  # 2 - 1


def test_metaskill_rate_is_per_message_and_delta():
    recs = [
        rec("2026-06-20T10:00:00+00:00", "please verify this is correct"),  # verify signal
        rec("2026-06-21T10:00:00+00:00", "just write it"),                  # no signal
        rec("2026-05-10T10:00:00+00:00", "make a button"),                  # prior, no signal
    ]
    d = build_delta(recs, window_days=30)
    assert d["recent"]["metaskill_rate"]["verify"] == 0.5   # 1 of 2 recent msgs
    assert d["prior"]["metaskill_rate"]["verify"] == 0.0
    assert d["deltas"]["metaskill_rate"]["verify"] == 0.5


def test_q_per_session():
    recs = [
        rec("2026-06-20T10:00:00+00:00", "a", session="s1"),
        rec("2026-06-20T11:00:00+00:00", "b", session="s1"),
        rec("2026-06-21T10:00:00+00:00", "c", session="s2"),
    ]
    d = build_delta(recs, window_days=30)
    assert d["recent"]["sessions"] == 2
    assert d["recent"]["q_per_session"] == 1.5   # 3 questions / 2 sessions


def test_new_and_dropped_topics():
    recs = [
        rec("2026-06-20T10:00:00+00:00", "kubernetes deployment question"),  # recent only
        rec("2026-05-10T10:00:00+00:00", "graphql schema question"),         # prior only
    ]
    d = build_delta(recs, window_days=30)
    new_terms = {t["term"] for t in d["new_topics"]}
    dropped_terms = {t["term"] for t in d["dropped_topics"]}
    assert "kubernetes" in new_terms
    assert "graphql" in dropped_terms
    assert "question" not in new_terms        # appears in both windows -> not new


def test_code_and_multistep_rates():
    recs = [
        rec("2026-06-20T10:00:00+00:00", "fix this ```code```"),                # code block
        rec("2026-06-21T10:00:00+00:00", "1. first do x\n2. then do y here"),   # multistep
    ]
    d = build_delta(recs, window_days=30)
    assert d["recent"]["code_block_rate"] == 0.5
    assert d["recent"]["multistep_rate"] == 0.5


def test_empty_no_crash():
    d = build_delta([], window_days=30)
    assert d["empty"] is True
    assert d["as_of"] is None
    assert d["recent"]["total"] == 0
    assert d["deltas"] == {}
    assert d["skill_candidates"] == []
