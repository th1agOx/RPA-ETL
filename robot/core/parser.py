import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..schema.models import InvoiceExtractionResult, Item, Party, Financials
from .validators import cnpj_validator, nfe_key_validator, monetari_value_validator

CNPJ_PATTERN = r'\b\d{2}\.?\d{3}\.?\d{3}/?\.?\d{4}-?\d{2}\b'
KEY_PATTERN = r'\b\d{44}\b'  # nfe key de 44 dígitos
VALUE_PATTERN = r'R?\$?\s*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))'

def find_key_valid_access(text: str) -> Optional[Dict[str, Any]]:
    """
    1. REGEX busca a sequência de 44 dígitos da chave
    2. Algoritmo valida estrutura + DV
    3. Retorna primeira válida 
    """
    extrations = re.findall(KEY_PATTERN, text)

    for extration in extrations:
        validation = nfe_key_validator(extration)
        if validation["valido"]:
            return validation
        
    return None

def find_cnpjs(text: str) -> List[Dict[str, Any]]:
    """
    1. REGEX extrai CNPJs
    2. Algoritmo valida veracidade
    3. Retorna metadados dos validos
    """
    extrations = re.findall(CNPJ_PATTERN, text)

    cnpjs_valid = []
    for extration in extrations:
        validation = cnpj_validator(extration)

        if validation["valido"]:
            cnpjs_valid.append(validation)

    return cnpjs_valid

def extract_emission_and_competence(text: str) -> tuple:

    patterns = [
        (r'EMISS[AÃ]O.*?(\d{2}/\d{2}/\d{4}(?:\s*\d{2}:\d{2}:\d{2})?)', 'emission'),
        (r'COMPET[EÊ]NCIA.*?(\d{2}/\d{2}/\d{4})', 'competence'), 
    ]

    emission = None
    competence = None

    for pattern, type in patterns:
        m = re.search(pattern, text, re.IGNORECASE)

        if m:
            if type == 'emission':
                emission = m.group(1)
            else:
                competence = m.group(1)

        # Fallback: primeira data encontrada
    if not emission:
        m = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        emission = m.group(1) if m else None
    
    return emission, competence

def extract_total_valid(text: str) -> Optional[str]:
    """
    Busca valor após palavras-chave de total
    Valida se há plausibilidade no valor extraido 
    """
    patterns = [
        r'TOTAL\s+GERAL.*?R?\$?\s*([\d\.,]+)',
        r'VALOR\s+L[IÍ]QUIDO.*?R?\$?\s*([\d\.,]+)',
        r'VALOR\s+TOTAL.*?R?\$?\s*([\d\.,]+)',
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidato = m.group(1)
            validacao = monetari_value_validator(candidato)
            
            if validacao["valido"]:
                return validacao["valor_formatado"]
    
    return None

# EXTRAÇÃO DE PRESTADOR/TOMADOR

def extract_issuer_recipient(text: str) -> tuple:
    """
    Extrai blocos PRESTADOR e TOMADOR.
    Valida CNPJs encontrados 
    """
    issuer = None
    recipient = None

    # PRESTADOR
    m = re.search(
        r'PRESTADOR(?:\s+DE\s+SERVI[CÇ]OS)?\s*(.*?)\s*(?:TOMADOR|DISCRIMINA[CÇ])', 
        text, 
        re.IGNORECASE | re.DOTALL
    )

    if m:
        issuer_block = m.group(1).strip()
        lines = issuer_block.splitlines()

        # Primeira linha = nome
        issuer_name = lines[0].strip() if lines else None

        # Busca CNPJ válido no bloco
        valid_cnpjs = find_cnpjs(issuer_block)
        provider_cnpj = valid_cnpjs[0]["cnpj_formatado"] if valid_cnpjs else None

        issuer = Party(name=issuer_name, cnpj_cpf=provider_cnpj)
    
    # TOMADOR
    m2 = re.search(
        r'TOMADOR(?:\s+DE\s+SERVI[CÇ]OS)?\s*(.*?)(?:DISCRIMINA[CÇ]|SERVI[CÇ]OS)', 
        text, 
        re.IGNORECASE | re.DOTALL
    )

    if m2:
        recipient_block = m2.group(1).strip()
        lines = recipient_block.splitlines()

        recipient_name = lines[0].strip() if lines else None

        valid_cnpjs = find_cnpjs(recipient_block)
        recipient_cnpj = valid_cnpjs[0]["cnpj_formatado"] if valid_cnpjs else None

        recipient = Party(name=recipient_name, cnpj_cpf=recipient_cnpj)

    return issuer, recipient

def extract_items(text: str) -> List[Item]:
    """
    Extrai itens da seção DISCRIMINAÇÃO.
    Usa heurística de colunas alinhadas.
    """
    items = []
    
    # Busca bloco de itens
    m = re.search(
        r'DISCRIMINA[CÇ][AÃ]O(?:\s+DOS\s+SERVI[CÇ]OS)?(.*?)(?:TOTAL\s+GERAL|VALOR\s+L[IÍ]QUIDO|OBSERVA[CÇ])',
        text,
        re.IGNORECASE | re.DOTALL
    )
    
    if not m:
        return items
    
    items_block = m.group(1).strip()
    
    for linha in items_block.splitlines():
        linha = linha.strip()
        
        if not linha or len(linha) < 10:
            continue
        
        # Tenta extrair valores monetários da linha
        valores = re.findall(VALUE_PATTERN, linha)
        valores_validos = [
            v for v in valores 
            if monetari_value_validator(v)["valido"]
        ]
        
        # Se tem valor, assume que é item válido
        if valores_validos:
            # Remove valores para pegar descrição
            descricao = linha
            for valor in valores_validos:
                descricao = descricao.replace(valor, '').strip()
            
            # Último valor = total do item (geralmente)
            valor_item = valores_validos[-1] if valores_validos else None
            
            items.append(Item(
                description=descricao,
                unit_value=valor_item,
                raw=linha
            ))
        else:
            # Sem valor = pode ser descrição longa/continuação
            if len(linha) > 15:
                items.append(Item(description=linha, raw=linha))
    
    return items

def extract_from_text(text: str, source_filename: Optional[str] = None) -> InvoiceExtractionResult:
    """
    Parser principal com validações heurísticas.
    """
    # Extrai e valida dados
    emission, competence = extract_emission_and_competence(text)
    chave_validada = find_key_valid_access(text)
    issuer, recipient = extract_issuer_recipient(text)
    total = extract_total_valid(text)
    items = extract_items(text)
    
    # Monta resultado
    financials = Financials(
        total=total,
        taxes=None,
        payment_method=None
    )
    
    return InvoiceExtractionResult(
        emission_date=emission,
        competence_date=competence,
        chave_acesso=chave_validada["chave_formatada"] if chave_validada else None,
        issuer=issuer,
        recipient=recipient,
        items=items,
        financials=financials,
        raw_text=text,
        source_filename=source_filename
    )