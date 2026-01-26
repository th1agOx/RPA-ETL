import hashlib
import time
import os
from datetime import datetime
from typing import Union, Optional, Dict, List, Any 
from pathlib import Path

from .pdf_reader import pdf_path_to_text, pdf_bytes_to_text, PDFExtractionResult
from .core.text_normalizer import normalize_text
from .core.parser import extract_from_text
from .core.validators import nfe_key_validator, cnpj_validator, validator_valor_fiscal_brasileiro
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

    # Configuração de Scoring (Trust Layer)
    BASE_SCORE = 1.0
    PENALTIES = {
        "missing_issuer_cnpj": 1.0, # Fatal (Critical)
        "invalid_issuer_cnpj": 1.0, # Fatal (Critical)
        "missing_total": 0.5,       # High impact
        "missing_recipient": 0.1,   # Warning
        "invalid_key": 0.2,         # Warning
        "low_confidence_item": 0.05 # Minor per item
    }

    def _validate_stage(self, payload) -> tuple[List[Any], float]:
        """
        Executa validações semânticas e calcula Trust Score.
        Retorna (issues, score).
        """
        issues = []
        score = self.BASE_SCORE
        
        from .schema.orchestrator_models import ValidationIssue

        # 1. Valida Emitente (Crítico)
        if not payload.issuer or not payload.issuer.cnpj_cpf:
            issues.append(ValidationIssue(
                code="MISSING_ISSUER",
                field="issuer.cnpj_cpf",
                message="CNPJ do emitente não encontrado",
                severity="error"
            ))
            score -= self.PENALTIES["missing_issuer_cnpj"]
        else:
            val_cnpj = cnpj_validator(payload.issuer.cnpj_cpf)
            if not val_cnpj["valido"]:
                 issues.append(ValidationIssue(
                    code="INVALID_ISSUER_CNPJ",
                    field="issuer.cnpj_cpf",
                    message=f"CNPJ inválido: {val_cnpj.get('erro')}",
                    severity="error"
                ))
                 score -= self.PENALTIES["invalid_issuer_cnpj"]

        # 2. Valida Tomador (Aviso)
        if not payload.recipient or not payload.recipient.cnpj_cpf:
             issues.append(ValidationIssue(
                code="MISSING_RECIPIENT",
                field="recipient",
                message="Tomador não identificado",
                severity="warning"
            ))
             score -= self.PENALTIES["missing_recipient"]

        # 3. Valida Total (Crítico/High)
        if not payload.financials or not payload.financials.total:
             issues.append(ValidationIssue(
                code="MISSING_TOTAL",
                field="financials.total",
                message="Valor total não encontrado",
                severity="error"
            ))
             score -= self.PENALTIES["missing_total"]
        else:
             val_total = validator_valor_fiscal_brasileiro(payload.financials.total)
             if not val_total["valido"]:
                  issues.append(ValidationIssue(
                    code="INVALID_TOTAL_FORMAT",
                    field="financials.total",
                    message=f"Formato inválido: {val_total.get('erro')}",
                    severity="warning" # Pode ser warning se o OCR errou algo sutil, mas impacta score
                ))
                  score -= 0.3

        # 4. Valida Chave (Aviso)
        if payload.chave_acesso:
            val_key = nfe_key_validator(payload.chave_acesso)
            if not val_key["valido"]:
                 issues.append(ValidationIssue(
                    code="INVALID_KEY",
                    field="chave_acesso",
                    message=f"Chave inválida: {val_key.get('erro')}",
                    severity="warning"
                ))
                 score -= self.PENALTIES["invalid_key"]

        # Clamp score
        return issues, max(0.0, score)

    def process(self, input_data: Union[str, bytes, Path], context: Dict[str, str]) -> PipelineResult:
        """
        Executa o pipeline completo: READ -> NORMALIZE -> PARSE -> VALIDATE.
        """
        trace_id = context.get("trace_id", "unknown_trace")
        execution_id = context.get("execution_id", "unknown_exec")
        tenant_id = context.get("tenant_id", "unknown_tenant")
        
        result = PipelineResult(
            trace_id=trace_id,
            execution_id=execution_id,
            tenant_id=tenant_id,
            start_time=datetime.now(),
            status="error",
            events=[],
            raw_metadata={},
            trust_score=0.0
        )

        try:
            # ... (READ, NORMALIZE stages remain similar, reusing existing logic implicitly or logically)
            # Para economizar tokens, vou assumir que o código anterior de READ e NORMALIZE está aqui, 
            # na verdade como estou substituindo o método todo, preciso reescrever parte dele ou instruir a ferramenta
            # a manter o topo. Mas o replace é por bloco. Vou reescrever o fluxo mantendo a lógica anterior
            # e adicionando o VALIDATE.
            
            # --- READ STAGE ---
            start_read = time.time()
            pdf_result: Optional[PDFExtractionResult] = None
            input_type = "bytes"
            input_source = "memory"
            
            try:
                if isinstance(input_data, (str, Path)):
                    input_path = str(input_data)
                    input_type = "file"
                    input_source = input_path
                    if not os.path.exists(input_path):
                        raise FileNotFoundError(f"File not found: {input_path}")
                    with open(input_path, "rb") as f:
                        file_bytes = f.read()
                        input_hash = self._calculate_hash(file_bytes)
                    pdf_result = pdf_path_to_text(input_path)
                else:
                    input_hash = self._calculate_hash(input_data)
                    pdf_result = pdf_bytes_to_text(input_data)

                duration_read = time.time() - start_read
                result.raw_metadata = {
                    "input_hash_sha256": input_hash,
                    "input_type": input_type,
                    "file_size_bytes": pdf_result.size_bytes,
                    "page_count": pdf_result.page_count,
                    "encoding_detected": pdf_result.encoding
                }
                result.events.append(OrchestratorEvent(
                    stage="READ", status="SUCCESS", timestamp=datetime.now(),
                    details={
                        "duration_sec": round(duration_read, 4), 
                        "page_count": pdf_result.page_count, 
                        "extraction_method": pdf_result.extration_method, 
                        "input_source": input_source
                    },
                    error_policy="CONTINUE"
                ))
            except Exception as e:
                result.events.append(OrchestratorEvent(
                    stage="READ",
                    status="FAILURE",
                    details={"error": str(e)},
                    error_policy="ABORT"
                ))
                raise e

            # --- NORMALIZE STAGE ---
            start_norm = time.time()
            raw_text = pdf_result.text
            raw_text_hash = self._calculate_hash(raw_text)
            
            try:
                normalized_text = normalize_text(raw_text)
                duration_norm = time.time() - start_norm
                normalized_text_hash = self._calculate_hash(normalized_text)
                
                result.events.append(OrchestratorEvent(
                    stage="NORMALIZE", status="SUCCESS", timestamp=datetime.now(),
                    details={
                        "duration_sec": round(duration_norm, 4), 
                        "raw_text_hash_sha256": raw_text_hash, 
                        "normalized_text_hash_sha256": normalized_text_hash, 
                        "reduction_ratio": round(
                            1 - (len(normalized_text)/len(raw_text)), 2
                            ) 
                            if len(raw_text) > 0 else 0
                    },
                    error_policy="CONTINUE"
                ))
            except Exception as e:
                result.events.append(OrchestratorEvent(
                    stage="NORMALIZE",
                    status="FAILURE",
                    details={"error": str(e)},
                    error_policy="ABORT"
                ))
                raise e

            # --- PARSE STAGE ---
            start_parse = time.time()
            try:
                extraction_result = extract_from_text(normalized_text, source_filename=str(input_source))
                duration_parse = time.time() - start_parse
                
                result.events.append(OrchestratorEvent(
                    stage="PARSE", status="SUCCESS", timestamp=datetime.now(),
                    details={
                        "duration_sec": round(duration_parse, 4), 
                        "items_count": len(extraction_result.items), 
                        "issuer_found": bool(extraction_result.issuer), 
                        "recipient_found": bool(extraction_result.recipient), 
                        "total_value": extraction_result.financials.total
                    },
                    error_policy="CONTINUE"
                ))
            except Exception as e:
                result.events.append(OrchestratorEvent(
                    stage="PARSE",
                    status="FAILURE",
                    details={"error": str(e)},
                    error_policy="ABORT"
                ))
                raise e

            # --- VALIDATE STAGE (NEW) ---
            start_validate = time.time()
            try:
                issues, score = self._validate_stage(extraction_result)
                duration_validate = time.time() - start_validate
                
                # Decisão de Status
                has_critical_error = any(i.severity == "error" for i in issues)
                
                final_status = "success"
                if has_critical_error:
                    final_status = "error"
                elif issues or score < 1.0: # Se tem warning ou score baixo
                    final_status = "partial"
                
                result.events.append(OrchestratorEvent(
                    stage="VALIDATE",
                    status="SUCCESS", 
                    timestamp=datetime.now(),
                    details={
                        "duration_sec": round(duration_validate, 4),
                        "trust_score": score,
                        "issues_count": len(issues),
                        "critical_errors": has_critical_error
                    },
                    error_policy="CONTINUE"
                ))
                
                result.payload = extraction_result
                result.validation_issues = issues
                result.trust_score = round(score, 2)
                result.status = final_status

            except Exception as e:
                result.events.append(OrchestratorEvent(
                    stage="VALIDATE", 
                    status="FAILURE", 
                    details={"error": str(e)}, 
                    error_policy="ABORT"
                ))
                raise e

        except Exception as e:
            result.status = "error"
            
        finally:
            result.end_time = datetime.now()
            
        return result
