from pydantic import BaseModel
from typing import List, Optional

class Item(BaseModel): ##     Semântica para agente n8n
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_value: Optional[str] = None  
    cfop: Optional[str] = None
    raw: Optional[str] = None


class Financials(BaseModel):  ##     Financeiro, Fiscal e event sourcing ( auditoria )
    total: Optional[str] = None
    taxes: Optional[dict] = None
    payment_method: Optional[str] = None


class Party(BaseModel): ##     Treinagem de embeddings , entidades fiscais (Quem presta o serviço | Quem compra)
    name: Optional[str] = None
    cnpj_cpf: Optional[str] = None
    address: Optional[str] = None
    municipal_insc: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class InvoiceExtractionResult(BaseModel): ##     Contrato entre o RPA e o SaaS

    emission_date: Optional[str] = None
    competence_date: Optional[str] = None
    chave_acesso: Optional[str] = None


    issuer: Optional[Party] = None
    recipient: Optional[Party] = None


    items: List[Item] = []
    financials: Optional[Financials] = None

    # fallback raw
    raw_text: str
    tenant_id: Optional[str] = None
    source_filename: Optional[str] = None