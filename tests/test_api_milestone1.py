"""
Tests for API endpoints (Milestone 1).
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

pytestmark = pytest.mark.api

def test_health_check():
    """Test health endpoint returns 200 and correct structure."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.2.1"
    assert "checks" in data
    assert data["checks"]["api"] is True


def test_process_pdf_valid_request(tmp_path):
    """Test PDF processing endpoint with valid request."""
    # Create a minimal valid PDF
    pdf_content = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000015 00000 n\n0000000068 00000 n\n0000000125 00000 n\n0000000281 00000 n\n0000000364 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n456\n%%EOF"
    
    # Create test context
    context = {
        "tenant_id": "test-tenant",
        "pipeline": "enterprise"
    }
    
    response = client.post(
        "/v1/process/pdf",
        files={"file": ("test.pdf", pdf_content, "application/pdf")},
        data={"context": str(context).replace("'", '"')}
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "execution_id" in data
    assert data["execution_id"].startswith("test-tenant_")


def test_process_pdf_invalid_content_type():
    """Test PDF endpoint rejects non-PDF files."""
    response = client.post(
        "/v1/process/pdf",
        files={"file": ("test.txt", b"not a pdf", "text/plain")},
        data={"context": '{"tenant_id":"test"}'}
    )
    
    assert response.status_code == 415


def test_process_pdf_invalid_context():
    """Test PDF endpoint rejects invalid context."""
    pdf_content = b"%PDF-1.4\ntest"
    
    response = client.post(
        "/v1/process/pdf",
        files={"file": ("test.pdf", pdf_content, "application/pdf")},
        data={"context": "invalid json"}
    )
    
    assert response.status_code == 422


def test_process_pdf_missing_tenant_id():
    """Test PDF endpoint requires tenant_id."""
    pdf_content = b"%PDF-1.4\ntest"
    
    response = client.post(
        "/v1/process/pdf",
        files={"file": ("test.pdf", pdf_content, "application/pdf")},
        data={"context": '{"pipeline":"enterprise"}'}
    )
    
    assert response.status_code == 422
