import pytest

from robot.core.parser import extract_from_text
from robot.core.text_normalizer import normalize_text

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

# TESTE DE PAYLOAD PARA DIFERENTES DESTINOS

@pytest.mark.e2e
@pytest.mark.payload_transform
def test_payload_transform_para_erp(texto_nfse_completo):
    """
    ✅ Transforma payload para formato esperado pelo ERP.
    Simula adaptador que seria usado no roteamento.
    """
    
    result = extract_from_text(normalize_text(texto_nfse_completo))
    
    # Transforma para formato ERP
    erp_payload = {
        "document_type": "NFS-e",
        "issue_date": result.emission_date,
        "supplier": {
            "tax_id": result.issuer.cnpj_cpf if result.issuer else None,
            "name": result.issuer.name if result.issuer else None
        },
        "customer": {
            "tax_id": result.recipient.cnpj_cpf if result.recipient else None,
            "name": result.recipient.name if result.recipient else None
        },
        "line_items": [
            {
                "description": item.description,
                "amount": item.unit_value
            }
            for item in result.items
        ],
        "total_amount": result.financials.total
    }
    
    # Validações
    assert erp_payload["document_type"] == "NFS-e"
    assert erp_payload["supplier"]["tax_id"] is not None
    assert len(erp_payload["line_items"]) >= 3


@pytest.mark.contract
@pytest.mark.payload_transform
def test_payload_transform_para_analytics(texto_nfse_completo):
    """
    ✅ Transforma payload para dados analíticos (TimescaleDB).
    """
    
    result = extract_from_text(normalize_text(texto_nfse_completo))
    
    # Transforma para analytics
    analytics_event = {
        "event_time": result.emission_date,
        "event_type": "invoice_processed",
        "issuer_cnpj": result.issuer.cnpj_cpf if result.issuer else None,
        "total_value": result.financials.total,
        "items_count": len(result.items),
        "has_key": result.chave_acesso is not None
    }
    
    # Validações
    assert analytics_event["event_type"] == "invoice_processed"
    assert analytics_event["items_count"] >= 0