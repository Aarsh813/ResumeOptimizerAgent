"""
Agent 3 — Resume Rewriter
"""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from llm_factory import get_llm, invoke_with_retry
from state import ResumeOptimizerState


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "resume_rewriter.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def _build_user_message(state: ResumeOptimizerState) -> str:
    iteration       = state.get("rewrite_iteration", 0)
    jd_analysis     = state.get("jd_analysis", {})
    skills_match    = state.get("skills_match", {})
    resume_latex    = state.get("resume_latex", "")
    optimized_latex = state.get("optimized_latex", "")
    hr_feedback     = state.get("hr_feedback", {})
    ats_report      = state.get("ats_report", {})

    current_latex = optimized_latex if optimized_latex else resume_latex

    parts = [
        "## Job Description Analysis",
        f"```json\n{json.dumps(jd_analysis, indent=2)}\n```",
        "",
        "## Skills Match Report",
        f"```json\n{json.dumps(skills_match, indent=2)}\n```",
        "",
        "## Current Resume (LaTeX Source)",
        "```latex",
        current_latex,
        "```",
    ]

    if iteration > 0 and hr_feedback:
        parts += [
            "",
            f"## Previous HR Reviewer Feedback (Iteration {iteration})",
            f"```json\n{json.dumps(hr_feedback, indent=2)}\n```",
            "Address ALL weaknesses and suggestions above.",
        ]

    if iteration > 0 and ats_report:
        parts += [
            "",
            f"## Previous ATS Checker Report (Iteration {iteration})",
            f"```json\n{json.dumps(ats_report, indent=2)}\n```",
            "Fix ALL format_issues and add ALL keyword_misses from the ATS report.",
        ]

    return "\n".join(parts)


def resume_rewriter_node(state: ResumeOptimizerState) -> dict:
    iteration  = state.get("rewrite_iteration", 0)
    loop_count = state.get("loop_count", 0)
    role       = state.get("jd_analysis", {}).get("role") or "Unknown Role"

    print(f"  [Agent 3] Rewriting resume for '{role}' "
          f"(rewrite #{iteration + 1}, feedback loop #{loop_count})...")

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=_build_user_message(state)),
    ]

    response        = invoke_with_retry(get_llm(0.2), messages, "Agent 3")
    optimized_latex = response.content.strip()

    # Strip markdown fences if the model wrapped the output
    if optimized_latex.startswith("```"):
        lines = optimized_latex.split("\n")
        optimized_latex = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    print(f"  [Agent 3] Done -- output is {len(optimized_latex)} chars of LaTeX")

    return {
        "optimized_latex": optimized_latex,
        "rewrite_iteration": iteration + 1,
    }
