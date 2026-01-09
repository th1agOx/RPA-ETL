import pytest
from robot.core.text_normalizer import normalize_text

@pytest.mark.normalization
def test_text_normalize_macro_cleneup_and_stability():
    raw = (
        "PRESTADOR\u00A0\u00A0DE\u00A0SERVIÇOS\n"
        "ABC TECNOLOGIA LTDA\n"
        "ABC TECNOLOGIA LTDA\n"
        "\n"
        "TOMADOR\u200B DE SERVIÇO\n"
        "CLIENTE XYZ\n"
        "VALOR\u00A0\u00A0TOTAL\n"
        "400 , 00\n"
    )

    normalized = normalize_text(raw)

    assert "\u00A0" not in normalized
    assert "\u200B" not in normalized

    assert "PRESTADOR" in normalized
    assert "TOMADOR" in normalized

    assert normalized.count("ABC TECNOLOGIA LTDA") == 1

    assert "400" in normalized