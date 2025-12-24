import pytest
from unittest.mock import MagicMock, patch
from robot.orchestrator import Orchestrator
from robot.schema.orchestrator_models import PipelineResult

# Mocking the dependencies to test Orchestrator Logic purely
# We don't want to test if fitz works (that is unit test), we want to test wiring

@pytest.fixture
def orchestrator():
    return Orchestrator()

@pytest.fixture
def sample_context():
    return {
        "trace_id": "test-trace-123",
        "execution_id": "exec-001",
        "tenant_id": "tenant-A"
    }

class MockPDFResult:
    def __init__(self, text="Sample Invoice", page_count=1, size_bytes=100):
        self.text = text
        self.page_count = page_count
        self.size_bytes = size_bytes
        self.encoding = "utf-8"
        self.extration_method = "embedded"

def test_orchestrator_success_flow_bytes(orchestrator, sample_context):
    """
    Verifica se o pipe funciona de ponta a ponta com input BYTES.
    """
    dummy_bytes = b"PDF_CONTENT_FAKE"
    
    # Mock das funções core
    with patch("robot.orchestrator.pdf_bytes_to_text") as mock_reader, \
         patch("robot.orchestrator.normalize_text") as mock_norm, \
         patch("robot.orchestrator.extract_from_text") as mock_parser: # Fix import path if needed
        
        # Setup Mocks
        mock_reader.return_value = MockPDFResult(text="Raw Text")
        mock_norm.return_value = "Normalized Text"
        
        mock_extraction = MagicMock()
        mock_extraction.items = []
        mock_extraction.financials.total = "R$ 100,00"
        mock_parser.return_value = mock_extraction

        # EXECUTE
        result = orchestrator.process(dummy_bytes, sample_context)

        # ASSERT
        assert result.status == "success"
        assert result.trace_id == "test-trace-123"
        assert len(result.events) == 3 # READ, NORMALIZE, PARSE
        
        # Check Event Sequence
        assert result.events[0].stage == "READ"
        assert result.events[0].status == "SUCCESS"
        
        assert result.events[1].stage == "NORMALIZE"
        assert result.events[1].status == "SUCCESS"
        assert "reduction_ratio" in result.events[1].details
        
        assert result.events[2].stage == "PARSE"
        assert result.events[2].status == "SUCCESS"

        # Check Metadata
        assert "input_hash_sha256" in result.raw_metadata
        assert result.raw_metadata["input_type"] == "bytes"

def test_orchestrator_failure_handling(orchestrator, sample_context):
    """
    Verifica se o pipe captura erro e retorna status ERROR com eventos até a falha.
    """
    dummy_bytes = b"BAD_PDF"
    
    with patch("robot.orchestrator.pdf_bytes_to_text") as mock_reader:
        mock_reader.side_effect = Exception("Critical PDF Error")
        
        result = orchestrator.process(dummy_bytes, sample_context)
        
        assert result.status == "error"
        assert len(result.events) == 1
        assert result.events[0].stage == "READ"
        assert result.events[0].status == "FAILURE"
        assert result.events[0].error_policy == "ABORT"
        assert result.payload is None # No payload on error
