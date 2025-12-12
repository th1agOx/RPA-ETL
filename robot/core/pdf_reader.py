import fitz

def pdf_path_to_text(path: str) -> str:
    """Lê um PDF do disco e retorna o texto concatenado."""
    doc = fitz.open(path)
    text_parts = []

    for page in doc:
        text_parts.append(page.get_text())

    doc.close()
    return "\n" .join(text_parts)


def pdf_bytes_to_text(pdf_bytes: bytes) -> str:
    """Lê um PDF recebido em bytes (upload) e retorna o texto concatenado."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []

    for page in doc:
        text_parts.append(page.get_text())
    
    doc.close()
    return "\n" .join(text_parts)