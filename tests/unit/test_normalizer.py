from robot.core.text_normalizer import normalize_text

def test_normalize_remove_invisible_chars():
    raw ="VALOR\xa0\xa0TOTAL\n400 , 00"

    clean = normalize_text(raw)

    assert "\xa0" not in clean
    assert "400,00" in clean

def test_normalize_preserves_structure():
    raw = """
    PRESTADOR DE SERVIÇOS
    EMPRESA TESTE LTDA
    
    TOMADOR DE SERVIÇO
    CLIENTE TESTE LTDA
    """

    clean = normalize_text(raw)

    assert "PRESTADOR DE SERVIÇOS" in clean
    assert "TOMADOR DE SERVIÇO" in clean