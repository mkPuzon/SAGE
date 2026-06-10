import ast
import os
import re

from openai import OpenAI

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_KEY"])
    return _client

def _keyword_prompt() -> str:
    return os.environ["KEYWORD_PROMPT_1"]


def _definition_prompt() -> str:
    return os.environ["DEFINTION_PROMPT_1"]

_KEYWORD_MODEL = "gpt-4.1-nano"
_DEFINITION_MODEL = "gpt-5.4-mini"

# Feed at most this many characters of paper text to the definition model.
# Keeps token costs predictable while covering the bulk of a typical paper.
_MAX_PAPER_CHARS = 15_000


def _parse_llm_response(raw: str):
    """Strip optional markdown fences then parse as a Python literal."""
    cleaned = re.sub(r"^```(?:python)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return ast.literal_eval(cleaned.strip())


def extract_keywords(abstract: str) -> tuple[list[str], str, object]:
    """Return (keywords, model_name, usage) for an abstract."""
    response = _get_client().chat.completions.create(
        model=_KEYWORD_MODEL,
        messages=[{"role": "user", "content": _keyword_prompt() + abstract}],
        temperature=0,
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


def extract_definitions(
    paper_text: str, keywords: list[str]
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
        model=_DEFINITION_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    raw = response.choices[0].message.content.strip()
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
