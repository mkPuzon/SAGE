from collections import defaultdict
from itertools import combinations

from sqlalchemy.orm import Session

from shared.models import Keyword, KeywordCooccurrence


def rebuild_cooccurrences(session: Session, threshold: int = 2) -> None:
    """Wipe and rebuild the whole co-occurrence table from scratch.

    Used for full rebuilds (seeding, one-time reconciliation). Only pairs that
    share at least `threshold` papers are stored, keeping the table lean.
    Prefer `update_cooccurrences` for incremental daily updates.
    """
    all_keywords = session.query(Keyword).all()

    paper_to_keywords: dict[str, list[str]] = defaultdict(list)
    for kw in all_keywords:
        for paper_id in (kw.paper_references or []):
            paper_to_keywords[paper_id].append(kw.keyword)

    counts: dict[tuple[str, str], int] = defaultdict(int)
    for kws in paper_to_keywords.values():
        for a, b in combinations(sorted(set(kws)), 2):
            counts[(a, b)] += 1
            counts[(b, a)] += 1

    session.query(KeywordCooccurrence).delete()
    written = 0
    for (a, b), score in counts.items():
        if score >= threshold:
            session.add(KeywordCooccurrence(keyword_a=a, keyword_b=b, score=score))
            written += 1
    session.commit()
    print(f"  Co-occurrence table rebuilt ({written} pairs, threshold={threshold}).")


def update_cooccurrences(
    session: Session,
    new_paper_keywords: list[list[str]],
    threshold: int = 2,
) -> None:
    """Incrementally update the co-occurrence table for newly added papers.

    `new_paper_keywords` is one list of keywords per newly-added paper. Since
    papers are never removed, a pair's shared-paper count only ever increases,
    and a pair can only change if both of its keywords appear together in a new
    paper. For each such pair we recompute the authoritative count via set
    intersection of the keywords' (already committed) paper_references and write
    the row only if it meets the threshold. This is idempotent and self-correcting.
    """
    # 1. Collect the unordered affected pairs across the whole batch (a < b).
    affected: set[tuple[str, str]] = set()
    for kws in new_paper_keywords:
        for a, b in combinations(sorted(set(kws)), 2):
            affected.add((a, b))

    if not affected:
        return

    # 2. Cache each keyword's committed paper_references as a set.
    refs_cache: dict[str, set[str]] = {}

    def refs_for(kw: str) -> set[str]:
        if kw not in refs_cache:
            row = session.get(Keyword, kw)
            refs_cache[kw] = set(row.paper_references or []) if row else set()
        return refs_cache[kw]

    # 3. Recompute authoritative score per pair; store both directions if >= threshold.
    updated = 0
    for a, b in affected:
        score = len(refs_for(a) & refs_for(b))
        if score >= threshold:
            _upsert_pair(session, a, b, score)
            _upsert_pair(session, b, a, score)
            updated += 1
        # score < threshold: leave the pair unstored. Scores only increase, so a
        # sub-threshold pair was never written and there is nothing to delete.
    session.commit()
    print(f"  Co-occurrence table updated ({updated} pairs, threshold={threshold}).")


def _upsert_pair(session: Session, a: str, b: str, score: int) -> None:
    existing = session.get(KeywordCooccurrence, (a, b))  # composite PK tuple
    if existing:
        existing.score = score
    else:
        session.add(KeywordCooccurrence(keyword_a=a, keyword_b=b, score=score))
