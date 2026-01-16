import pytest

from robot.core.text_normalizer import normalize_text
from robot.core.parser import extract_from_text

@pytest.fixture(scope="session")
def texto_nfse_completo():
    """
    Texto pré-extraído de NFS-e real.
    Usado quando não há PDF disponível.
    """
    return """
    PREFEITURA MUNICIPAL DE SÃO PAULO
    NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFS-e
    
    Número: 123456
    Data de Emissão: 15/12/2024 10:30:00
    Competência: 12/2024
    
    PRESTADOR DE SERVIÇOS
    EMPRESA ABC TECNOLOGIA LTDA
    CNPJ: 04.252.011/0001-10
    Inscrição Municipal: 123.456.789-0
    Endereço: Rua Teste, 123 - São Paulo/SP
    
    TOMADOR DE SERVIÇOS
    CLIENTE XYZ INDÚSTRIA S.A.
    CNPJ: 11.222.333/0001-81
    Endereço: Av Principal, 456 - São Paulo/SP
    
    DISCRIMINAÇÃO DOS SERVIÇOS
    Desenvolvimento de software customizado        10 HRS    R$ 200,00    R$ 2.000,00
    Consultoria em arquitetura de sistemas         5 HRS    R$ 250,00    R$ 1.250,00
    Treinamento técnico da equipe                  8 HRS    R$ 150,00    R$ 1.200,00
    
    VALOR TOTAL DOS SERVIÇOS: R$ 4.450,00
    
    TRIBUTOS:
    ISS (5%): R$ 222,50
    
    VALOR LÍQUIDO: R$ 4.227,50
    
    OBSERVAÇÕES:
    Serviços prestados conforme contrato 2024/001
    """

@pytest.mark.contract
@pytest.mark.quality
def test_payload_pronto_para_api(texto_nfse_completo):
    """
    ✅ Valida que payload pode ser serializado para JSON (FastAPI).
    """
    
    result = extract_from_text(normalize_text(texto_nfse_completo))
    
    # Serialização para JSON
    payload = result.dict()
    
    # Validações de estrutura
    assert "emission_date" in payload
    assert "issuer" in payload
    assert "recipient" in payload
    assert "items" in payload
    assert "financials" in payload
    assert "raw_text" in payload
    
    # Validação de tipos
    assert isinstance(payload["items"], list)
    assert isinstance(payload["financials"], dict)
    
    # Validação de valores não-nulos críticos
    assert payload["emission_date"] is not None
    assert payload["issuer"] is not None
    assert payload["financials"]["total"] is not None

# TESTE DE SERIALIZAÇÃO (Preparar para API)

@pytest.mark.contract
def test_payload_serializavel_json(texto_nfse_completo):
    """
    ✅ Payload pode ser convertido para JSON sem erros.
    Necessário para FastAPI response.
    """
    import json
    
    result = extract_from_text(normalize_text(texto_nfse_completo))
    payload = result.dict()
    
    # Serializa para JSON
    json_str = json.dumps(payload, ensure_ascii=False, default=str)
    
    # Valida que é JSON válido
    assert len(json_str) > 100
    
    # Deserializa de volta
    payload_restored = json.loads(json_str)
    
    assert payload_restored["emission_date"] == payload["emission_date"]
    assert payload_restored["issuer"]["cnpj_cpf"] == payload["issuer"]["cnpj_cpf"]
