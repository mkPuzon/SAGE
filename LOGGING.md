# SAGE Run Logging

Each time `job()` runs in `processor/main.py`, a structured JSON log file is written to `data/logs/run_YYYY-MM-DD.json` on the host (mounted into the processor container at `/data/logs/`). Re-runs on the same calendar day overwrite the file.

## Log Location

| Host path | Container path | Env var |
|-----------|---------------|---------|
| `./data/logs/run_YYYY-MM-DD.json` | `/data/logs/run_YYYY-MM-DD.json` | `LOG_DIR` |

## Implementation

Logging lives in `processor/src/logger.py`. A `RunLogger` instance is created at the top of `job()` and passed into `process_paper()`. The instance accumulates metrics in memory throughout the run and is flushed to disk in a `finally` block, so the log is written even when the job fails partway through.

### Timing

`time.perf_counter()` is used throughout — it has sub-millisecond resolution and is not affected by system clock adjustments.

Two context managers handle timing:

```python
# Top-level pipeline step (e.g. "fetch_papers", "backup_db")
with logger.time_step("fetch_papers"):
    papers = fetch_arxiv_papers(...)

# Per-paper sub-step (e.g. "extract_keywords", "download_pdf")
with logger.time_paper_step(paper_id, "extract_keywords"):
    keywords, model, usage = extract_keywords(abstract)
```

Each wraps its block in a `try/finally` so the duration is recorded even if the step raises.

### OpenAI Usage

`extract_keywords()` and `extract_definitions()` in `processor/src/extractor.py` each return a 3-tuple:

```python
return result, response.model, response.usage
```

`response.usage` is the raw object returned by the OpenAI Python SDK. Its fields are:
- `prompt_tokens` — tokens in the input (system + user message)
- `completion_tokens` — tokens in the model's response
- `total_tokens` — sum of the above

These are passed directly to `logger.record_openai_usage()`, which appends a record to `openai.calls` and accumulates running totals in `openai.totals`.

### Cost Calculation

Cost is computed per API call using a pricing table in `processor/src/logger.py`:

```python
MODEL_PRICING = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-5.4-mini": {"input": 0.75, "output": 4.45},
    "gpt-5.4-nano": {"input": 0.20, "output": 1.25}
}
```

Rates are USD per 1 million tokens. The formula applied to each call:

```
estimated_cost_usd = (prompt_tokens × input_rate + completion_tokens × output_rate) / 1_000_000
```

The model name used for the lookup comes from `response.model` (the string OpenAI echoes back in the response), not a local constant, so it reflects the actual model that served the request. If the model is not in `MODEL_PRICING`, `estimated_cost_usd` is set to `null` and `"pricing_unknown": true` is added to that call entry — the call is still recorded and its tokens still accumulate into the totals.

Run-level totals are accumulated incrementally as each call is recorded, so no second pass over the data is needed at write time.

**Important:** OpenAI pricing may change over time. Update `MODEL_PRICING` in `processor/src/logger.py` when prices change, and cross-reference against the OpenAI usage dashboard for billing accuracy.

## Log Schema

```jsonc
{
  // Unique identifier for this run; ISO 8601 timestamp of when job() started
  "run_id": "2026-05-30T02:00:00",
  "date": "2026-05-30",

  // Total wall-clock time for the entire job() call, in seconds
  "duration_seconds": 142.3,

  // Duration of each top-level pipeline phase
  "steps": {
    "fetch_papers":        { "duration_seconds": 1.2  },
    "process_papers":      { "duration_seconds": 130.5 },  // includes 3s sleeps between papers
    "backup_db":           { "duration_seconds": 0.8  },
    "update_cooccurrences":{ "duration_seconds": 0.4  },
    "clean_backups":       { "duration_seconds": 0.05 }
  },

  // High-level paper counts for the run
  "papers": {
    "fetched":    25,  // total returned by arXiv API
    "skipped":    10,  // already in DB, no work done
    "processed":  14,  // successfully extracted and saved
    "errored":     1   // raised an exception; see papers_detail for which one
  },

  // Keyword counts (only counts keywords from "processed" papers)
  "keywords": {
    "total_extracted": 42   // 3 per paper × processed papers
  },

  // OpenAI API usage for this run
  "openai": {
    // One entry per API call, in the order they were made
    "calls": [
      {
        "step": "extract_keywords",       // which pipeline step made this call
        "paper_id": "2501.12345",
        "model": "gpt-4.1-nano",          // echoed from response.model
        "prompt_tokens": 150,
        "completion_tokens": 25,
        "total_tokens": 175,
        "estimated_cost_usd": 0.000025
        // "pricing_unknown": true        // present only when model not in MODEL_PRICING
      }
    ],
    // Aggregated totals across all calls
    "totals": {
      "prompt_tokens": 3500,
      "completion_tokens": 600,
      "total_tokens": 4100,
      "estimated_cost_usd": 0.00121,
      // Breakdown by model — useful for comparing model costs
      "by_model": {
        "gpt-4.1-nano": {
          "prompt_tokens": 1500,
          "completion_tokens": 300,
          "total_tokens": 1800,
          "estimated_cost_usd": 0.00027
        },
        "gpt-5.4-mini": {
          "prompt_tokens": 2000,
          "completion_tokens": 300,
          "total_tokens": 2300,
          "estimated_cost_usd": 0.00094
        }
      }
    }
  },

  // One entry per paper, in processing order
  "papers_detail": [
    {
      "paper_id": "2501.12345",
      "title": "Attention Is All You Need",
      "status": "processed",            // "processed" | "skipped" | "errored"
      "keywords": ["Transformer", "Self-Attention", "Positional Encoding"],
      "duration_seconds": 8.5,          // null for skipped papers
      "steps": {
        "extract_keywords":   { "duration_seconds": 0.5 },
        "download_pdf":       { "duration_seconds": 2.1 },
        "extract_definitions":{ "duration_seconds": 5.3 },
        "db_upsert":          { "duration_seconds": 0.6 }
      }
    }
  ]
}
```
