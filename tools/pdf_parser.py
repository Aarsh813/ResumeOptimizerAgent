"""
PDF Text Extractor
Extracts plain text from a PDF file for ATS simulation.
Uses pdfminer.six as primary, falls back to pymupdf (fitz) if available.
"""

import os


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract readable plain text from a PDF file.

    Returns:
        Extracted text string.
        Error message string if extraction fails.
    """
    if not os.path.exists(pdf_path):
        return f"ERROR: PDF not found at {pdf_path}"

    # Try pdfminer.six first (best for ATS-style extraction)
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(pdf_path)
        if text and text.strip():
            return text.strip()
    except ImportError:
        pass
    except Exception as e:
        pass  # fall through to next method

    # Try pymupdf (fitz) as fallback
    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        pages = [page.get_text() for page in doc]
        doc.close()
        text = "\n".join(pages).strip()
        if text:
            return text
    except ImportError:
        pass
    except Exception as e:
        return f"ERROR extracting PDF text: {e}"

    return "ERROR: Could not extract text from PDF. Install pdfminer.six: pip install pdfminer.six"
