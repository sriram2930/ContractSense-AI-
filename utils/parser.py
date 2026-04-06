import pdfplumber
import docx
import re


def extract_text_from_pdf(file) -> str:
    """Extract raw text from a PDF file object."""
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file) -> str:
    """Extract raw text from a DOCX file object."""
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])


def extract_text(uploaded_file) -> str:
    """Route to correct extractor based on file type."""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(uploaded_file)
    elif name.endswith(".docx"):
        return extract_text_from_docx(uploaded_file)
    elif name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    else:
        raise ValueError(f"Unsupported file type: {name}")


def chunk_into_clauses(text: str) -> list[str]:
    """
    Naive clause chunker — splits on numbered sections, lettered items,
    or double newlines. Works for most standard contracts.
    """
    # Split on patterns like "1.", "2.", "Section 1", "ARTICLE I", or double newlines
    pattern = r'(?=\n(?:\d+\.|Section\s+\d+|ARTICLE\s+[IVXLC]+|[A-Z]{2,}\s*[:\n]))'
    chunks = re.split(pattern, text)
    cleaned = [c.strip() for c in chunks if len(c.strip()) > 80]
    return cleaned