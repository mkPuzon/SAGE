import ast
import datetime as dt
import json
import os
import re

from openai import OpenAI

_client: OpenAI | None = None

_LITELLM_BASE_URL = "http://litellm.colby.edu:4000/v1"
_LITELLM_MODEL = "qwen-3.6-27b"
_OPENAI_KEYWORD_MODEL = "gpt-5-nano"
_OPENAI_DEFINITION_MODEL = "gpt-5.4"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        litellm_key = os.environ.get("LITELLM_API_KEY")
        if litellm_key:
            _client = OpenAI(api_key=litellm_key, base_url=_LITELLM_BASE_URL)
        else:
            _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _keyword_model() -> str:
    return _LITELLM_MODEL if os.environ.get("LITELLM_API_KEY") else _OPENAI_KEYWORD_MODEL


def _definition_model() -> str:
    return _LITELLM_MODEL if os.environ.get("LITELLM_API_KEY") else _OPENAI_DEFINITION_MODEL


def _keyword_prompt() -> str:
    return os.environ["KEYWORD_PROMPT_1"]


def _definition_prompt() -> str:
    return os.environ["DEFINITION_PROMPT_1"]

# Feed at most this many characters of paper text to the definition model.
# Keeps token costs predictable while covering the bulk of a typical paper.
_MAX_PAPER_CHARS = 15_000


def _parse_llm_response(raw: str):
    """Strip thinking block and optional markdown fences, then parse as a Python literal."""
    # Qwen reasoning mode inlines thinking content ending with </think> before the actual answer
    think_end = raw.find("</think>")
    if think_end != -1:
        raw = raw[think_end + len("</think>"):]
    cleaned = re.sub(r"^```(?:python)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return ast.literal_eval(cleaned.strip())


def extract_keywords(abstract: str) -> tuple[list[str], str, object]:
    """Return (keywords, model_name, usage) for an abstract."""
    response = _get_client().chat.completions.create(
        model=_keyword_model(),
        messages=[{"role": "user", "content": _keyword_prompt() + abstract}],
        temperature=1,
    )
    raw = response.choices[0].message.content.strip()
    result = _parse_llm_response(raw)
    if not isinstance(result, list):
        raise ValueError(f"Expected list from keyword model, got: {type(result)}")
    return [str(k) for k in result], response.model, response.usage


def _flatten_definition(value) -> str | None:
    """Normalize a definition value that may be a nested dict, string, or None."""
    if value is None or value == "None":
        return None
    if isinstance(value, dict):
        # Model sometimes returns {'definition': '...', 'importance': '...'}
        definition = value.get("definition")
        if definition and definition != "None":
            return str(definition)
        # Fall back to joining all non-empty values
        parts = [str(v) for v in value.values() if v and v != "None"]
        return " ".join(parts) if parts else None
    return str(value)


def _write_definition_sample(
    paper_id: str, keywords: list[str], prompt: str, response: str
) -> None:
    log_dir = os.environ.get("LOG_DIR")
    if not log_dir:
        return
    path = os.path.join(log_dir, "definition_samples.jsonl")
    record = {
        "timestamp": dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "paper_id": paper_id,
        "keywords": keywords,
        "prompt": prompt,
        "response": response,
    }
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def extract_definitions(
    paper_text: str,
    keywords: list[str],
    paper_id: str = "",
    capture: bool = False,
) -> tuple[dict[str, str | None], dict[str, str | None], str, object]:
    """Return (simple_defs, technical_defs, model_name, usage) derived from the full paper text."""
    truncated = paper_text[:_MAX_PAPER_CHARS]
    prompt = (
        _definition_prompt()
        + str(keywords)
        + "\n\nHere is the paper text:\n"
        + truncated
    )
    response = _get_client().chat.completions.create(
        model=_definition_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
    )
    raw = response.choices[0].message.content.strip()

    if capture:
        _write_definition_sample(paper_id, keywords, prompt, raw)

    result = _parse_llm_response(raw)
    if not isinstance(result, dict):
        raise ValueError(f"Expected dict from definition model, got: {type(result)}")

    simple: dict[str, str | None] = {}
    technical: dict[str, str | None] = {}
    for kw in keywords:
        entry = result.get(kw) or {}
        if isinstance(entry, dict):
            simple[kw] = _flatten_definition(entry.get("simple"))
            technical[kw] = _flatten_definition(entry.get("technical"))
        else:
            # Fallback if model returns a plain string instead of a nested dict
            simple[kw] = _flatten_definition(entry)
            technical[kw] = None
    return simple, technical, response.model, response.usage
