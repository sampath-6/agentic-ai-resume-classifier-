from pathlib import Path


def _extract_pdf_pypdf(file_path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_pdf_pdfplumber(file_path: str) -> str:
    import pdfplumber

    with pdfplumber.open(file_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _extract_docx(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(file_path: str, attempt: int = 1) -> str:
    """attempt > 1 switches to a slower, more tolerant PDF backend as a fallback."""
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return _extract_pdf_pypdf(file_path) if attempt == 1 else _extract_pdf_pdfplumber(file_path)
    if ext == ".docx":
        return _extract_docx(file_path)
    if ext == ".txt":
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")

    raise ValueError(f"Unsupported file type: {ext}")
