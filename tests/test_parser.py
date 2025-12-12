from robot.core.pdf_reader import pdf_bytes_to_text
from robot.core.text_normalizer import normalize_text
from robot.core.parser import extract_from_text

def test_extract_basic_invoice():
    with open("C:/_repos_/saas/base-test/nacional_NFS_tests/NFS-E_amigao.pdf", "rb") as f:
        raw = pdf_bytes_to_text(f.read())

    clean = normalize_text(raw)
    result = extract_from_text(clean)

    assert result.invoice_id is not None
    assert "400,00" in result.values
    assert len(result.values) < 10