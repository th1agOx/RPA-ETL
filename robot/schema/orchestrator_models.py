from typing import List, Optional, Dict, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .models import InvoiceExtractionResult

class ValidationIssue(BaseModel):
    code: str
    field: Optional[str] = None
    message: str
    severity: Literal["warning", "error"]

class OrchestratorEvent(BaseModel):
    """
    Representa um evento imutável ocorrido durante o pipeline.
    Usado para Event Sourcing e Observabilidade.
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    stage: Literal["READ", "NORMALIZE", "PARSE", "VALIDATE"]
    status: Literal["SUCCESS", "FAILURE"]
    # Details deve ser flat e serializável
    details: Dict[str, Any] = Field(default_factory=dict)
    error_policy: Literal["ABORT", "CONTINUE"] = "ABORT"

class PipelineResult(BaseModel):
    """
    Container final do processamento.
    NÃO é o evento em si, mas contem o histórico (Audit Trail) e o Payload.
    """
    trace_id: str
    execution_id: str
    tenant_id: str
    
    start_time: datetime
    end_time: Optional[datetime] = None
    
    status: Literal["success", "partial", "error"]
    
    # Trust Layer
    trust_score: float = 0.0 # 0.0 a 1.0
    validation_issues: List[ValidationIssue] = Field(default_factory=list)

    # Audit Trail: Lista ordenada de eventos
    events: List[OrchestratorEvent] = Field(default_factory=list)
    
    # Payload: Só existe se status == success ou partial
    payload: Optional[InvoiceExtractionResult] = None
    
    # Metadados brutos (ex: hashes de arquivos, tamanho)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def map_to_event_contract(result: "PipelineResult") -> dict:
        return {
            "event_id" : result.execution_id,
            "event_type": "fiscal.extraction.completed",
            "timestamp": result.end_time.isoformat() if result.end_time else datetime.now().isoformat(),
            "tenant_id": result.tenant_id,
            "status": result.status, 
            "data": {
                "payload": result.payload.model_dump() if result.payload else {},
                "audit_trail": [event.model_dump() for event in result.events],
                "metrics": {
                    "total_duration_ms": (result.end_time - result.start_time).total_seconds() * 1000
                }
            }
        }