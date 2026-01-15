import fitz
from typing import NamedTuple, Literal

class PDFExtractionResult(NamedTuple):
    """
    CONTRATO DE SAÍDA RETORNADO PELO pdf_reader
    """
    text: str

    page_count: int

    has_unicode_issuer: bool

    encoding: Literal["utf-8", "latin-1", "unknown"]

    extration_method: Literal["embedded", "ocr", "mixed"]

    size_bytes: int

    file_size_kb: float


def pdf_path_to_text(path: str) -> PDFExtractionResult:
    """
    Lê um PDF do disco e retorna o texto concatenado e metadados.
    """
    doc = fitz.open(path)

    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())

    raw_text = "\n".join(text_parts)

    has_issues = any(
        char in raw_text
        for char in ['\xa0', '\u200b', '\u200c', '\u200d']
    )

    try:
        raw_text.encode('utf-8')
        encoding = "utf-8"
    except UnicodeEncodeError:
        encoding = "unknown"

    result = PDFExtractionResult(
        text=raw_text,
        page_count=len(doc),
        has_unicode_issuer=has_issues,
        encoding=encoding,
        extration_method="embedded",  # FITZ usa embedded text
        size_bytes=len(raw_text.encode("utf-8", errors="ignore")),
        file_size_kb=len(doc.tobytes()) / 1024,
    ) 

    doc.close()

    return result

def pdf_bytes_to_text(pdf_bytes: bytes) -> PDFExtractionResult:
    """
    Lê um PDF de bytes (upload) e retorna o texto e metadados.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    
    raw_text = "\n".join(text_parts)

    has_issues = any(
        char in raw_text
        for char in ['\xa0', '\u200b', '\u200c', '\u200d']
    )

    try:
        raw_text.encode('utf-8')
        encoding = "utf-8"
    except UnicodeEncodeError:
        encoding = "unknown"

    result = PDFExtractionResult(
        text=raw_text,
        page_count=len(doc),
        has_unicode_issuer=has_issues,
        encoding=encoding,
        extration_method="embedded", 
        size_bytes=len(raw_text.encode("utf-8", errors="ignore")),
        file_size_kb=len(pdf_bytes) / 1024, 
    )

    doc.close()
    return result