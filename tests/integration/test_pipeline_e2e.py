import pytest
from robot.core.parser import extract_from_text
from robot.core.pdf_reader import pdf_bytes_to_text
from robot.core.text_normalizer import normalize_text

@pytest.mark.e2e
@pytest.mark.audit
def test_pipeline_full_flow(pdf_sample_bytes):
    raw = pdf_bytes_to_text(pdf_sample_bytes)
    clean = normalize_text(raw)
    payload = extract_from_text(clean)

    assert payload.emission_date is not None
    assert payload.competence_date is not None
    assert payload.emission_date is not None
    assert payload.issuer is not None
    assert payload.recipient is not None
    assert payload.financials is not None
    assert payload.items is not None
    
