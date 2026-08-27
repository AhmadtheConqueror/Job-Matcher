import re
from pathlib import Path

from docx import Document
from PyPDF2 import PdfReader


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_text_from_file(file_path):
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        text = _extract_pdf_text(path)
    elif extension == ".docx":
        text = _extract_docx_text(path)
    elif extension == ".txt":
        text = path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported CV file type.")

    text = clean_text(text)
    if not text:
        raise ValueError("No readable text found in this CV.")
    return text


def _extract_pdf_text(path):
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(path):
    document = Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)

