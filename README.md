<div align="center">

# 🎯 ResumeOptimizerAgent

**A LangGraph-powered multi-agent system that automatically optimizes your resume for any job description.**

Give it a job URL or pasted JD text → get back a perfectly tailored, ATS-passing, HR-approved LaTeX resume.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## What it does

Most resume optimizers are single-shot LLM calls. This one is a **full agentic pipeline** — five specialized agents working in series and parallel, with an automatic feedback loop, just like a real hiring process:

```
JD URL / Text
      │
      ▼
 [Agent 1] JD Reviewer ──────────────────────────────────┐
      │                                                   │
      ▼                                                   ▼
 [Agent 2] Skills Analyser & Matcher              (parallel parse)
      │
      ▼
 [Agent 3] Resume Rewriter  ◄──────────────────── (loops back with feedback)
      │
      ├──────────────────────────────┐
      ▼                              ▼
 [Agent 4] HR Reviewer         [Agent 5] ATS Checker     ← run in parallel
      │                              │
      └──────────────┬───────────────┘
                     ▼
           Feedback Aggregator
           ├── PASS → Output (LaTeX + PDF + Report)
           └── FAIL → Loop back to Agent 3 (max N loops)
```

### The 5 Agents

| Agent | Role | Output |
|-------|------|--------|
| **JD Reviewer** | Parses the job description (URL or text) into structured keywords, required skills, ATS phrases, and resume strategy | JSON analysis |
| **Skills Matcher** | Cross-references your `skills.md` experience against the JD. Finds matches, gaps, and reframing opportunities | Match report + gap analysis |
| **Resume Rewriter** | Rewrites your LaTeX resume — tailored summary, injected keywords, reordered sections, stronger bullet points. **Never fabricates** skills you don't have | Optimized `.tex` |
| **HR Reviewer** | Simulates a senior hiring manager at the target company reviewing your resume for narrative quality and fit | Score + structured feedback |
| **ATS Checker** | Simulates a real ATS scan (Taleo, Workday, Greenhouse rules) — keyword match rate, section headers, format compliance | ATS score + fixes |

---

## Quick Start

### 1. Clone & set up environment

```bash
git clone https://github.com/Aarsh813/ResumeOptimizerAgent.git
cd ResumeOptimizerAgent
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Add your resume and skills

Copy your LaTeX resume into `workspace/resume.tex` and fill in `workspace/skills.md` with all your experience, projects, and skills.

Templates are provided — see [`workspace/resume.tex`](workspace/resume.tex) and [`workspace/skills.md`](workspace/skills.md).

### 3. Set up your API key

Copy the example config:
```bash
cp .env.example .env
```

Edit `.env` and choose a provider:

#### Option A — Groq (Recommended: Free, fast, no credit card)
1. Go to **[console.groq.com](https://console.groq.com)** → sign up free
2. Create an API key (starts with `gsk_...`)
3. Add to `.env`:
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

#### Option B — Google Gemini (1500 req/day free)
```env
LLM_PROVIDER=google
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```
Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

#### Option C — Ollama (Fully local, no limits, no API key)
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```
Install Ollama from [ollama.com](https://ollama.com), then run `ollama pull llama3.2`.

### 4. Run

```bash
# With a job URL
python main.py --jd "https://jobs.example.com/software-engineer-12345"

# With pasted JD text
python main.py --jd "We are looking for a Senior Software Engineer..."

# Control the feedback loop depth (default: 2)
python main.py --jd "..." --max-loops 3
```

---

## Example Output

```
============================================================
  Resume Optimizer  --  LangGraph Multi-Agent Pipeline
============================================================

[*] Loading workspace files...
   resume.tex: 3286 chars
   skills.md:  2938 chars
[URL] JD source: https://xyz.wd501.myworkdayjobs.com/...
[~] Max feedback loops: 1

[>] Starting pipeline...

  [Agent 1] Fetching JD from URL...
  [Agent 1] Done -- role: Software Engineer I, company: XYZ Technologies
  [Agent 2] Matching skills (2938 chars) against JD for 'Software Engineer I'...
  [Agent 2] Done -- 11 matches, 2 gaps, score: 78/100
  [Agent 3] Rewriting resume for 'Software Engineer I' (rewrite #1, feedback loop #0)...
  [Agent 3] Done -- output is 4865 chars of LaTeX
  [Agent 4] HR review for 'Software Engineer I' at 'XYZ Technologies' (loop 0)...
  [Agent 5] Running ATS check (loop 0)...
  [Agent 4] Done -- HR score: 8.4/10, pass: True
  [Agent 5] Done -- ATS score: 82/100, pass: True, 1 keyword miss

  [Feedback] Loop 1 results:
    HR:  ✓ PASS (score: 8.4/10)
    ATS: ✓ PASS (score: 82/100)
  [Feedback] Both reviewers PASSED — proceeding to output generation.

  [Output] LaTeX saved → output/Software_Engineer_I_20250629_212300.tex
  [Output] Report saved → output/report_20250629_212300.json

============================================================
  Pipeline Complete
============================================================
  Role:            Software Engineer I
  Company:         XYZ Technologies
  Rewrite loops:   1
  Skills match:    78/100
  HR score:        8.4/10  (PASS)
  ATS score:       82/100  (PASS)
  Output LaTeX:    output/Software_Engineer_I_20250629_212300.tex
============================================================
```

---

## Project Structure

```
ResumeOptimizerAgent/
├── main.py                    # CLI entry point
├── graph.py                   # LangGraph StateGraph (the pipeline)
├── state.py                   # Shared TypedDict state schema
├── llm_factory.py             # Multi-provider LLM setup + retry logic
│
├── agents/
│   ├── jd_reviewer.py         # Agent 1 — JD analysis
│   ├── skills_matcher.py      # Agent 2 — skills match & gap analysis
│   ├── resume_rewriter.py     # Agent 3 — LaTeX rewriter
│   ├── hr_reviewer.py         # Agent 4 — HR persona reviewer
│   └── ats_checker.py         # Agent 5 — ATS simulation
│
├── tools/
│   ├── jd_scraper.py          # URL → clean JD text (JSON-LD + HTML parsing)
│   ├── latex_compiler.py      # LaTeX → PDF (tectonic / pdflatex)
│   └── pdf_parser.py          # PDF → plain text (for ATS agent)
│
├── prompts/
│   ├── jd_reviewer.md         # System prompt for Agent 1
│   ├── skills_matcher.md      # System prompt for Agent 2
│   ├── resume_rewriter.md     # System prompt for Agent 3
│   ├── hr_reviewer.md         # System prompt for Agent 4
│   └── ats_checker.md         # System prompt for Agent 5
│
├── workspace/                 # YOUR FILES GO HERE (gitignored)
│   ├── resume.tex             # Your LaTeX resume source
│   └── skills.md              # Your experience, projects, skills
│
├── output/                    # Generated files (gitignored)
│   ├── *.tex                  # Optimized LaTeX per run
│   ├── *.pdf                  # Compiled PDF (if LaTeX compiler found)
│   └── report_*.json          # Full pipeline audit log
│
├── .env.example               # Config template
├── requirements.txt
└── README.md
```

---

## Configuration Reference

All configuration lives in `.env`. Copy `.env.example` to get started.

```env
# Provider: groq | google | ollama | xai
LLM_PROVIDER=groq

# Groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile   # or: llama-3.1-8b-instant, gemma2-9b-it

# Google Gemini
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash         # or: gemini-2.5-flash (only 20 req/day free)

# Ollama (local)
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434

# Retry on rate limits (auto-backoff)
LLM_MAX_RETRIES=4
LLM_RETRY_DELAY=35
```

---

## Supported Job Portals

The JD scraper uses **JSON-LD structured data extraction** (not raw HTML scraping), which works reliably on most ATS job portals even when they are JavaScript-rendered:

| Portal | Works? |
|--------|--------|
| Workday (Zebra, etc.) | ✅ |
| Greenhouse | ✅ |
| Lever | ✅ |
| LinkedIn | ⚠️ Partial (JS-heavy) |
| Cisco Careers | ⚠️ Partial |
| Any static job page | ✅ |
| **Plain text / paste** | ✅ Always works |

> **Tip:** If a URL doesn't work, just paste the JD text directly:
> ```bash
> python main.py --jd "$(cat jd.txt)"
> ```

---

## PDF Compilation (Optional)

The pipeline always outputs a `.tex` file. To also get a compiled `.pdf`, install one of:

- **Tectonic** (recommended, self-contained): [tectonic-typesetting.github.io](https://tectonic-typesetting.github.io)
- **MiKTeX / TeX Live** (includes `pdflatex`): [miktex.org](https://miktex.org)

The compiler is auto-detected — no config needed.

---

## How the Feedback Loop Works

```
Resume Rewriter
      │
      ├──► HR Reviewer  ──┐
      │                   ├──► Feedback Aggregator
      └──► ATS Checker ───┘          │
                               ┌─────┴──────┐
                               ▼            ▼
                         HR ✓ & ATS ✓   HR ✗ or ATS ✗
                         → Output       → Rewrite again
                                          (up to --max-loops)
```

- HR and ATS agents run **in parallel** after every rewrite
- If either fails, their full feedback JSON is sent back to the Rewriter as additional context
- The Rewriter addresses every specific `weakness` and `keyword_miss` in the next iteration
- After `--max-loops` iterations (default: 2), the best version is output regardless

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">
Built with <a href="https://langchain-ai.github.io/langgraph/">LangGraph</a> · Powered by <a href="https://console.groq.com">Groq</a> / <a href="https://aistudio.google.com">Gemini</a> / <a href="https://ollama.com">Ollama</a>
</div>
