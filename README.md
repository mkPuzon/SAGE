# SAGE — AI Research Glossary

A website for exploring cutting-edge AI research through a dynamic, LLM-generated glossary. Papers are scraped from arXiv daily, keywords are extracted from their abstracts, and plain-English definitions are derived from the full paper text. The result is a searchable, living glossary that grows as new research is published.

## Architecture

SAGE runs on three services
1) Nginx instance to serve the front end and hit the api
2) The api to query the database
3) A scheuled Python data processor

All three services run in a single Docker Compose network. The only port exposed to the host is `8080` on nginx. The `processor` and `api` containers share a SQLite database via a bind-mounted host directory (`./data/db/`), so data persists across container restarts.

## Tech Stack

| Layer | Tools |
|-------|------|
| Backend | FastAPI, Python 3.12 |
| Database | SQLite via SQLAlchemy 2.x |
| Scraping | `requests`, `xml.etree` |
| PDF parsing | `pypdf` |
| LLM | OpenAI (`gpt-4.1-nano`, `gpt-5.4-mini`) |
| Reverse proxy | nginx |
| Frontend | HTML, CSS, JS |
| Containerization | Docker Compose |


## Services

### processor

A one-shot Python script that runs the full data pipeline scheduled with the Python `schedule` library for each morning at 2am.

`PYTHONPATH` has two entries: `/app` so that `import shared.models` resolves, and `/app/processor` so that `processor/main.py`'s existing `from src.scraper import ...` resolves without modification.

**Environment** (injected via `env_file: .env` in Compose):
- `OPENAI_KEY` — OpenAI API key
- `KEYWORD_PROMPT_1` — prompt template for keyword extraction
- `DEFINTION_PROMPT_1` — prompt template for definition extraction

Not needed in `.env` file, but good to know:
- `DB_PATH` — absolute path to the SQLite file inside the container (`/data/db/sage.db`)
- `BACKUP_DIR` — absolute path for daily backup files (`/data/backups`)

### api

A FastAPI application served by uvicorn. It mounts the same SQLite bind mount as the processor (read-only in practice) and exposes two search endpoints consumed by the frontend.

The `api` container is not exposed directly to the host. All traffic reaches it through nginx.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/keywords?q=<query>` | Case-insensitive substring search across keyword names. Returns up to 20 results ordered by `count` descending. |
| `GET` | `/api/keywords/{keyword}` | Full keyword record with definition, count, and joined article metadata for every paper that references it. Returns 404 if not found. |
| `GET` | `/api/keywords/{keyword}/related` | Up to 10 related keywords ordered by co-occurrence score descending. Returns `[]` if none exist. |
| `GET` | `/health` | Liveness check — returns `{"status": "ok"}`. |

### nginx

An `nginx:alpine` container that acts as the sole public entry point. It serves the static frontend files baked into the image at build time and reverse-proxies API traffic to the `api` container.

**Routing** (`nginx/nginx.conf`):

```
location /api/   → proxy_pass http://api:8000
location /health → proxy_pass http://api:8000/health
location /       → /usr/share/nginx/html (static files)
```

Because the frontend JavaScript uses relative paths (`/api/...`), requests originate from the same origin that served the page. nginx handles the routing entirely, so there are no CORS issues and no hardcoded hostnames in client-side code.

**Dockerfile** (`nginx/Dockerfile`):
```
FROM nginx:alpine
COPY nginx/nginx.conf → /etc/nginx/nginx.conf
COPY frontend/        → /usr/share/nginx/html/
```

The frontend files are copied into the image at build time, not mounted at runtime. Rebuilding the nginx image is required after any frontend change.


## Shared Database Layer

`shared/models.py` is the source for the database schema. Both `processor` and `api` import from it; each Dockerfile copies the `shared/` directory into its image.

SQLAlchemy 2.x with SQLite is used. The `get_engine()` function creates the engine and runs `CREATE TABLE IF NOT EXISTS` for both tables on startup.

### Schema

**`articles` table**

| Column | Type | Notes |
|--------|------|-------|
| `paper_id` | `TEXT` PK | arXiv ID (e.g. `2501.12345`) |
| `title` | `TEXT` | Paper title |
| `arxiv_url` | `TEXT` | `https://arxiv.org/abs/<id>` |
| `pdf_url` | `TEXT` | `https://arxiv.org/pdf/<id>` |
| `date_submitted` | `TEXT` | ISO date the paper was submitted to arXiv |
| `date_scraped` | `TEXT` | ISO date SAGE processed this paper |
| `tags` | `JSON` | arXiv category list, e.g. `["cs.AI", "cs.LG"]` |
| `abstract` | `TEXT` | Full abstract text |

**`keywords` table**

| Column | Type | Notes |
|--------|------|-------|
| `keyword` | `TEXT` PK | Term in title case, e.g. `"Transformer Architecture"` |
| `definition` | `TEXT` | LLM-generated plain-English definition |
| `count` | `INTEGER` | Number of times this keyword has been extracted across all papers |
| `paper_references` | `JSON` | List of `paper_id` strings that reference this keyword |

`tags` and `paper_references` are stored as JSON strings in SQLite (SQLAlchemy's `JSON` type handles serialization transparently). When upserting a keyword that already exists, `count` is incremented and `paper_references` is merged as a set to prevent duplicates.

**`keyword_cooccurrences` table**

| Column | Type | Notes |
|--------|------|-------|
| `keyword_a` | `TEXT` PK | Source keyword |
| `keyword_b` | `TEXT` PK | Related keyword |
| `score` | `INTEGER` | Number of papers that reference both keywords |

Composite primary key on `(keyword_a, keyword_b)`. SQLite builds a B-tree over this key with `keyword_a` as the leading column, so lookups by `keyword_a` are an indexed range scan — O(log N) — regardless of table size.


## Related Keywords

The sidebar on each keyword's detail panel shows terms that tend to appear together with it across the paper corpus.

### How similarity is determined

Two keywords are considered related if they were both extracted from **at least 2 papers in common**. The `score` between keyword A and keyword B is the count of papers that reference both, and pairs that share only a single paper are not stored at all — this keeps the table lean and filters out incidental, one-off co-occurrences. A higher score means the two concepts co-occur more frequently and are more likely to be genuinely related. This is a **co-occurrence model**: no embedding vectors, no semantic similarity, no ML — just counting shared papers. It is fast to compute and trivial to interpret.

### How the index is updated

Each daily processor job updates the index **incrementally** via `update_cooccurrences` in `processor/src/cooccurrence.py`, rather than rebuilding the whole table:

1. **Find affected pairs** — only pairs of keywords that appear together in a *newly added* paper can change, because papers are never removed and a pair's shared-paper count only ever increases. The job collects each new paper's keyword set and generates the candidate (A, B) pairs.
2. **Recompute authoritative scores** — for each affected pair, the true score is recomputed as the size of the set intersection of the two keywords' `paper_references` (already committed by the keyword upsert). This is idempotent and self-correcting, so duplicate pairs within a batch are harmless.
3. **Upsert if ≥ threshold** — a pair's row (both `(A, B)` and `(B, A)`, so every API query is a simple `WHERE keyword_a = ?`) is written only when its score reaches 2. Sub-threshold pairs were never stored, so nothing needs to be deleted.

`rebuild_cooccurrences(session, threshold=2)` still performs a full wipe-and-rewrite and is used for seeding and for the one-time reconciliation command (`python main.py reconcile-cooccurrences`), which purges any legacy score-1 rows from an existing DB. All of this runs offline (inside the processor), never on the request path.

### Scaling characteristics

| Dimension | Behaviour |
|-----------|-----------|
| Query time | O(log N) — indexed PK lookup; unaffected by corpus size |
| Daily update time | O(p × k²) where p = new papers per run and k = keywords per paper (3) — independent of total corpus size, unlike the old full rebuild |
| Full rebuild time | O(K × d²) where K = keyword count, d = average papers per keyword — only paid during seeding/reconciliation |
| Table size | O(K × d) rows in practice (sparse); worst case O(K²) if every keyword co-occurs with every other |


## Scraper Pipeline

The pipeline is orchestrated by `processor/main.py` and runs once per day. Each paper is processed sequentially with a 3-second sleep between papers to respect arXiv's rate limits.

### Step 1 — Fetch paper metadata (`src/scraper.py`)

Papers are fetched from the [arXiv API](https://info.arxiv.org/help/api/index.html) using a single HTTP GET:

```
GET http://export.arxiv.org/api/query
    ?search_query=cat:cs.AI
    &start=0
    &max_results=<num_papers>
    &sortBy=submittedDate
    &sortOrder=descending
```

The API returns an **Atom XML feed** (RFC 4287). Each `<entry>` element contains:

```xml
<entry>
  <id>http://arxiv.org/abs/2501.12345v1</id>
  <title>Paper Title</title>
  <summary>Abstract text...</summary>
  <published>2025-01-19T18:00:00Z</published>
  <category term="cs.AI" scheme="..."/>
  <category term="cs.LG" scheme="..."/>
</entry>
```

The parser (`xml.etree.ElementTree`; Python built-in library) walks the feed using the Atom namespace `{http://www.w3.org/2005/Atom}`:

1. **Extract arXiv ID** — the `<id>` URL is matched against `arxiv\.org/abs/([\w.]+?)(?:v\d+)?$` to strip the version suffix. The result (`2501.12345`) becomes `paper_id`.
2. **Construct URLs** — `arxiv_url` and `pdf_url` are built from the ID rather than parsed from link tags, since the URL pattern is stable.
3. **Collect tags** — all `<category term="...">` elements are collected into a list.
4. **Normalize text** — newlines are collapsed in title and abstract fields.

Papers already present in the database (checked by primary key before any further work) are skipped without making any API or LLM calls.

### Step 2 — Extract keywords (`src/extractor.py`)

The abstract is appended to `KEYWORD_PROMPT_1` from `.env` and sent to **`gpt-4.1-nano`** with `temperature=0`:

```
KEYWORD_PROMPT_1 + abstract_text
```

The prompt instructs the model to return exactly three keywords as a Python list string, e.g.:

```python
['State Space Model', 'Sparse Attention Module', 'Vision Transformer']
```

The response is parsed with `ast.literal_eval` after stripping any markdown code fences the model may have added. `temperature=0` is used throughout to make outputs deterministic and parseable.

### Step 3 — Download and extract PDF text (`src/pdf_reader.py`)

The PDF is downloaded directly from `https://arxiv.org/pdf/<arxiv_id>` using `requests` with a 60-second timeout and a descriptive `User-Agent` header (arXiv's API guidelines require this).

Text is extracted with **`pypdf`** (pure Python, no system dependencies). Only the first 15 pages are processed — sufficient to cover the introduction, methodology, and most results sections of a typical paper while keeping memory usage bounded.

Each page's text is extracted independently and joined with newlines. The combined result is then **truncated to 15,000 characters** before being sent to the LLM, keeping token costs predictable regardless of paper length.

### Step 4 — Extract definitions (`src/extractor.py`)

The extracted paper text, along with the keyword list, is sent to **`gpt-5.4-mini`** with the `DEFINTION_PROMPT_1` template:

```
DEFINTION_PROMPT_1 + str(keywords) + "\n\nHere is the paper text:\n" + paper_text[:15000]
```

The model returns a Python dict mapping each keyword to a definition string. The same `ast.literal_eval` parsing is applied. A normalization step (`_flatten_definition`) handles cases where the model returns nested dicts (e.g. `{'definition': '...', 'importance': '...'}`) by extracting the `definition` key or joining all values.

### Step 5 — Upsert to database

The article record is inserted. For each keyword:

- If the keyword does not exist: insert with `count=1` and `paper_references=[paper_id]`.
- If the keyword already exists: increment `count`, merge `paper_references` as a set (deduplicating if the same paper is processed again), then reassign the list (SQLAlchemy requires reassignment, not in-place mutation, to detect the change).

### Step 6 — Backup

After all papers are processed, `sqlite3.Connection.backup()` is used to write a point-in-time snapshot to `./data/backups/sage_YYYY-MM-DD.db`. This uses SQLite's built-in online backup API, which is safe to run while the `api` container holds an open connection to the live database.


## Data Persistence

The SQLite database is stored at `./data/db/sage.db` on the host via a **bind mount** (not a Docker named volume). This means the file is always accessible on the host filesystem and survives `docker compose down`, Docker restarts, and image rebuilds.

```
./data/
  db/
    sage.db            ← live database (bind-mounted into processor + api)
  backups/
    sage_2026-01-01.db ← daily snapshots written by the processor
    sage_2026-01-02.db
    ...
```


## Testing

```bash
pytest tests/
```

`tests/db_tests/test_data_models.py` runs against an in-memory SQLite database and covers:

- Article creation and JSON column round-tripping
- Keyword upsert incrementing `count` across multiple papers
- Keyword upsert deduplicating `paper_references` when the same paper_id appears twice
- New keywords starting with `count == 1`


# TODOs
# v2 Next steps
Backend
- [X] Complete search page functionality
- [x] Add threshold of 2 papers for cooccurence; keywords that only occurr in the same paper 1 time are not added to the table.
- [x] Implement incremental keyword cooccurnce updates instead of a total table rewrite
- [ ] Schedule deletion of backups
- [ ] Add logging across processor and db operations

- [ ] Revise prompts for more explicitly structured definitions
- [ ] Generate two definition: one technical, one accessable


Frontend
- [X] Complete search page prototype 
- [ ] Print full categories instead of tags


# v3 Next steps
- [ ] Add an term explore page (graph)
- [ ] Run cost metrics for scraper and adjust model 