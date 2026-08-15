"""
Resume screening: prompt construction + response parsing.

Kept as pure functions (no LLMClient dependency here) so the prompt
design and parsing robustness can be unit-tested without any LLM call at
all — only app/api/v1/recruitment/routes.py wires this together with a
real or fake LLMClient.
"""
import json
import re

from app.core.exceptions import AppError

_SCREENING_PROMPT_TEMPLATE = """You are an HR resume screening assistant. Compare the candidate's resume \
against the job requirements and respond with ONLY a JSON object (no other text) in this exact shape:

{{"score": <integer 0-100>, "summary": "<2-3 sentence assessment>"}}

Job Title: {job_title}
Job Requirements:
{job_requirements}

Candidate Resume:
{resume_text}

Respond with ONLY the JSON object."""


def build_screening_prompt(job_title: str, job_requirements: str, resume_text: str) -> str:
    return _SCREENING_PROMPT_TEMPLATE.format(
        job_title=job_title,
        job_requirements=job_requirements or "(no specific requirements listed)",
        resume_text=resume_text,
    )


def parse_screening_response(raw_response: str) -> tuple[float, str]:
    """
    Returns (score, summary). Raises AppError if the LLM's response can't be
    salvaged into that shape — this happens in practice (models sometimes wrap
    JSON in markdown fences, add a preamble, etc.), so this is deliberately
    forgiving: try direct parse first, then extract the first {...} block.
    """
    candidate_text = raw_response.strip()

    parsed = _try_json_parse(candidate_text)
    if parsed is None:
        match = re.search(r"\{.*\}", candidate_text, re.DOTALL)
        if match:
            parsed = _try_json_parse(match.group(0))

    if parsed is None:
        raise AppError(f"Could not parse a score from the LLM response: {raw_response[:200]!r}", status_code=502)

    score = parsed.get("score")
    summary = parsed.get("summary")

    if not isinstance(score, (int, float)):
        raise AppError(f"LLM response missing a valid numeric 'score': {parsed}", status_code=502)
    if not isinstance(summary, str) or not summary.strip():
        raise AppError(f"LLM response missing a 'summary': {parsed}", status_code=502)

    score = max(0.0, min(100.0, float(score)))  # clamp defensively even if the model ignores the 0-100 instruction
    return score, summary.strip()


def _try_json_parse(text: str) -> dict | None:
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None
