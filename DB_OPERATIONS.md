# DB Operations — Keyword Duplicate Handling

This document traces exactly how the SAGE pipeline creates and updates rows in the `keywords` table, with special focus on what happens when a keyword already exists.

---

## Overview

Every keyword extracted from a paper passes through `upsert_keyword()` (`processor/src/seed.py:166`). The function performs a primary-key lookup first: if the keyword is new it inserts a full row; if it already exists it merges the new paper's data into the existing row. The definition written at first insert is **never overwritten** — only `count`, `paper_references`, and `dates` change on subsequent encounters.

---

## Pipeline Call Chain

Each paper goes through this sequence inside `process_paper()` (`processor/main.py:40`):

1. **Article dedup check** (`main.py:44`)
   ```python
   if s.get(Article, paper_id):
       return  # skip — paper already fully processed
   ```
   This is the primary guard. A paper that committed successfully is never reprocessed.

2. **Keyword extraction** (`main.py:51`)
   ```python
   keywords = extract_keywords(paper["abstract"])
   # → calls gpt-4.1-nano, returns list of 3 strings
   ```
   Source: `processor/src/extractor.py:38`

3. **PDF download and text extraction** (`main.py:55`)
   Up to 15 pages extracted by `pypdf`, then truncated to 15,000 chars before any LLM call.
   Source: `processor/src/pdf_reader.py`

4. **Definition extraction** (`main.py:59`)
   ```python
   definitions = extract_definitions(pdf_text, keywords)
   # → calls gpt-5.4-mini, returns {keyword: definition_string}
   ```
   Source: `processor/src/extractor.py:67`

5. **DB writes** (`main.py:61–74`)
   ```python
   with Session(engine) as s:
       s.add(Article(**paper))
       for kw in keywords:
           definition = definitions.get(kw)
           upsert_keyword(s, {
               "keyword": kw,
               "definition": definition or "Definition not available.",
               "paper_references": [paper_id],
               "dates": [paper["date_submitted"]],
           })
       s.commit()
   ```
   All writes — the article row and all keyword upserts — are committed in a single transaction.

6. **Cooccurrence rebuild** (`main.py:102–103`)
   ```python
   with Session(engine) as session:
       rebuild_cooccurrences(session)
   ```
   Runs after all papers in the batch are processed. Full table wipe and rewrite.
   Source: `processor/src/cooccurrence.py:9`

---

## `upsert_keyword()` — Full Logic

`processor/src/seed.py:166`

```python
def upsert_keyword(session: Session, kw_data: dict) -> None:
    existing = session.get(Keyword, kw_data["keyword"])
    if existing:
        existing.count += 1
        refs = set(existing.paper_references or [])
        refs.update(kw_data["paper_references"])
        existing.paper_references = list(refs)
        existing.dates = (existing.dates or []) + kw_data.get("dates", [])
    else:
        session.add(
            Keyword(
                keyword=kw_data["keyword"],
                definition=kw_data["definition"],
                count=1,
                paper_references=kw_data["paper_references"],
                dates=kw_data.get("dates", []),
            )
        )
```

---

## Field-by-Field Behaviour

| Column | Type | First insert | Subsequent upsert |
|--------|------|-------------|-------------------|
| `keyword` | `TEXT PK` | Set from `kw_data["keyword"]` | Unchanged — used as the lookup key |
| `definition` | `TEXT` | Set from `kw_data["definition"]` | **Never updated** |
| `count` | `INTEGER` | `1` | Incremented by `1` per upsert call |
| `paper_references` | `JSON` | `[paper_id]` | Set-merged with new IDs, then reassigned |
| `dates` | `JSON` | `[date_submitted]` | New dates appended — **no deduplication** |

### `definition`
The definition generated from the first paper to introduce a keyword is stored and never touched again. All subsequent papers may produce a different (potentially better) definition via the LLM, but it is silently discarded in `upsert_keyword`. The incoming `kw_data["definition"]` is only used in the `else` branch.

### `count`
Incremented once per call to `upsert_keyword`, which happens once per keyword per paper. This accurately counts the number of papers that referenced the keyword **as long as each paper is processed exactly once** (enforced by the article-level dedup check). If a paper somehow gets processed twice (crash between article insert and keyword commit), `count` inflates while `paper_references` stays correct.

### `paper_references`
Stored as a JSON array. On update, the existing list is converted to a `set`, updated with the new paper IDs, then converted back to a list and **reassigned**:

```python
refs = set(existing.paper_references or [])
refs.update(kw_data["paper_references"])
existing.paper_references = list(refs)
```

The explicit reassignment (`= list(refs)`) is required because SQLAlchemy tracks JSON column changes by object identity. Mutating the list in-place (e.g. `.append()`) would leave the column unmarked as dirty and the change would not be persisted.

The set conversion guarantees no duplicate `paper_id` strings. List order after conversion is non-deterministic (Python set iteration order).

### `dates`
Appended with simple list concatenation — **no deduplication**:

```python
existing.dates = (existing.dates or []) + kw_data.get("dates", [])
```

Each call appends the new paper's `date_submitted` string. The list grows by one entry per paper that references the keyword, in the order papers were processed. Because there is no set-conversion step, reprocessing the same paper would append the same date again.

---

## Notable Behaviours

### Definition is frozen at first insert
Once a keyword row exists, its definition is never changed regardless of how many additional papers reference it. The upsert branch (`if existing:`) has no assignment to `existing.definition`. To update a definition, a direct SQL update or a manual reset of the row is required.

### `count` and `paper_references` can diverge
`count` is a call counter; `len(paper_references)` reflects unique papers. Under normal operation these are equal. They can diverge only if:
- A paper is reprocessed (article insert succeeded but keyword commit crashed): `count` increments again, `paper_references` does not grow.
- Seed data with multi-paper `paper_references` arrays: the seed passes `["id1", "id2", "id3"]` in one call, so `count` increments by 1 but `len(paper_references)` grows by 3.

### `dates` is not deduplicated
Unlike `paper_references`, `dates` is never passed through a set. This is consistent with its purpose as an ordered log of when the keyword appeared in the corpus, but it means duplicate dates are possible under reprocessing.

### Article-level guard is the primary dedup mechanism
`process_paper()` (`main.py:44`) exits immediately if the article's `paper_id` is already in the `articles` table. Because the article row and all keyword rows are committed in the same transaction (`main.py:74`), a successfully committed article guarantees its keywords were also committed. The only window where `upsert_keyword` could be called twice for the same paper is a crash between `s.add(Article(...))` and `s.commit()` — in that case the article row is not committed, so the next run would reprocess the paper and call `upsert_keyword` again.

---

## Cooccurrence Table

`processor/src/cooccurrence.py:9`

The `keyword_cooccurrences` table is fully rebuilt after every processor job (and after seeding). It has no insert/update path — only wipe and rewrite.

### Rebuild steps

1. **Invert the keyword index**
   Query all `Keyword` rows. For each keyword, iterate its `paper_references` JSON array and build a `paper_id → [keyword, ...]` map in memory.

2. **Count co-occurring pairs**
   For each paper, generate all `(A, B)` pairs from its keyword list using `combinations(sorted(kws), 2)`. Both `(A, B)` and `(B, A)` are incremented so that every API query is a simple `WHERE keyword_a = ?` with no `OR` clause.

3. **Wipe and rewrite**
   ```python
   session.query(KeywordCooccurrence).delete()
   for (a, b), score in counts.items():
       session.add(KeywordCooccurrence(keyword_a=a, keyword_b=b, score=score))
   session.commit()
   ```
   The full table is deleted and repopulated in one transaction. The table is always consistent with the current `paper_references` data — there is no partial state.

### Schema

| Column | Type | Notes |
|--------|------|-------|
| `keyword_a` | `TEXT PK` | Source keyword (leading PK column — indexed) |
| `keyword_b` | `TEXT PK` | Related keyword |
| `score` | `INTEGER` | Number of papers referencing both keywords |

The composite primary key `(keyword_a, keyword_b)` gives O(log N) lookups by `keyword_a`. The API uses `WHERE keyword_a = ?` ordered by `score DESC LIMIT 10`.
