"""
LaTeX Compiler Tool
Compiles a .tex string to PDF using pdflatex (or tectonic if available).
Returns the path to the compiled PDF on success, or an error string.
"""

import os
import shutil
import subprocess
import tempfile


def compile_latex(latex_source: str, output_dir: str, output_name: str = "resume_optimized") -> str:
    """
    Write latex_source to a temp .tex file, compile it, and copy the PDF
    to output_dir/<output_name>.pdf.

    Returns:
        Absolute path to the PDF on success.
        Error message string on failure.
    """
    # Detect available LaTeX engine
    engine = None
    for candidate in ["tectonic", "pdflatex", "xelatex"]:
        if shutil.which(candidate):
            engine = candidate
            break

    if engine is None:
        return (
            "ERROR: No LaTeX compiler found. Install tectonic (recommended) or pdflatex.\n"
            "  → tectonic: https://tectonic-typesetting.github.io/\n"
            "  → MiKTeX/TeX Live for pdflatex."
        )

    os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, f"{output_name}.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_source)

        if engine == "tectonic":
            cmd = ["tectonic", tex_path]
        else:
            # pdflatex / xelatex — run twice for cross-references
            cmd = [engine, "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, cwd=tmpdir
            )
            if engine != "tectonic" and result.returncode != 0:
                # Try second run (some packages need two passes)
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=60, cwd=tmpdir
                )

            pdf_path = os.path.join(tmpdir, f"{output_name}.pdf")
            if not os.path.exists(pdf_path):
                return f"Compilation failed:\n{result.stderr[-2000:]}"

            dest = os.path.join(output_dir, f"{output_name}.pdf")
            shutil.copy2(pdf_path, dest)
            return os.path.abspath(dest)

        except subprocess.TimeoutExpired:
            return "Compilation timed out after 60 seconds."
        except Exception as e:
            return f"Unexpected compilation error: {e}"
