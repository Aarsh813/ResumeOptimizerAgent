"""
Resume Optimizer — CLI Entry Point

Usage:
    python main.py --jd "https://careers.cisco.com/..." [--max-loops 2]
    python main.py --jd "We are looking for a Senior SWE..." [--max-loops 2]
    python main.py --jd path/to/jd.txt [--max-loops 2]

Workspace files expected:
    workspace/resume.tex    — Your LaTeX resume source
    workspace/skills.md     — Your skills, experience, projects in Markdown
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

# Validate API key early
if not os.getenv("GOOGLE_API_KEY"):
    print("ERROR: GOOGLE_API_KEY not found in environment. Set it in your .env file.")
    sys.exit(1)


def load_workspace_files() -> tuple[str, str]:
    """Load resume.tex and skills.md from the workspace/ directory."""
    workspace = Path("workspace")

    resume_path = workspace / "resume.tex"
    skills_path = workspace / "skills.md"

    if not resume_path.exists():
        print(f"ERROR: Resume not found at {resume_path}")
        print("       Create workspace/resume.tex with your LaTeX resume source.")
        sys.exit(1)

    if not skills_path.exists():
        print(f"ERROR: Skills file not found at {skills_path}")
        print("       Create workspace/skills.md with your experience, skills, and projects.")
        sys.exit(1)

    return resume_path.read_text(encoding="utf-8"), skills_path.read_text(encoding="utf-8")


def resolve_jd(jd_arg: str) -> str:
    """
    Resolve the --jd argument to a string:
    - If it looks like a URL → return as-is (scraper will handle it)
    - If it's a file path that exists → read and return contents
    - Otherwise → treat as plain text
    """
    if jd_arg.startswith(("http://", "https://")):
        return jd_arg  # URL
    path = Path(jd_arg)
    if path.exists() and path.suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    return jd_arg  # plain text


def print_banner():
    print("\n" + "=" * 60)
    print("  Resume Optimizer  --  LangGraph Multi-Agent Pipeline")
    print("=" * 60 + "\n")


def print_summary(run_report: dict):
    print("\n" + "=" * 60)
    print("  Pipeline Complete")
    print("=" * 60)
    print(f"  Role:            {run_report.get('role', '?')}")
    print(f"  Company:         {run_report.get('company', '?')}")
    print(f"  Rewrite loops:   {run_report.get('total_loops', 0)}")
    print(f"  Skills match:    {run_report.get('skills_match_score', '?')}/100")

    hr = run_report.get("hr_feedback", {})
    ats = run_report.get("ats_report", {})
    print(f"  HR score:        {hr.get('score', '?')}/10  "
          f"({'PASS' if hr.get('pass') else 'FAIL'})")
    print(f"  ATS score:       {ats.get('score', '?')}/100  "
          f"({'PASS' if ats.get('pass') else 'FAIL'})")
    print(f"\n  Output LaTeX:    {run_report.get('output_tex', 'N/A')}")
    if run_report.get("output_pdf"):
        print(f"  Output PDF:      {run_report.get('output_pdf')}")
    else:
        print("  Output PDF:      (LaTeX compiler not available — .tex file saved)")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Resume Optimizer — LangGraph multi-agent pipeline"
    )
    parser.add_argument(
        "--jd",
        required=True,
        help="Job description: URL, file path to .txt/.md, or plain text string",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=2,
        help="Maximum HR+ATS feedback loops (default: 2)",
    )
    args = parser.parse_args()

    print_banner()

    # Load workspace files
    print("[*] Loading workspace files...")
    resume_latex, skills_md = load_workspace_files()
    print(f"   resume.tex: {len(resume_latex)} chars")
    print(f"   skills.md:  {len(skills_md)} chars")

    # Resolve JD
    jd_raw = resolve_jd(args.jd)
    if jd_raw.startswith("http"):
        print(f"[URL] JD source: {jd_raw[:70]}...")
    else:
        print(f"[TEXT] JD source: plain text ({len(jd_raw)} chars)")

    print(f"[~] Max feedback loops: {args.max_loops}\n")

    # Build initial state
    initial_state: dict = {
        "jd_raw": jd_raw,
        "jd_text": "",
        "resume_latex": resume_latex,
        "skills_md": skills_md,
        "jd_analysis": {},
        "skills_match": {},
        "optimized_latex": "",
        "rewrite_iteration": 0,
        "hr_feedback": {},
        "ats_report": {},
        "loop_count": 0,
        "max_loops": args.max_loops,
        "final_approved": False,
        "final_pdf_path": None,
        "run_report": {},
    }

    # Import and run the pipeline
    from graph import pipeline

    print("[>] Starting pipeline...\n")
    print("-" * 60)

    try:
        final_state = pipeline.invoke(initial_state)
        print_summary(final_state["run_report"])
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Pipeline error: {e}")
        raise


if __name__ == "__main__":
    main()