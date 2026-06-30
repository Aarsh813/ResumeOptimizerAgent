"""
Agent 2 — Skills Analyser & Matcher
"""

import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from llm_factory import get_llm, invoke_with_retry
from state import ResumeOptimizerState


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "skills_matcher.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse failed: {e}", "raw_response": text[:500]}


def skills_matcher_node(state: ResumeOptimizerState) -> dict:
    skills_md   = state.get("skills_md", "")
    jd_analysis = state.get("jd_analysis", {})
    role        = jd_analysis.get("role") or "Unknown Role"

    print(f"  [Agent 2] Matching skills ({len(skills_md)} chars) against JD for '{role}'...")

    user_content = (
        f"## Job Description Analysis\n```json\n{json.dumps(jd_analysis, indent=2)}\n```\n\n"
        f"## Candidate Skills & Experience\n{skills_md}"
    )

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    response    = invoke_with_retry(get_llm(0.1), messages, "Agent 2")
    skills_match = _extract_json(response.content)

    matched_count = len(skills_match.get("matched_skills", []))
    gap_count     = len(skills_match.get("gaps", []))
    score         = skills_match.get("overall_match_score", "?")
    print(f"  [Agent 2] Done -- {matched_count} matches, {gap_count} gaps, score: {score}/100")

    return {"skills_match": skills_match}
