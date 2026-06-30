"""
LLM Factory
Centralised LLM creation with automatic retry/backoff on rate-limit errors.
Supports multiple providers — swap via .env without touching agent code.

Provider options (set LLM_PROVIDER in .env):
  google  →  Google Gemini  (GOOGLE_API_KEY required)
  groq    →  Groq Cloud      (GROQ_API_KEY required)  ← recommended free option
  ollama  →  Local Ollama    (no key needed, Ollama must be running)

Free-tier limits (as of 2025):
  Groq  llama-3.3-70b-versatile  →  14,400 req/day, 30 req/min  (best free option)
  Groq  gemma2-9b-it             →  14,400 req/day, 30 req/min
  Gemini gemini-2.0-flash        →  1,500 req/day
  Gemini gemini-2.5-flash        →  20 req/day  (too low for this pipeline)
"""

import os
import re
import time
from langchain_core.language_models.chat_models import BaseChatModel

# ── Configuration (all from .env) ─────────────────────────────────────────────
LLM_PROVIDER    = os.getenv("LLM_PROVIDER",        "groq").lower()
GROQ_MODEL      = os.getenv("GROQ_MODEL",           "llama-3.3-70b-versatile")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL",         "gemini-2.0-flash")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",         "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL",      "http://localhost:11434")
MAX_RETRIES     = int(os.getenv("LLM_MAX_RETRIES",  "4"))
BASE_DELAY      = float(os.getenv("LLM_RETRY_DELAY","35"))


def _make_llm(temperature: float = 0.1) -> BaseChatModel:
    """Instantiate an LLM based on LLM_PROVIDER env var."""

    if LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY not set. Get a free key at https://console.groq.com"
            )
        return ChatGroq(
            model=GROQ_MODEL,
            temperature=temperature,
            groq_api_key=api_key,
        )

    elif LLM_PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=temperature,
        )

    elif LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=temperature,
        )

    elif LLM_PROVIDER == "xai":
        # xAI (Grok) — uses an OpenAI-compatible API
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "XAI_API_KEY not set. Get a key at https://console.x.ai"
            )
        xai_model = os.getenv("XAI_MODEL", "grok-3-mini")
        return ChatOpenAI(
            model=xai_model,
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            temperature=temperature,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. "
            "Choose: groq | google | ollama"
        )


def invoke_with_retry(llm: BaseChatModel, messages: list, agent_name: str = "Agent"):
    """
    Invoke an LLM with exponential backoff on rate-limit (429) errors.
    Other errors are re-raised immediately.
    """
    delay = BASE_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return llm.invoke(messages)
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "rate_limit" in err_str.lower()
            is_exhausted  = "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()

            if (is_rate_limit or is_exhausted) and attempt < MAX_RETRIES:
                m = re.search(r"retry.*?(\d+)", err_str, re.IGNORECASE)
                suggested = int(m.group(1)) + 5 if m else delay
                wait = max(suggested, delay)
                print(f"\n  [{agent_name}] Rate limit hit. "
                      f"Waiting {wait:.0f}s then retrying ({attempt}/{MAX_RETRIES - 1})...")
                time.sleep(wait)
                delay = min(delay * 2, 120)
            else:
                raise


# ── LLM cache: one instance per (provider, temperature) ───────────────────────
_llm_cache: dict[float, BaseChatModel] = {}

def get_llm(temperature: float = 0.1) -> BaseChatModel:
    """Return a cached LLM instance for the given temperature."""
    if temperature not in _llm_cache:
        _llm_cache[temperature] = _make_llm(temperature)
    return _llm_cache[temperature]
