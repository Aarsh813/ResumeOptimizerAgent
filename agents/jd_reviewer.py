"""
Agent 1 — JD Reviewer
Analyzes a job description (URL or plain text) and returns structured JSON
with keywords, required skills, ATS phrases, and resume strategy.
"""

import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from tools.jd_scraper import get_jd_from_url
from llm_factory import get_llm, invoke_with_retry
from state import ResumeOptimizerState


# ── Load prompt ────────────────────────────────────────────────────────────────
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "jd_reviewer.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def _is_url(text: str) -> bool:
    return text.strip().startswith(("http://", "https://"))


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse failed: {e}", "raw_response": text[:500]}


def jd_reviewer_node(state: ResumeOptimizerState) -> dict:
    """
    LangGraph node for Agent 1.
    Reads state["jd_raw"], fetches URL if needed, runs LLM analysis,
    returns updated state keys: jd_text, jd_analysis.
    """
    jd_raw = state.get("jd_raw", "")

    # Step 1: resolve URL → text
    if _is_url(jd_raw):
        print(f"  [Agent 1] Fetching JD from URL: {jd_raw[:60]}...")
        jd_text = get_jd_from_url.invoke({"url": jd_raw})
        if jd_text.startswith("WARNING:"):
            print(f"\n  [Agent 1] *** SCRAPING WARNING ***")
            print(f"  {jd_text.splitlines()[0]}")
            print(f"  The JD analysis will be limited. Consider pasting the JD text directly.\n")
    else:
        jd_text = jd_raw
        print(f"  [Agent 1] Using plain text JD ({len(jd_text)} chars)")

    # Step 2: LLM analysis
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze this Job Description:\n\n{jd_text}"),
    ]

    print("  [Agent 1] Running JD analysis...")
    response = invoke_with_retry(get_llm(0.1), messages, "Agent 1")
    jd_analysis = _extract_json(response.content)

    role = jd_analysis.get("role") or "?"
    company = jd_analysis.get("company") or "?"
    print(f"  [Agent 1] Done -- role: {role}, company: {company}")

    return {
        "jd_text": jd_text,
        "jd_analysis": jd_analysis,
    }