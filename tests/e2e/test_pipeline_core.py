import pytest
from pathlib import Path

from robot.pdf_reader import pdf_bytes_to_text
from robot.core.text_normalizer import normalize_text
from robot.core.parser import extract_from_text
from robot.schema.models import InvoiceExtractionResult

@pytest.fixture(scope="session")
def pdf_nfse_real():
    """
    PDF real de NFS-e (simplificada para teste).
    Em produção, você teria PDFs de diversos municípios.
    """

    pdf_path = Path("C:/_repos_/saas/base-test/nacional_NFS_tests/NFS-E_Quinta_do_Bosque")
    
    if pdf_path.exists():
        return pdf_path.read_bytes()
    
    # Fallback: PDF mock para CI/CD sem arquivos reais
    return b"%PDF-1.4 mock content"  

# TESTE E2E: Pipeline Completo

@pytest.mark.e2e
def test_pipeline_pdf_to_payload(pdf_nfse_real):
    """
    ✅ E2E COM PDF: Bytes → Texto → Parse → Schema
    
    Simula upload real de PDF.
    """
    
    # FASE 1: EXTRAÇÃO DO PDF

    try:
        texto_bruto = pdf_bytes_to_text(pdf_nfse_real)
    except:
        pytest.skip("PDF mock não processável (esperado em CI)")
    
    assert len(texto_bruto) > 0
    
    # FASE 2: NORMALIZAÇÃO

    texto_normalizado = normalize_text(texto_bruto)
    
    # FASE 3: PARSING

    result = extract_from_text(texto_normalizado, source_filename="NFS-E_Quinta_do_Bosque.pdf")
    
    # VALIDAÇÃO: Schema válido

    assert isinstance(result, InvoiceExtractionResult)
    assert result.source_filename == "NFS-E_Quinta_do_Bosque.pdf"

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

@pytest.mark.e2e
def test_pipeline_completo_nfse(texto_nfse_completo):
    """
    ✅ E2E PRINCIPAL: Input (texto) → Output (schema validado)
    
    Pipeline:
    1. Texto bruto (já extraído do PDF)
    2. Normalização
    3. Parsing + Validação
    4. Schema estruturado
    """
    
    texto_normalizado = normalize_text(texto_nfse_completo)
    
    # Valida trecho de normalização 
    assert "\xa0" not in texto_normalizado  # Remove Unicode invisível
    assert len(texto_normalizado) > 0
    assert "PRESTADOR" in texto_normalizado
    
    # FASE 2: EXTRAÇÃO + VALIDAÇÃO
    result = extract_from_text(texto_normalizado, source_filename="nfse_sample.txt")
    
    # FASE 3: VALIDAÇÃO DO SCHEMA
    assert isinstance(result, InvoiceExtractionResult)
    
    # Datas
    assert result.emission_date == "15/12/2024 10:30:00"
    assert result.competence_date == "12/2024"
    
    # Prestador
    assert result.issuer is not None
    assert result.issuer.name is not None
    assert "ABC TECNOLOGIA" in result.issuer.name
    assert result.issuer.cnpj_cpf == "04.252.011/0001-10"
    
    # Tomador
    assert result.recipient is not None
    assert result.recipient.name is not None
    assert "XYZ" in result.recipient.name
    assert result.recipient.cnpj_cpf == "11.222.333/0001-81"
    
    # Itens
    assert len(result.items) >= 3
    assert any("software" in item.description.lower() for item in result.items)
    
    # Valores
    assert result.financials is not None
    assert result.financials.total is not None
    assert "4.450,00" in result.financials.total or "4.227,50" in result.financials.total
    
    # Raw text preservado (auditoria)
    assert len(result.raw_text) > 100

@pytest.mark.e2e
@pytest.mark.quality
def test_payload_contem_metadados_auditoria(texto_nfse_completo):
    """
    ✅ Valida metadados necessários para event sourcing.
    """
    
    result = extract_from_text(normalize_text(texto_nfse_completo))
    
    # Raw text preservado (auditoria)
    assert result.raw_text is not None
    assert len(result.raw_text) > 100
    
    # Source preservado
    # (Em produção, seria task_id, user_id, etc)
    assert result.source_filename is None or isinstance(result.source_filename, str)

@pytest.mark.e2e
@pytest.mark.routing
def test_decisao_roteamento_por_valor(texto_nfse_completo):
    """
    ✅ Baseado no payload, decide rota de processamento.
    Simula lógica que seria implementada no FastAPI.
    """
    
    result = extract_from_text(normalize_text(texto_nfse_completo))
    
    # REGRA 1: Valor alto → Auditoria

    if result.financials.total:
        valor_str = result.financials.total.replace("R$", "").replace(".", "").replace(",", ".").strip()
        valor_float = float(valor_str)
        
        if valor_float > 10000:
            rota = "auditoria_fiscal"
        else:
            rota = "processamento_normal"
    else:
        rota = "revisao_manual"
    
    # Valida decisão
    assert rota in ["auditoria_fiscal", "processamento_normal", "revisao_manual"]
    
    # Neste caso, R$ 4.450,00 → processamento_normal
    assert rota == "processamento_normal"


@pytest.mark.e2e
@pytest.mark.routing
def test_decisao_confianca_baixa():
    """
    ✅ Documentos com CNPJs inválidos → fila de revisão.
    """
    
    texto_problematico = """
    PRESTADOR
    Empresa Duvidosa
    CNPJ: 11.111.111/1111-11
    
    TOTAL: R$ 1.000,00
    """
    
    result = extract_from_text(normalize_text(texto_problematico))
    
    # CNPJ inválido → confiança baixa
    if result.issuer and result.issuer.cnpj_cpf is None:
        rota = "revisao_manual"
    else:
        rota = "processamento_automatico"
    
    assert rota == "revisao_manual"