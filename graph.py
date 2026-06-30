"""
LangGraph Pipeline — Resume Optimizer
Defines the full StateGraph with parallel execution and feedback loops.

Flow:
  scrape_jd → jd_reviewer ─┐
                            ├─(parallel)─→ skills_matcher → resume_rewriter
                            ┘                                     │
                                     ┌────────────────────────────┤
                                     │                            │
                                  hr_reviewer (parallel)    ats_checker (parallel)
                                     │                            │
                                     └──────────┬─────────────────┘
                                            feedback_agg
                                           ╱             ╲
                                    (loop back)       (finish)
                                   resume_rewriter   output_generator → END
"""

import json
import os
from datetime import datetime
from pathlib import Path

from langgraph.graph import StateGraph, END

from state import ResumeOptimizerState
from agents.jd_reviewer import jd_reviewer_node
from agents.skills_matcher import skills_matcher_node
from agents.resume_rewriter import resume_rewriter_node
from agents.hr_reviewer import hr_reviewer_node
from agents.ats_checker import ats_checker_node
from tools.latex_compiler import compile_latex


# ── Helper Nodes ──────────────────────────────────────────────────────────────

def feedback_aggregator_node(state: ResumeOptimizerState) -> dict:
    """
    Merges HR + ATS results, increments loop_count.
    The conditional edge reads the updated state to decide loop vs. finish.
    """
    hr_feedback = state.get("hr_feedback", {})
    ats_report = state.get("ats_report", {})
    loop_count = state.get("loop_count", 0) + 1

    hr_pass = hr_feedback.get("pass", False)
    ats_pass = ats_report.get("pass", False)
    hr_score = hr_feedback.get("score", 0)
    ats_score = ats_report.get("score", 0)

    print(f"\n  [Feedback] Loop {loop_count} results:")
    print(f"    HR:  {'✓ PASS' if hr_pass else '✗ FAIL'} (score: {hr_score}/10)")
    print(f"    ATS: {'✓ PASS' if ats_pass else '✗ FAIL'} (score: {ats_score}/100)")

    final_approved = hr_pass and ats_pass
    if final_approved:
        print("  [Feedback] Both reviewers PASSED — proceeding to output generation.")
    elif loop_count >= state.get("max_loops", 2):
        print(f"  [Feedback] Max loops ({state.get('max_loops', 2)}) reached — "
              "outputting best version.")
        final_approved = True  # force finish even if not perfect
    else:
        print(f"  [Feedback] Sending feedback to resume rewriter for loop {loop_count + 1}...")

    return {
        "loop_count": loop_count,
        "final_approved": final_approved,
    }


def output_generator_node(state: ResumeOptimizerState) -> dict:
    """
    Saves the final optimized LaTeX, attempts PDF compilation,
    and writes a full run report as JSON.
    """
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    optimized_latex = state.get("optimized_latex", "")
    jd_analysis = state.get("jd_analysis", {})
    role = jd_analysis.get("role", "resume").replace("/", "-").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{role}_{timestamp}"

    # Save .tex
    tex_path = output_dir / f"{base_name}.tex"
    tex_path.write_text(optimized_latex, encoding="utf-8")
    print(f"\n  [Output] LaTeX saved → {tex_path}")

    # Attempt PDF compilation
    print("  [Output] Compiling PDF...")
    pdf_result = compile_latex(optimized_latex, str(output_dir), base_name)
    if pdf_result.startswith("ERROR") or not os.path.exists(pdf_result):
        print(f"  [Output] ⚠ PDF compilation failed: {pdf_result[:100]}")
        pdf_path = None
    else:
        pdf_path = pdf_result
        print(f"  [Output] PDF compiled → {pdf_path}")

    # Build run report
    run_report = {
        "timestamp": timestamp,
        "role": jd_analysis.get("role"),
        "company": jd_analysis.get("company"),
        "total_loops": state.get("loop_count", 0),
        "rewrite_iterations": state.get("rewrite_iteration", 0),
        "final_approved": state.get("final_approved", False),
        "hr_feedback": state.get("hr_feedback", {}),
        "ats_report": state.get("ats_report", {}),
        "skills_match_score": state.get("skills_match", {}).get("overall_match_score"),
        "output_tex": str(tex_path),
        "output_pdf": pdf_path,
    }

    report_path = output_dir / f"report_{timestamp}.json"
    report_path.write_text(json.dumps(run_report, indent=2), encoding="utf-8")
    print(f"  [Output] Report saved → {report_path}")

    return {
        "final_pdf_path": pdf_path,
        "run_report": run_report,
    }


# ── Conditional Edge Logic ─────────────────────────────────────────────────────

def should_loop(state: ResumeOptimizerState) -> str:
    """
    Returns 'loop' to send back to resume_rewriter,
    or 'finish' to proceed to output_generator.
    """
    if state.get("final_approved", False):
        return "finish"
    return "loop"


# ── Graph Definition ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(ResumeOptimizerState)

    # Register all nodes
    graph.add_node("jd_reviewer",      jd_reviewer_node)
    graph.add_node("skills_matcher",   skills_matcher_node)
    graph.add_node("resume_rewriter",  resume_rewriter_node)
    graph.add_node("hr_reviewer",      hr_reviewer_node)
    graph.add_node("ats_checker",      ats_checker_node)
    graph.add_node("feedback_agg",     feedback_aggregator_node)
    graph.add_node("output_generator", output_generator_node)

    # Entry → JD Reviewer
    graph.set_entry_point("jd_reviewer")

    # JD Reviewer → Skills Matcher (skills matcher needs jd_analysis)
    graph.add_edge("jd_reviewer", "skills_matcher")

    # Skills Matcher → Resume Rewriter (rewriter needs both jd_analysis + skills_match)
    graph.add_edge("skills_matcher", "resume_rewriter")

    # Resume Rewriter → HR Reviewer AND ATS Checker (parallel fan-out)
    graph.add_edge("resume_rewriter", "hr_reviewer")
    graph.add_edge("resume_rewriter", "ats_checker")

    # Both reviewers → Feedback Aggregator (fan-in join)
    graph.add_edge("hr_reviewer",  "feedback_agg")
    graph.add_edge("ats_checker",  "feedback_agg")

    # Feedback Aggregator → conditional: loop back or finish
    graph.add_conditional_edges(
        "feedback_agg",
        should_loop,
        {
            "loop":   "resume_rewriter",   # send feedback back to rewriter
            "finish": "output_generator",  # done!
        }
    )

    # Output Generator → END
    graph.add_edge("output_generator", END)

    return graph.compile()


# ── Exported compiled graph ───────────────────────────────────────────────────
pipeline = build_graph()
