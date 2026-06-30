"""
Agent 5 — ATS Checker
"""

import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from llm_factory import get_llm, invoke_with_retry
from state import ResumeOptimizerState
from tools.pdf_parser import extract_text_from_pdf


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "ats_checker.md"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        return {
            "score": 50,
            "pass": False,
            "error": f"JSON parse failed: {e}",
            "keyword_misses": [],
            "format_issues": [{"issue": "Could not parse ATS report", "severity": "Unknown", "fix": "Retry"}],
            "recommendations": [],
        }


def _strip_latex_commands(latex: str) -> str:
    """Extract readable text from LaTeX source for ATS simulation."""
    text = re.sub(r"%.*$", "", latex, flags=re.MULTILINE)
    text = re.sub(r"\\(?:begin|end)\{[^}]*\}", "", text)
    text = re.sub(
        r"\\(?:documentclass|usepackage|geometry|setlength|definecolor|colorlet|"
        r"pagestyle|thispagestyle|renewcommand|setmainfont|fontsize|selectfont)\{[^}]*\}(?:\[[^]]*\])?",
        "", text
    )
    text = re.sub(
        r"\\(?:textbf|textit|emph|textcolor\{[^}]*\}|href\{[^}]*\}|underline|"
        r"large|Large|LARGE|huge|Huge|small|footnotesize|normalsize)\{([^}]*)\}",
        r"\1", text
    )
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^]]*\])?(?:\{[^}]*\})*", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ats_checker_node(state: ResumeOptimizerState) -> dict:
    jd_analysis     = state.get("jd_analysis", {})
    optimized_latex = state.get("optimized_latex", state.get("resume_latex", ""))
    final_pdf_path  = state.get("final_pdf_path")
    loop            = state.get("loop_count", 0)

    print(f"  [Agent 5] Running ATS check (loop {loop})...")

    if final_pdf_path:
        resume_text = extract_text_from_pdf(final_pdf_path)
        if resume_text.startswith("ERROR"):
            resume_text = _strip_latex_commands(optimized_latex)
    else:
        resume_text = _strip_latex_commands(optimized_latex)

    user_content = (
        f"## Job Description Analysis\n```json\n{json.dumps(jd_analysis, indent=2)}\n```\n\n"
        f"## Resume Text (as parsed by ATS)\n{resume_text}"
    )

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    response   = invoke_with_retry(get_llm(0.0), messages, "Agent 5")
    ats_report = _extract_json(response.content)

    score  = ats_report.get("score", "?")
    passed = ats_report.get("pass", False)
    misses = len(ats_report.get("keyword_misses", []))
    print(f"  [Agent 5] Done -- ATS score: {score}/100, pass: {passed}, {misses} keyword misses")

    return {"ats_report": ats_report}
