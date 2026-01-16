import hashlib
import time
import os
from datetime import datetime
from typing import Union, Optional, Dict 
from pathlib import Path

from pdf_reader import pdf_path_to_text, pdf_bytes_to_text, PDFExtractionResult
from .core.text_normalizer import normalize_text
from .core.parser import extract_from_text
from .schema.orchestrator_models import PipelineResult, OrchestratorEvent

class Orchestrator:
    """
    Coordenador do pipeline RPA.
    Responsável por unir Reader -> Normalizer -> Parser com observabilidade e rastreabilidade.
    NÃO decide persistência. Apenas gera eventos confiáveis.
    """
    
    def __init__(self):
        pass

    def _calculate_hash(self, data: Union[str, bytes]) -> str:
        """Gera SHA-256 determinístico do conteúdo."""
        if isinstance(data, str):
            content = data.encode('utf-8')
        else:
            content = data
        return hashlib.sha256(content).hexdigest()

    def process(self, input_data: Union[str, bytes, Path], context: Dict[str, str]) -> PipelineResult:
        """
        Executa o pipeline completo.
        
        Args:
            input_data: Caminho do arquivo (str/Path) ou bytes do PDF.
            context: Dicionário obrigatório com 'trace_id', 'execution_id', 'tenant_id'.
        """
        trace_id = context.get("trace_id", "unknown_trace")
        execution_id = context.get("execution_id", "unknown_exec")
        tenant_id = context.get("tenant_id", "unknown_tenant")
        
        result = PipelineResult(
            trace_id=trace_id,
            execution_id=execution_id,
            tenant_id=tenant_id,
            start_time=datetime.now(),
            status="error", # Pessimista por padrão
            events=[],
            raw_metadata={}
        )

        try:
            # ====================================================
            # 1. READ STAGE
            # ====================================================
            start_read = time.time()
            pdf_result: Optional[PDFExtractionResult] = None
            
            # Identifica tipo de input para metadados (SEM LOGAR CONTEÚDO)
            input_type = "bytes"
            input_source = "memory"
            
            try:
                if isinstance(input_data, (str, Path)):
                    input_path = str(input_data)
                    input_type = "file"
                    input_source = input_path
                    if not os.path.exists(input_path):
                        raise FileNotFoundError(f"File not found: {input_path}")
                        
                    # Hash do arquivo fisico
                    with open(input_path, "rb") as f:
                        file_bytes = f.read()
                        input_hash = self._calculate_hash(file_bytes)
                        
                    pdf_result = pdf_path_to_text(input_path)
                
                else:
                    # Bytes diretos
                    input_hash = self._calculate_hash(input_data)
                    pdf_result = pdf_bytes_to_text(input_data)

                # Sucesso na leitura
                duration_read = time.time() - start_read
                
                # Registra metadados brutos fundamentais agora que lemos
                result.raw_metadata = {
                    "input_hash_sha256": input_hash,
                    "input_type": input_type,
                    "file_size_bytes": pdf_result.size_bytes,
                    "page_count": pdf_result.page_count,
                    "encoding_detected": pdf_result.encoding
                }

                event_read = OrchestratorEvent(
                    stage="READ",
                    status="SUCCESS",
                    timestamp=datetime.now(),
                    details={
                        "duration_sec": round(duration_read, 4),
                        "page_count": pdf_result.page_count,
                        "extraction_method": pdf_result.extration_method,
                        "input_source": input_source
                    },
                    error_policy="CONTINUE"
                )
                result.events.append(event_read)

            except Exception as e:
                # Falha na leitura é fatal (ABORT)
                result.events.append(OrchestratorEvent(
                    stage="READ",
                    status="FAILURE",
                    details={"error": str(e)},
                    error_policy="ABORT"
                ))
                raise e # Re-raise para cair no catch global e finalizar

            # ====================================================
            # 2. NORMALIZE STAGE
            # ====================================================
            start_norm = time.time()
            raw_text = pdf_result.text
            
            # Hash do texto bruto extraído
            raw_text_hash = self._calculate_hash(raw_text)
            
            try:
                normalized_text = normalize_text(raw_text)
                
                duration_norm = time.time() - start_norm
                normalized_text_hash = self._calculate_hash(normalized_text)
                
                result.events.append(OrchestratorEvent(
                    stage="NORMALIZE",
                    status="SUCCESS",
                    timestamp=datetime.now(),
                    details={
                        "duration_sec": round(duration_norm, 4),
                        "raw_text_hash_sha256": raw_text_hash,
                        "normalized_text_hash_sha256": normalized_text_hash,
                        "reduction_ratio": round(1 - (len(normalized_text)/len(raw_text)), 2) if len(raw_text) > 0 else 0
                    },
                    error_policy="CONTINUE"
                ))
                
            except Exception as e:
                 # Falha na normalização pode ser fatal dependendo da regra, aqui assumo ABORT
                result.events.append(OrchestratorEvent(
                    stage="NORMALIZE",
                    status="FAILURE",
                    details={"error": str(e)},
                    error_policy="ABORT"
                ))
                raise e

            # ====================================================
            # 3. PARSE STAGE
            # ====================================================
            start_parse = time.time()
            
            try:
                extraction_result = extract_from_text(normalized_text, source_filename=str(input_source))
                
                duration_parse = time.time() - start_parse
                
                # Validação soft: Se não extraiu nada relevante, marcamos warning?
                # Por hora, se não crashou, é success. A qualidade é medida pelo validators.
                
                result.events.append(OrchestratorEvent(
                    stage="PARSE",
                    status="SUCCESS",
                    timestamp=datetime.now(),
                    details={
                        "duration_sec": round(duration_parse, 4),
                        "items_count": len(extraction_result.items),
                        "issuer_found": bool(extraction_result.issuer),
                        "recipient_found": bool(extraction_result.recipient),
                        "total_value": extraction_result.financials.total
                    },
                    error_policy="CONTINUE"
                ))
                
                # Pipeline Completo com Sucesso
                result.payload = extraction_result
                result.status = "success"

            except Exception as e:
                result.events.append(OrchestratorEvent(
                    stage="PARSE",
                    status="FAILURE",
                    details={"error": str(e)},
                    error_policy="ABORT"
                ))
                raise e

        except Exception as e:
            # Catch global para garantir que retornamos o result com "error"
            # mas com o histórico do que aconteceu até o momento.
            result.status = "error"
            # O evento de falha já foi adicionado nos blocos try internos
            
        finally:
            result.end_time = datetime.now()
            
        return result
