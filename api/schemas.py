"""
Pydantic schemas for API contracts.
Separates business context from transport layer.
"""
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import json


class BusinessContext(BaseModel):
    """
    Business context for processing.
    NEVER contains binary data - only metadata.
    """
    tenant_id: str = Field(..., min_length=1, max_length=100, description="Tenant identifier")
    trace_id: Optional[str] = Field(None, description="Distributed tracing ID")
    execution_id: Optional[str] = Field(None, description="Unique execution identifier")
    pipeline: Literal["enterprise", "custom"] = Field(
        default="enterprise",
        description="Pipeline type: enterprise (Celery) or custom (n8n)"
    )
    dry_run: bool = Field(default=False, description="Simulation mode flag")
    priority: Literal["low", "normal", "high"] = Field(default="normal")
    source: Optional[str] = Field(None, description="Source system identifier")
    
    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        """Ensure tenant_id contains only safe characters."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("tenant_id must contain only alphanumeric, dash, or underscore")
        return v


class ProcessResponse(BaseModel):
    """
    Standard API response for process requests.
    """
    execution_id: str
    status: Literal["accepted", "processing", "completed", "failed"]
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    trace_id: Optional[str] = None


class AuditEventResponse(BaseModel):
    """
    Single audit event representation.
    """
    event_id: str
    event_index: int
    timestamp: datetime
    stage: Literal["READ", "NORMALIZE", "PARSE", "VALIDATE"]
    status: Literal["SUCCESS", "FAILURE"]
    details: Dict[str, Any]
    error_policy: Literal["ABORT", "CONTINUE"]


class AuditTrailResponse(BaseModel):
    """
    Complete audit trail for an execution.
    READ-ONLY - never triggers reprocessing.
    """
    execution_id: str
    tenant_id: str
    trace_id: str
    start_time: datetime
    end_time: Optional[datetime]
    final_status: Literal["success", "partial", "error"]
    trust_score: float = Field(ge=0.0, le=1.0)
    events: List[AuditEventResponse]
    validation_issues: List[Dict[str, Any]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """
    Health check response.
    """
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    checks: Dict[str, bool] = Field(default_factory=dict)


def parse_context_from_form(context_str: str) -> BusinessContext:
    """
    Parse and validate context from form-data string.
    
    Args:
        context_str: JSON string from multipart form
        
    Returns:
        Validated BusinessContext
        
    Raises:
        ValueError: If JSON is invalid or validation fails
    """
    try:
        context_dict = json.loads(context_str)
        return BusinessContext(**context_dict)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in context field: {e}")
    except Exception as e:
        raise ValueError(f"Context validation failed: {e}")
