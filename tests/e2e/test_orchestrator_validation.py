import pytest
from unittest.mock import MagicMock, patch
from robot.orchestrator import Orchestrator
from robot.schema.orchestrator_models import PipelineResult

@pytest.fixture
def orchestrator():
    return Orchestrator()

@pytest.fixture
def sample_context():
    return {
        "trace_id": "trace-val-001",
        "execution_id": "exec-val-001",
        "tenant_id": "tenant-A"
    }

# Mock PDF Result para isolar
class MockPDFResult:
    def __init__(self, text="Sample", page_count=1, size_bytes=100):
        self.text = text
        self.page_count = page_count
        self.size_bytes = size_bytes
        self.encoding = "utf-8"
        self.extration_method = "embedded"

@patch("robot.orchestrator.pdf_bytes_to_text")
@patch("robot.orchestrator.normalize_text")
@patch("robot.orchestrator.extract_from_text")
@patch("robot.orchestrator.cnpj_validator")
@patch("robot.orchestrator.validator_valor_fiscal_brasileiro")
@patch("robot.orchestrator.nfe_key_validator")
def test_orchestrator_validate_success(mock_key_val, mock_fiscal_val, mock_cnpj_val, mock_parser, mock_norm, mock_reader, orchestrator, sample_context):
    """
    Cenário: Tudo válido. Score deve ser 1.0 e Status 'success'.
    """
    mock_reader.return_value = MockPDFResult("Conteudo valido")
    mock_norm.return_value = "Conteudo valido"
    
    # Mock Validators Responses
    mock_cnpj_val.return_value = {"valido": True}
    mock_fiscal_val.return_value = {"valido": True}
    mock_key_val.return_value = {"valido": True}

    # Mock do payload extraído com tudo certo
    mock_payload = MagicMock()
    mock_payload.issuer.cnpj_cpf = "04.252.011/0001-10" 
    mock_payload.recipient.cnpj_cpf = "11.222.333/0001-81"
    mock_payload.financials.total = "R$ 1.500,00"
    mock_payload.chave_acesso = "35241204252011000110550010000012345012345678903"
    mock_parser.return_value = mock_payload

    result = orchestrator.process(b"PDF_BYTES", sample_context)

    assert result.status == "success"
    assert result.trust_score == 1.0
    assert len(result.validation_issues) == 0
    assert len(result.events) == 4 # READ, NORMALIZE, PARSE, VALIDATE
    assert result.events[3].stage == "VALIDATE"
    assert result.events[3].status == "SUCCESS"

@patch("robot.orchestrator.pdf_bytes_to_text")
@patch("robot.orchestrator.normalize_text")
@patch("robot.orchestrator.extract_from_text")
@patch("robot.orchestrator.cnpj_validator")
@patch("robot.orchestrator.validator_valor_fiscal_brasileiro")
@patch("robot.orchestrator.nfe_key_validator")
def test_orchestrator_validate_partial(mock_key_val, mock_fiscal_val, mock_cnpj_val, mock_parser, mock_norm, mock_reader, orchestrator, sample_context):
    """
    Cenário: Emitente válido (crítico ok), mas Tomador ausente (warning).
    Status deve ser 'partial' e Score < 1.0.
    """
    mock_reader.return_value = MockPDFResult()
    mock_norm.return_value = ""
    
    mock_cnpj_val.return_value = {"valido": True}
    mock_fiscal_val.return_value = {"valido": True}
    mock_key_val.return_value = {"valido": True}
    
    mock_payload = MagicMock()
    mock_payload.issuer.cnpj_cpf = "04.252.011/0001-10" # Válido
    mock_payload.financials.total = "R$ 1.000,00" # Válido
    
    # Falhas / Warnings
    mock_payload.recipient = None # Missing Recipient (Warning)
    mock_payload.chave_acesso = None # Missing Key (not invalid, just missing optional check logic if not None, but wait logic says 'if payload.chave_acesso')
    
    mock_parser.return_value = mock_payload

    result = orchestrator.process(b"PDF_BYTES", sample_context)

    assert result.status == "partial"
    assert result.trust_score < 1.0
    assert result.trust_score >= 0.0
    
    # Verifica issues
    codes = [i.code for i in result.validation_issues]
    assert "MISSING_RECIPIENT" in codes
    
@patch("robot.orchestrator.pdf_bytes_to_text")
@patch("robot.orchestrator.normalize_text")
@patch("robot.orchestrator.extract_from_text")
@patch("robot.orchestrator.cnpj_validator")
@patch("robot.orchestrator.validator_valor_fiscal_brasileiro")
@patch("robot.orchestrator.nfe_key_validator")
def test_orchestrator_validate_error(mock_key_val, mock_fiscal_val, mock_cnpj_val, mock_parser, mock_norm, mock_reader, orchestrator, sample_context):
    """
    Cenário: Emitente inválido (crítico). Status deve ser 'error'.
    """
    mock_reader.return_value = MockPDFResult()
    mock_norm.return_value = ""

    # Mock Validador retornando invalido
    mock_cnpj_val.return_value = {"valido": False, "erro": "Checksum inválido"}
    mock_fiscal_val.return_value = {"valido": True}
    
    mock_payload = MagicMock()
    mock_payload.issuer.cnpj_cpf = "00.000.000/0000-00"
    mock_payload.financials.total = "R$ 100,00"
    mock_parser.return_value = mock_payload

    result = orchestrator.process(b"PDF_BYTES", sample_context)

    assert result.status == "error"
    # Embora seja sucesso técnico do pipeline (não crashou), é erro de negócio crítico
    assert result.trust_score < 1.0
    assert any(i.code == "INVALID_ISSUER_CNPJ" for i in result.validation_issues)

@patch("robot.orchestrator.pdf_bytes_to_text")
@patch("robot.orchestrator.normalize_text")
@patch("robot.orchestrator.extract_from_text")
@patch("robot.orchestrator.cnpj_validator")
@patch("robot.orchestrator.validator_valor_fiscal_brasileiro")
@patch("robot.orchestrator.nfe_key_validator")
def test_orchestrator_consistency_determinism(mock_key_val, mock_fiscal_val, mock_cnpj_val, mock_parser, mock_norm, mock_reader, orchestrator, sample_context):
    """
    Cenário: Duas execuções com mesmo input produzem resultados idênticos.
    Garante ausência de estado compartilhado/escondido.
    """
    mock_reader.return_value = MockPDFResult("Static Content")
    mock_norm.return_value = "Static Content"
    
    mock_cnpj_val.return_value = {"valido": True}
    mock_fiscal_val.return_value = {"valido": True}
    mock_key_val.return_value = {"valido": True}

    fixed_payload = MagicMock()
    fixed_payload.issuer.cnpj_cpf = "04.252.011/0001-10"
    fixed_payload.recipient.cnpj_cpf = "11.222.333/0001-81" 
    fixed_payload.financials.total = "R$ 500,00"
    fixed_payload.chave_acesso = "35241204252011000110550010000012345012345678903"
    
    mock_parser.return_value = fixed_payload

    # Execução 1
    res1 = orchestrator.process(b"STATIC_INPUT", sample_context)
    
    # Execução 2
    res2 = orchestrator.process(b"STATIC_INPUT", sample_context)
    
    # Assert Identidade
    assert res1.status == res2.status
    assert res1.trust_score == res2.trust_score
    assert len(res1.events) == len(res2.events)
    assert res1.events[3].stage == res2.events[3].stage
    
    # Assert Conteúdo Issues
    issues1 = [i.model_dump() for i in res1.validation_issues]
    issues2 = [i.model_dump() for i in res2.validation_issues]
    assert issues1 == issues2