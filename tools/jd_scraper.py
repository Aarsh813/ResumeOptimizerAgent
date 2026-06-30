"""
JD Scraper Tool
Extracts clean job description text from a URL or returns raw text as-is.

Strategy (in order of preference):
1. JSON-LD structured data (<script type="application/ld+json">) — reliable
   even on JS-heavy portals like Workday, Greenhouse, Lever, Cisco
2. OpenGraph / meta description as supplementary context
3. HTML content extraction with noise removal

For fully JS-rendered pages where none of the above yield content,
the tool returns a clear warning so the JD Reviewer can flag it.
"""

import json
import re
import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_NOISE_TAGS = [
    "nav", "header", "footer", "aside", "script", "style",
    "noscript", "iframe", "form", "button", "svg", "img",
]

_JD_SECTION_KEYWORDS = [
    "description", "responsibilities", "requirements", "qualifications",
    "about the role", "about this job", "what you", "minimum qualifications",
    "preferred qualifications", "skills", "job-description", "posting", "content",
    "job_description", "jobDescription", "details",
]

# Minimum characters to consider a scrape successful
_MIN_CONTENT_LENGTH = 200


def _clean_text(text: str) -> str:
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if len(line.strip()) > 10]
    return "\n".join(cleaned)


def _extract_json_ld(soup: BeautifulSoup) -> str:
    """
    Extract job posting data from JSON-LD structured data.
    Many ATS portals (Workday, Greenhouse, Lever) embed full JD in JSON-LD
    even when the page body is JS-rendered.
    """
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Handle single object or list
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                job_type = item.get("@type", "")
                if "JobPosting" in str(job_type):
                    parts = []
                    if item.get("title"):
                        parts.append(f"Job Title: {item['title']}")
                    if item.get("hiringOrganization", {}).get("name"):
                        parts.append(f"Company: {item['hiringOrganization']['name']}")
                    if item.get("jobLocation"):
                        loc = item["jobLocation"]
                        if isinstance(loc, dict):
                            addr = loc.get("address", {})
                            city = addr.get("addressLocality", "")
                            country = addr.get("addressCountry", "")
                            parts.append(f"Location: {city}, {country}")
                    if item.get("description"):
                        # Strip HTML tags from description
                        desc_soup = BeautifulSoup(item["description"], "html.parser")
                        parts.append(f"\nJob Description:\n{desc_soup.get_text(separator=chr(10))}")
                    if item.get("qualifications"):
                        parts.append(f"\nQualifications:\n{item['qualifications']}")
                    if item.get("responsibilities"):
                        parts.append(f"\nResponsibilities:\n{item['responsibilities']}")
                    if parts:
                        results.append("\n".join(parts))
        except (json.JSONDecodeError, AttributeError):
            continue
    return "\n\n".join(results)


def _extract_meta_info(soup: BeautifulSoup) -> str:
    """Extract OG tags and meta description as fallback context."""
    parts = []
    title = soup.find("title")
    if title:
        parts.append(f"Page Title: {title.get_text().strip()}")

    for prop in ["og:title", "og:description", "description"]:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            parts.append(tag["content"].strip())
    return "\n".join(parts)


def _extract_html_content(soup: BeautifulSoup) -> str:
    """Remove noise tags and find the most JD-relevant section."""
    for tag in _NOISE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    candidates = []
    for el in soup.find_all(["div", "section", "article", "main"]):
        attrs = " ".join([
            el.get("id", ""),
            " ".join(el.get("class", [])),
        ]).lower()
        if any(kw in attrs for kw in _JD_SECTION_KEYWORDS):
            candidates.append(el)

    if candidates:
        best = max(candidates, key=lambda el: len(el.get_text()))
        return _clean_text(best.get_text(separator="\n"))

    body = soup.find("body")
    if body:
        return _clean_text(body.get_text(separator="\n"))
    return ""


@tool
def get_jd_from_url(url: str) -> str:
    """
    Fetch a job description page from a URL and return the cleaned text.
    Tries JSON-LD structured data first (works on Workday, Greenhouse, Lever,
    Cisco, Zebra, etc.), then falls back to HTML parsing.
    Returns a warning string if the page is fully JS-rendered with no parseable content.
    """
    try:
        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=15) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code} fetching URL: {url}"
    except httpx.RequestError as e:
        return f"Network error fetching URL: {e}"
    except Exception as e:
        return f"Unexpected fetch error: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    sections = []

    # Strategy 1: JSON-LD (best for ATS portals)
    json_ld_text = _extract_json_ld(soup)
    if json_ld_text.strip():
        sections.append(json_ld_text.strip())

    # Strategy 2: Meta tags (always collect as supplementary context)
    meta_text = _extract_meta_info(soup)
    if meta_text.strip():
        sections.append(meta_text.strip())

    # Strategy 3: HTML content (only if JSON-LD was insufficient)
    if len(json_ld_text) < _MIN_CONTENT_LENGTH:
        html_text = _extract_html_content(soup)
        if html_text.strip():
            sections.append(html_text.strip())

    combined = "\n\n---\n\n".join(sections)

    if len(combined.strip()) < _MIN_CONTENT_LENGTH:
        return (
            f"WARNING: Could not extract meaningful JD content from {url}\n"
            "This page is likely fully JavaScript-rendered (common with Workday, iCIMS).\n"
            "TIP: Copy and paste the job description text directly using --jd \"<paste text here>\""
        )

    # Truncate to ~8000 chars to stay within model context
    if len(combined) > 8000:
        combined = combined[:8000] + "\n... [truncated]"

    return combined