"""
Shared TypedDict state schema for the Resume Optimizer LangGraph pipeline.
All agent nodes read from and write to this single state object.
"""

from typing import TypedDict, Optional, List, Annotated
from langgraph.graph.message import add_messages


class ResumeOptimizerState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────────
    jd_raw: str                     # Raw JD: plain text or URL
    jd_text: str                    # Cleaned, scraped JD text
    resume_latex: str               # Original LaTeX source from workspace/
    skills_md: str                  # Content of workspace/skills.md

    # ── Agent 1 — JD Reviewer output ─────────────────────────────────────────
    jd_analysis: dict               # {role, company, required_skills,
                                    #  preferred_skills, keywords, tone,
                                    #  ats_phrases, seniority, red_flags}

    # ── Agent 2 — Skills Matcher output ──────────────────────────────────────
    skills_match: dict              # {matched, partial, gaps,
                                    #  emphasis_recs, transferable}

    # ── Agent 3 — Resume Rewriter output (evolves per loop) ──────────────────
    optimized_latex: str            # Current best LaTeX
    rewrite_iteration: int          # How many times agent 3 has run

    # ── Agent 4 — HR Reviewer output ─────────────────────────────────────────
    hr_feedback: dict               # {score, pass, strengths,
                                    #  weaknesses, suggestions}

    # ── Agent 5 — ATS Checker output ─────────────────────────────────────────
    ats_report: dict                # {score, pass, keyword_hits,
                                    #  keyword_misses, format_issues,
                                    #  recommendations}

    # ── Control flow ─────────────────────────────────────────────────────────
    loop_count: int                 # Current feedback loop iteration
    max_loops: int                  # Hard cap on feedback loops
    final_approved: bool            # True when both HR+ATS pass (or cap hit)
    final_pdf_path: Optional[str]   # Absolute path to compiled PDF
    run_report: dict                # Full pipeline audit log
