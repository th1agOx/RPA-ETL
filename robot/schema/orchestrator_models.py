from typing import List, Optional, Dict, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .models import InvoiceExtractionResult

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
    
    status: Literal["success", "error"]
    
    # Audit Trail: Lista ordenada de eventos
    events: List[OrchestratorEvent] = Field(default_factory=list)
    
    # Payload: Só existe se status == success
    # Usando Optional para garantir que falhas não tenham payload parcial
    payload: Optional[InvoiceExtractionResult] = None
    
    # Metadados brutos (ex: hashes de arquivos, tamanho)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
