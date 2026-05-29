import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy.orm import Session
from shared.models import get_engine, Keyword, KeywordCooccurrence
from processor.src.seed import upsert_keyword
from processor.src.cooccurrence import rebuild_cooccurrences, update_cooccurrences


@pytest.fixture
def engine():
    eng = get_engine(":memory:")
    yield eng
    eng.dispose()


def _add_paper(session: Session, paper_id: str, keywords: list[str]) -> None:
    """Mimic the processor: upsert each keyword with this paper as a reference."""
    for kw in keywords:
        upsert_keyword(
            session,
            {"keyword": kw, "definition": "d", "paper_references": [paper_id]},
        )
    session.commit()


def _pairs(session: Session) -> dict[tuple[str, str], int]:
    return {
        (r.keyword_a, r.keyword_b): r.score
        for r in session.query(KeywordCooccurrence).all()
    }


def test_threshold_excludes_single_share(engine):
    # a&b share 2 papers; a&c share 1 paper.
    with Session(engine) as s:
        _add_paper(s, "p1", ["a", "b"])
        _add_paper(s, "p2", ["a", "b", "c"])
        update_cooccurrences(s, [["a", "b"], ["a", "b", "c"]])
        pairs = _pairs(s)

    assert pairs.get(("a", "b")) == 2
    assert pairs.get(("b", "a")) == 2
    # a&c and b&c share only one paper -> not stored.
    assert ("a", "c") not in pairs
    assert ("b", "c") not in pairs


def test_incremental_matches_full_rebuild(engine):
    papers = [
        ("p1", ["a", "b", "c"]),
        ("p2", ["a", "b", "d"]),
        ("p3", ["a", "c"]),
        ("p4", ["b", "c", "d"]),
    ]

    # Incremental: feed papers one batch at a time.
    with Session(engine) as s:
        for pid, kws in papers:
            _add_paper(s, pid, kws)
            update_cooccurrences(s, [kws])
        incremental = _pairs(s)

    # Full rebuild over the same final keyword state.
    with Session(engine) as s:
        rebuild_cooccurrences(s, threshold=2)
        rebuilt = _pairs(s)

    assert incremental == rebuilt
    # Sanity: every stored score meets the threshold and is symmetric.
    assert all(score >= 2 for score in incremental.values())
    for (a, b), score in incremental.items():
        assert incremental[(b, a)] == score


def test_idempotent(engine):
    with Session(engine) as s:
        _add_paper(s, "p1", ["a", "b"])
        _add_paper(s, "p2", ["a", "b"])
        update_cooccurrences(s, [["a", "b"], ["a", "b"]])
        first = _pairs(s)
        update_cooccurrences(s, [["a", "b"], ["a", "b"]])
        second = _pairs(s)

    assert first == second == {("a", "b"): 2, ("b", "a"): 2}


def test_pair_appears_only_when_crossing_threshold(engine):
    with Session(engine) as s:
        # First shared paper: below threshold, no row written.
        _add_paper(s, "p1", ["a", "b"])
        update_cooccurrences(s, [["a", "b"]])
        assert _pairs(s) == {}

        # Second shared paper pushes a&b to 2: the row now appears.
        _add_paper(s, "p2", ["a", "b"])
        update_cooccurrences(s, [["a", "b"]])
        assert _pairs(s) == {("a", "b"): 2, ("b", "a"): 2}


def test_duplicate_keywords_in_paper_do_not_inflate(engine):
    with Session(engine) as s:
        _add_paper(s, "p1", ["a", "b"])
        _add_paper(s, "p2", ["a", "b"])
        # Same paper batch passed with a duplicated keyword.
        update_cooccurrences(s, [["a", "a", "b"], ["a", "b", "b"]])
        pairs = _pairs(s)

    assert pairs == {("a", "b"): 2, ("b", "a"): 2}


def test_fewer_than_two_keywords_is_noop(engine):
    with Session(engine) as s:
        _add_paper(s, "p1", ["a"])
        update_cooccurrences(s, [["a"], []])
        assert _pairs(s) == {}
