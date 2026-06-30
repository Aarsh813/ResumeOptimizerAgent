"""
Agent 4 — HR Reviewer
"""

import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from llm_factory import get_llm, invoke_with_retry
from state import ResumeOptimizerState


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "hr_reviewer.md"
_SYSTEM_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        return {
            "score": 5.0,
            "pass": False,
            "error": f"JSON parse failed: {e}",
            "suggestions": [],
            "weaknesses": [text[:300]],
        }


def hr_reviewer_node(state: ResumeOptimizerState) -> dict:
    jd_analysis     = state.get("jd_analysis", {})
    optimized_latex = state.get("optimized_latex", state.get("resume_latex", ""))
    role            = jd_analysis.get("role")    or "the role"
    company         = jd_analysis.get("company") or "the company"
    loop            = state.get("loop_count", 0)

    print(f"  [Agent 4] HR review for '{role}' at '{company}' (loop {loop})...")

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.replace("{company}", company).replace("{role}", role)

    user_content = (
        f"## Job Description Analysis\n```json\n{json.dumps(jd_analysis, indent=2)}\n```\n\n"
        f"## Resume to Review\n(LaTeX source — evaluate content, ignore LaTeX commands)\n\n"
        f"```\n{optimized_latex}\n```"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response    = invoke_with_retry(get_llm(0.3), messages, "Agent 4")
    hr_feedback = _extract_json(response.content)

    score  = hr_feedback.get("score", "?")
    passed = hr_feedback.get("pass", False)
    print(f"  [Agent 4] Done -- HR score: {score}/10, pass: {passed}")

    return {"hr_feedback": hr_feedback}
