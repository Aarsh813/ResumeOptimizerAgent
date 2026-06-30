# LangGraph Resume Optimizer — Agentic AI System Plan

A multi-agent AI pipeline that takes a **job description (URL or plain text)** and a **resume (LaTeX source)** + **personal skills/experience (Markdown)**, and produces a fully optimized, ATS-passing, HR-approved resume PDF — with iterative feedback loops.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ENTRY POINT (CLI)                            │
│   python main.py --jd "url or text" [--max-loops 2]                │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (LangGraph)                         │
│                    StateGraph / CompiledGraph                        │
└──┬─────────────────────────────────────────────────────────────┬───┘
   │                                                             │
   ▼  (parallel fork)                                           ▼
┌──────────────────┐                              ┌──────────────────────┐
│  Agent 1         │                              │  Agent 2             │
│  JD Reviewer     │                              │  Skills Analyser     │
│                  │                              │  & Matcher           │
│  Input: JD text  │                              │  Input: skills.md    │
│  Output:         │                              │  + JD keywords       │
│  - Keywords      │                              │  Output:             │
│  - Skills needed │                              │  - Matched skills    │
│  - Tone/Role     │                              │  - Gap analysis      │
│  - ATS flags     │                              │  - Highlight recs    │
└────────┬─────────┘                              └──────────┬───────────┘
         │                                                   │
         └──────────────────┬────────────────────────────────┘
                            │  (join / merge)
                            ▼
              ┌─────────────────────────┐
              │  Agent 3                │
              │  Resume Rewriter        │
              │                         │
              │  Input: LaTeX resume    │
              │  + JD analysis          │
              │  + skills match         │
              │  Output: New LaTeX      │
              └────────────┬────────────┘
                           │
              ┌────────────┴────────────┐
              │  (parallel fork again)  │
              ▼                         ▼
┌─────────────────────┐    ┌────────────────────────┐
│  Agent 4            │    │  Agent 5               │
│  HR Reviewer        │    │  ATS Checker           │
│                     │    │                        │
│  Role: Simulate     │    │  Rules: Real ATS       │
│  hiring manager of  │    │  scoring (keyword      │
│  target company     │    │  density, format,      │
│                     │    │  section headers,      │
│  Output:            │    │  file parse-ability)   │
│  - HR feedback      │    │                        │
│  - Pass/Fail        │    │  Output:               │
│                     │    │  - ATS score           │
│                     │    │  - Specific failures   │
└────────┬────────────┘    └──────────┬─────────────┘
         │                            │
         └───────────┬────────────────┘
                     │  (merge feedback)
                     ▼
         ┌───────────────────────┐
         │  Feedback Aggregator  │
         │  (conditional edge)   │
         │                       │
         │  PASS? → Final Output │
         │  FAIL? → Loop back    │
         │          to Agent 3   │
         │  (max N loops)        │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   OUTPUT GENERATOR    │
         │   LaTeX → PDF         │
         │   + JSON report       │
         └───────────────────────┘
```

---

## Project Structure

```
ResumeReviewer/
├── main.py                          # CLI entry point
├── graph.py                         # LangGraph StateGraph definition
├── state.py                         # Shared TypedDict state schema
│
├── agents/
│   ├── __init__.py
│   ├── jd_reviewer.py               # Agent 1 — JD Analyzer
│   ├── skills_matcher.py            # Agent 2 — Skills Analyser & Matcher
│   ├── resume_rewriter.py           # Agent 3 — Resume Rewriter
│   ├── hr_reviewer.py               # Agent 4 — HR Reviewer
│   └── ats_checker.py               # Agent 5 — ATS Checker
│
├── tools/
│   ├── __init__.py
│   ├── jd_scraper.py                # Scrape JD from URL (BeautifulSoup/Playwright)
│   ├── latex_compiler.py            # Compile LaTeX → PDF (pdflatex / tectonic)
│   └── pdf_parser.py                # Extract text from PDF for ATS check
│
├── prompts/
│   ├── jd_reviewer.md               # Prompt template for Agent 1
│   ├── skills_matcher.md            # Prompt template for Agent 2
│   ├── resume_rewriter.md           # Prompt template for Agent 3
│   ├── hr_reviewer.md               # Prompt template for Agent 4
│   └── ats_checker.md               # Prompt template for Agent 5
│
├── workspace/
│   ├── resume.tex                   # Your LaTeX resume source
│   └── skills.md                    # Your skills/experience/projects markdown
│
├── output/
│   ├── resume_optimized.tex         # Final rewritten LaTeX
│   ├── resume_optimized.pdf         # Compiled PDF
│   └── report.json                  # Full pipeline run report
│
├── requirements.txt
└── .env                             # API keys (OPENAI_API_KEY, etc.)
```

---

## State Schema (`state.py`)

```python
from typing import TypedDict, Optional, List

class ResumeOptimizerState(TypedDict):
    # Inputs
    jd_raw: str                    # Raw JD (text or URL)
    jd_text: str                   # Scraped/cleaned JD text
    resume_latex: str              # Original LaTeX source
    skills_md: str                 # skills.md content

    # Agent 1 Output
    jd_analysis: dict              # keywords, skills, tone, role, company name

    # Agent 2 Output
    skills_match: dict             # matched_skills, gaps, highlight_recs

    # Agent 3 Output (evolves per loop)
    optimized_latex: str           # Current best LaTeX
    rewrite_iteration: int         # Loop counter

    # Agent 4 Output
    hr_feedback: dict              # score, pass/fail, comments

    # Agent 5 Output
    ats_report: dict               # score, failures, suggestions

    # Control
    loop_count: int
    max_loops: int
    final_approved: bool
    final_pdf_path: Optional[str]
    run_report: dict
```

---

## Agent Specifications

### Agent 1 — JD Reviewer

| Property | Detail |
|----------|--------|
| **Input** | Raw JD text (or URL → scraper extracts text) |
| **Model** | GPT-4o / Claude Sonnet |
| **Task** | Parse JD into structured keywords, required skills, nice-to-haves, company tone, seniority level, ATS-critical phrases |
| **Output format** | JSON: `{ "role": "", "company": "", "required_skills": [], "preferred_skills": [], "keywords": [], "tone": "", "ats_phrases": [], "red_flags": [] }` |
| **Parallelism** | Runs in parallel with Agent 2 |

### Agent 2 — Skills Analyser & Matcher

| Property | Detail |
|----------|--------|
| **Input** | `skills.md` + JD analysis from Agent 1 |
| **Model** | GPT-4o / Claude Sonnet |
| **Task** | Extract all experiences, projects, technologies from `skills.md`. Cross-reference against JD requirements. Identify exact matches, partial matches, and gaps. Suggest which resume sections to emphasize. |
| **Output format** | JSON: `{ "matched": [], "partial": [], "gaps": [], "emphasis_recs": [], "transferable": [] }` |
| **Note** | Agent 2 waits for Agent 1's output (keywords) but can pre-parse `skills.md` in parallel |

### Agent 3 — Resume Rewriter

| Property | Detail |
|----------|--------|
| **Input** | Original LaTeX + JD analysis + skills match + (on loop: HR/ATS feedback) |
| **Model** | GPT-4o / Claude Sonnet (long context) |
| **Task** | Rewrite the LaTeX resume — reorder sections, reword bullet points with action verbs + quantified impact, inject ATS keywords naturally, tailor summary/objective to role |
| **Constraints** | Must preserve LaTeX structure validity; do not hallucinate skills not in `skills.md` |
| **Output** | Modified `.tex` string |

### Agent 4 — HR Reviewer

| Property | Detail |
|----------|--------|
| **Input** | Compiled PDF text + JD analysis |
| **Model** | GPT-4o |
| **Persona** | Senior HR at `{company}` hiring for `{role}` |
| **Task** | Review resume as a human HR would: narrative flow, impact clarity, relevance, red flags, cultural fit signals |
| **Output format** | JSON: `{ "score": 0-10, "pass": bool, "strengths": [], "weaknesses": [], "suggestions": [] }` |
| **Parallelism** | Runs in parallel with Agent 5 |

### Agent 5 — ATS Checker

| Property | Detail |
|----------|--------|
| **Input** | Parsed PDF text + JD analysis |
| **Model** | GPT-4o |
| **Rules** | Simulates real ATS: keyword match rate, section header recognition (Education, Experience, Skills), date formatting, no tables/columns/graphics in text layer, font-safe characters, file parsability |
| **Output format** | JSON: `{ "score": 0-100, "pass": bool (threshold: 75), "keyword_hits": [], "keyword_misses": [], "format_issues": [], "recommendations": [] }` |
| **Parallelism** | Runs in parallel with Agent 4 |

---

## LangGraph Graph Definition (`graph.py`)

```python
from langgraph.graph import StateGraph, END
from langgraph.pregel import GraphRecursionError

graph = StateGraph(ResumeOptimizerState)

# Node registration
graph.add_node("scrape_jd",        scrape_jd_node)          # Tool node
graph.add_node("jd_reviewer",      jd_reviewer_node)         # Agent 1
graph.add_node("skills_matcher",   skills_matcher_node)      # Agent 2
graph.add_node("resume_rewriter",  resume_rewriter_node)     # Agent 3
graph.add_node("hr_reviewer",      hr_reviewer_node)         # Agent 4
graph.add_node("ats_checker",      ats_checker_node)         # Agent 5
graph.add_node("feedback_agg",     feedback_aggregator_node) # Merge + decide
graph.add_node("output_generator", output_generator_node)    # Compile PDF

# Edges
graph.set_entry_point("scrape_jd")
graph.add_edge("scrape_jd", "jd_reviewer")

# Parallel fork: Agent 1 → (Agent 2 in parallel with itself already running)
# LangGraph parallel: use Send() API for fan-out
graph.add_edge("jd_reviewer", "skills_matcher")
graph.add_edge("skills_matcher", "resume_rewriter")  # join happens here

# Parallel fork after rewrite
graph.add_edge("resume_rewriter", "hr_reviewer")
graph.add_edge("resume_rewriter", "ats_checker")

# Join + conditional loop
graph.add_edge("hr_reviewer",  "feedback_agg")
graph.add_edge("ats_checker",  "feedback_agg")

graph.add_conditional_edges(
    "feedback_agg",
    should_loop,           # returns "resume_rewriter" or "output_generator"
    {
        "loop":   "resume_rewriter",
        "finish": "output_generator"
    }
)
graph.add_edge("output_generator", END)
```

### Conditional Loop Logic

```python
def should_loop(state: ResumeOptimizerState) -> str:
    hr_pass  = state["hr_feedback"]["pass"]
    ats_pass = state["ats_report"]["pass"]
    at_limit = state["loop_count"] >= state["max_loops"]

    if (hr_pass and ats_pass) or at_limit:
        return "finish"
    return "loop"
```

---

## Parallel Execution Strategy

LangGraph supports two parallelism patterns:

| Pattern | Used Where |
|---------|-----------|
| **Static fan-out** (multiple `add_edge` from one node) | Agent 4 + Agent 5 running simultaneously after Agent 3 |
| **`Send()` API** (dynamic fan-out) | Can be used if multiple JD sections need sub-analysis |

For Agent 1 + Agent 2 pre-parse (skills.md parsing), we can use a `parallel_init` node that uses `Send()` to fan out both tasks simultaneously and collect via a reducer.

---

## Tooling

| Tool | Library | Purpose |
|------|---------|---------|
| JD URL Scraper | `httpx` + `BeautifulSoup4` / `playwright` | Extract clean JD text from LinkedIn, Greenhouse, Lever, etc. |
| LaTeX Compiler | `tectonic` (self-contained) or `pdflatex` via subprocess | Compile `.tex` → `.pdf` |
| PDF Text Extractor | `pdfminer.six` or `pymupdf` | Extract plain text for ATS simulation |
| LLM | `langchain-openai` / `langchain-anthropic` | Model calls for all agents |
| LangGraph | `langgraph` | Graph orchestration, state, loops |

---

## Open Questions

> [!IMPORTANT]
> **LLM Provider**: Which model backend do you want to use — OpenAI (GPT-4o), Anthropic (Claude), or local (Ollama)? This affects prompt formatting and API key setup.

> [!IMPORTANT]
> **LaTeX Compiler**: Do you have `tectonic` or `pdflatex` installed locally? If not, we can skip PDF compilation and output `.tex` only (or use an online API like latexonline.cc).

> [!NOTE]
> **ATS Checker depth**: Should Agent 5 use purely LLM-based rule simulation, or also integrate a library like `resume-parser` / `pyresparser` for structural checks?

> [!NOTE]
> **Feedback loop limit**: Default max loops = 2. Is that acceptable, or do you want a configurable quality threshold instead of a hard loop cap?

> [!NOTE]
> **skills.md format**: Do you have a preferred format for `skills.md`? (e.g., sections by project, by technology, by timeline?) Or should I define a template?

---

## Proposed Tech Stack

```
langgraph>=0.2
langchain-openai>=0.1       # or langchain-anthropic
langchain-core>=0.2
httpx                        # HTTP for JD scraping
beautifulsoup4               # HTML parsing
pdfminer.six                 # PDF text extraction
tectonic / pdflatex          # LaTeX → PDF (external binary)
python-dotenv                # .env management
rich                         # CLI output formatting
```

---

## Verification Plan

### Automated
- Unit tests per agent node with mock LLM responses
- Integration test with a sample JD + sample resume

### Manual
- Run `python main.py --jd "https://example.com/job"` and verify:
  - Agent 1 produces structured JSON
  - Agent 2 identifies correct matches
  - Agent 3 output is valid LaTeX that compiles
  - Agent 4 + 5 run in parallel (check timing logs)
  - Loop triggers when score is below threshold
  - Final PDF is readable and ATS-pass

---

## Implementation Phases

| Phase | Scope |
|-------|-------|
| **Phase 1** | Project scaffold, state schema, graph skeleton, CLI |
| **Phase 2** | Agent 1 + 2 (JD analysis, skills matching) + JD scraper tool |
| **Phase 3** | Agent 3 (resume rewriter) with LaTeX handling |
| **Phase 4** | Agent 4 + 5 (HR + ATS) with parallel execution |
| **Phase 5** | Feedback loop, conditional edges, output generator |
| **Phase 6** | Prompt engineering, testing, polish |
