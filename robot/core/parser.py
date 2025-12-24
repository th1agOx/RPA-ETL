import re
from typing import List, Optional, Dict, Any
from ..schema.models import InvoiceExtractionResult, Item, Party, Financials
from .validators import(
    cnpj_validator, 
    nfe_key_validator, 
    monetari_value_validator,
    validator_valor_fiscal_brasileiro
)

CNPJ_PATTERN = r'\b\d{2}\.?\d{3}\.?\d{3}/?\.?\d{4}-?\d{2}\b'
KEY_PATTERN = r'\b\d{44}\b'  # nfe key de 44 dígitos
VALUE_PATTERN = r'R?\$?\s*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))'

def normalizer_unicode(text: str) -> str:
    try:
        return text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
    except:
        return text

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
    """
    Extrai datas de emissão e competência separadamente.
    busca COMPETÊNCIA em formatos MM/YYYY ou MM-YYYY
    FALLBACK independente para cada campo
    """
    emission = None
    competence = None

    pattern_emission = [
        r'EMISS[AÃ]O.*?(\d{2}/\d{2}/\d{4}(?:\s*\d{2}:\d{2}:\d{2})?)',
        r'DATA\s+DE\s+EMISS[AÃ]O.*?(\d{2}/\d{2}/\d{4})',    
    ]

    for pattern in pattern_emission:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            emission = m.group(1)
        break

        # Fallback: primeira data DD/MM/YYYY encontrada
    if not emission:
        m = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        emission = m.group(1) if m else None
    
    pattern_competence = [
        r'COMPET[EÊ]NCIA.*?(\d{2}/\d{4})',
        r'COMPET[EÊ]NCIA.*?(\d{2}/\d{2}/\d{4})'
        r'COMPET[EÊ]NCIA.*?(\d{2}-\d{4})'
    ]

    for pattern in pattern_competence:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            competence = m.group(1)
            break
    
    return emission, competence

def extract_total_valid(text: str) -> Optional[str]:
    """
    Busca valor após palavras-chave de total.
    
    CORREÇÕES:
    1. Aceita valores SEM "R$" explícito
    2. Valida plausibilidade via monetari_value_validator
    3. Ignora "TOTAL DE ITENS" (quantidade)
    4. Retorna sempre formatado: "R$ X.XXX,XX" 
    """
    patterns = [
        r'TOTAL\s+GERAL\s*:?\s*R?\$?\s*([\d\.,]+)',
        r'VALOR\s+L[IÍ]QUIDO\s*:?\s*R?\$?\s*([\d\.,]+)',
        r'VALOR\s+TOTAL\s*:?\s*R?\$?\s*([\d\.,]+)',

        r'TOTAL\s*:?\s*R?\$?\s*([\d\.,]+)', 
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidato = m.group(1)
            validacao = monetari_value_validator(candidato, fiscal_context=True)
            
            if validacao["valido"]:
                # Retorna valor formatado (sempre "R$ X.XXX,XX")
                return validacao["valor_formatado"]
            
            continue
    
    return None

# EXTRAÇÃO DE PRESTADOR/TOMADOR

def extract_issuer_recipient(text: str) -> tuple:
    """
    Extrai dados do PRESTADOR e TOMADOR.

    CORREÇÕES:
    1. Normaliza Unicode antes de processar
    2. Pega PRIMEIRA ocorrência (ignora duplicatas)
    3. Valida CNPJs encontrados
    4. Robustez em blocos ausentes/malformados
   
    """
    text = normalizer_unicode(text)

    issuer = None
    recipient = None

    # PRESTADOR
    patterns_issuer = [
        r'PRESTADOR(?:\s+DE\s+SERVI[CÇ]OS)?\s*(.*?)\s*(?:TOMADOR|DISCRIMINA[CÇ]|$)',
        r'EMITENTE\s*(.*?)\s*(?:DESTINAT[AÁ]RIO|DISCRIMINA[CÇ]|$)', 
    ]

    for pattern in patterns_issuer:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            issuer_block = m.group(1).strip()
            lines = [l.strip() for l in issuer_block.splitlines() if l.strip()]

            # Primeira linha = nome
            issuer_name = lines[0].strip() if lines else None

            # Busca CNPJ válido no bloco
            valid_cnpjs = find_cnpjs(issuer_block)
            provider_cnpj = valid_cnpjs[0]["cnpj_formatado"] if valid_cnpjs else None

            issuer = Party(name=issuer_name, cnpj_cpf=provider_cnpj)
            break

        # TOMADOR / DESTINATÁRIO

    patterns_recipient = [
        r'TOMADOR(?:\s+DE\s+SERVI[CÇ]OS)?\s*(.*?)(?:DISCRIMINA[CÇ]|SERVI[CÇ]OS|OBSERVA[CÇ]|$)',
        r'DESTINAT[AÁ]RIO\s*(.*?)(?:DISCRIMINA[CÇ]|PRODUTOS|OBSERVA[CÇ]|$)',
    ]

    for pattern in patterns_recipient:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            recipient_block = m.group(1).strip()
            lines = [l.strip() for l in recipient_block.splitlines() if l.strip()]

            # Primeira linha = nome
            recipient_name = lines[0] if lines else None

            # Busca CNPJ válido no bloco
            valid_cnpjs = find_cnpjs(recipient_block)
            recipient_cnpj = valid_cnpjs[0]["cnpj_formatado"] if valid_cnpjs else None

            recipient = Party(name=recipient_name, cnpj_cpf=recipient_cnpj)
            break

    return issuer, recipient

def extract_items(text: str) -> List[Item]:
    """
    Extrai itens da seção DISCRIMINAÇÃO.
    
    CORREÇÕES PRINCIPAIS:
    1. Detecta bloco DISCRIMINAÇÃO corretamente
    2. Para quando encontra TOTAL/OBSERVAÇÕES
    3. Ignora linhas < 10 caracteres
    4. Remove valores da descrição
    5. Identifica item SE contém valor monetário válido
    """
    items = []
    
    # ============================================
    # FASE 1: ENCONTRAR BLOCO DE ITENS
    # ============================================
    patterns_block = [
        r'DISCRIMINA[CÇ][AÃ]O(?:\s+DOS\s+SERVI[CÇ]OS)?\s*(.*?)\s*(?:TOTAL\s+GERAL|VALOR\s+TOTAL|VALOR\s+L[IÍ]QUIDO|OBSERVA[CÇ]|$)',
        r'DISCRIMINA[CÇ][AÃ]O(?:\s+DOS\s+PRODUTOS)?\s*(.*?)\s*(?:TOTAL|OBSERVA[CÇ]|$)',
    ]
    
    items_block = None
    for pattern in patterns_block:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            items_block = m.group(1).strip()
            break
    
    if not items_block:
        return items
    
    for linha in items_block.splitlines():
        linha = linha.strip()
        
        # Ignora linhas vazias ou muito curtas
        if not linha or len(linha) < 10:
            continue       

        valores = re.findall(VALUE_PATTERN, linha)
        
        # Valida cada valor encontrado
        valores_validos = []
        for valor in valores:
            validacao = monetari_value_validator(valor, fiscal_context=True)
            if validacao["valido"]:
                valores_validos.append(valor)
        

        if valores_validos:
            # Linha TEM valor → é item válido
            
            # Remove valores para extrair descrição limpa
            descricao = linha
            for valor in valores_validos:
                descricao = descricao.replace(valor, '').strip()
            
            # Remove também "R$" soltos
            descricao = re.sub(r'R\$\s*', '', descricao).strip()
            
            # Último valor = total do item (convenção NF-e)
            valor_item = valores_validos[-1]
            
            items.append(Item(
                description=descricao,
                unit_value=valor_item,
                raw=linha
            ))
        
        else:
            # Linha SEM valor → pode ser descrição longa/continuação
            # Só adiciona se tiver conteúdo relevante (> 15 chars)
            if len(linha) > 15:
                items.append(Item(
                    description=linha,
                    unit_value=None,
                    raw=linha
                ))
    
    return items

def extract_from_text(text: str, source_filename: Optional[str] = None) -> InvoiceExtractionResult:
    """
    Parser principal com validações heurísticas.

    Pipeline:
    1. Normliza Unicode
    2. Extrai daddos com fallbacks
    3. Valida cada campo
    4. Retorna schema estruturado
    """
    text = normalizer_unicode(text)

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