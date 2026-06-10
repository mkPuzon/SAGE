import json
import os
import re
import time
from contextlib import contextmanager

# USD per 1M tokens — verify and update as OpenAI pricing changes
MODEL_PRICING = {
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-5.4-mini": {"input": 0.75, "output": 4.45},
}


class RunLogger:
    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._start = time.perf_counter()
        self._steps: dict = {}
        self._paper_records: dict[str, dict] = {}
        self._openai_calls: list[dict] = []
        self._openai_totals: dict = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "by_model": {},
        }

    def _get_or_create_paper(self, paper_id: str) -> dict:
        if paper_id not in self._paper_records:
            self._paper_records[paper_id] = {
                "paper_id": paper_id,
                "title": "",
                "status": "unknown",
                "keywords": [],
                "duration_seconds": None,
                "steps": {},
            }
        return self._paper_records[paper_id]

    @contextmanager
    def time_step(self, name: str):
        """Context manager that records wall-clock duration for a top-level pipeline step."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self._steps[name] = {"duration_seconds": round(time.perf_counter() - t0, 3)}

    @contextmanager
    def time_paper_step(self, paper_id: str, name: str):
        """Context manager that records wall-clock duration for one sub-step of a paper."""
        record = self._get_or_create_paper(paper_id)
        t0 = time.perf_counter()
        try:
            yield
        finally:
            record["steps"][name] = {"duration_seconds": round(time.perf_counter() - t0, 3)}

    def record_paper(
        self,
        paper_id: str,
        title: str,
        status: str,
        keywords: list[str] | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        record = self._get_or_create_paper(paper_id)
        record.update({
            "title": title,
            "status": status,
            "keywords": keywords or [],
            "duration_seconds": duration_seconds,
        })

    def record_openai_usage(self, step: str, paper_id: str, model: str, usage) -> None:
        if usage is None:
            return
        model = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model)
        pricing = MODEL_PRICING.get(model)
        if pricing:
            cost = round(
                (usage.prompt_tokens * pricing["input"] + usage.completion_tokens * pricing["output"])
                / 1_000_000,
                8,
            )
            pricing_unknown = False
        else:
            cost = None
            pricing_unknown = True

        call: dict = {
            "step": step,
            "paper_id": paper_id,
            "model": model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost_usd": cost,
        }
        if pricing_unknown:
            call["pricing_unknown"] = True
        self._openai_calls.append(call)

        self._openai_totals["prompt_tokens"] += usage.prompt_tokens
        self._openai_totals["completion_tokens"] += usage.completion_tokens
        self._openai_totals["total_tokens"] += usage.total_tokens
        if cost is not None:
            self._openai_totals["estimated_cost_usd"] = round(
                self._openai_totals["estimated_cost_usd"] + cost, 8
            )

        by_model = self._openai_totals["by_model"]
        if model not in by_model:
            by_model[model] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
            }
        m = by_model[model]
        m["prompt_tokens"] += usage.prompt_tokens
        m["completion_tokens"] += usage.completion_tokens
        m["total_tokens"] += usage.total_tokens
        if cost is not None:
            m["estimated_cost_usd"] = round(m["estimated_cost_usd"] + cost, 8)

    def write(self, log_dir: str, date: str) -> str:
        os.makedirs(log_dir, exist_ok=True)
        total_duration = round(time.perf_counter() - self._start, 3)
        papers_detail = list(self._paper_records.values())

        status_counts: dict[str, int] = {}
        for p in papers_detail:
            s = p["status"]
            status_counts[s] = status_counts.get(s, 0) + 1

        payload = {
            "run_id": self._run_id,
            "date": date,
            "duration_seconds": total_duration,
            "steps": self._steps,
            "papers": {
                "fetched": len(papers_detail),
                "skipped": status_counts.get("skipped", 0),
                "processed": status_counts.get("processed", 0),
                "errored": status_counts.get("errored", 0),
            },
            "keywords": {
                "total_extracted": sum(
                    len(p["keywords"]) for p in papers_detail if p["status"] == "processed"
                ),
            },
            "openai": {
                "calls": self._openai_calls,
                "totals": self._openai_totals,
            },
            "papers_detail": papers_detail,
        }

        path = os.path.join(log_dir, f"run_{date}.json")
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"  Run log written → {path}")
        return path
