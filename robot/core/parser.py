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

import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

INVALID_NAME_TOKENS = {
    "DO", "DE", "DA", "DOS", "DAS", "SERVICO", "SERVICOS", "PRODUTO", "PRODUTOS",
    "DO", "DE", "DA", "DOS", "DAS", "SERVICO", "SERVICOS", "PRODUTO", "PRODUTOS",
    "PRESTADOR", "TOMADOR", "EMITENTE", "DESTINATARIO",
    "CNPJ", "CPF", "DADOS", "MUNICIPAL", "SECRETARIA", "FAZENDA", "PREFEITURA",
    "NOTA", "FISCAL", "ELETRONICA", "NFSE", "NFE", "NFS-E",
    "NOME", "RAZAO", "SOCIAL", "ENDERECO", "MUNICIPIO", "UF",
    "EMPRESARIAL", "NIF", "INSCRICAO", "ESTADUAL"
}

def clean_party_name(name: str) -> Optional[str]:
    """
    Normaliza nome de Entidades:
    1. Uppercase
    2. Remove espaços extras
    3. Remove pontuação solta no fim
    4. Rejeita se conter APENAS tokens inválidos
    """
    if not name:
        return None
    
    # Remove espaços multiplos e quebras
    name = re.sub(r'\s+', ' ', name)
    
    # Uppercase para padronização
    name = name.upper().strip()
    
    # Remove hífens ou pontos soltos no final (resíduo comum de OCR)
    name = re.sub(r'[\.\-\,]+$', '', name)
    
    name = name.strip()
    if not name:
        return None

    # Validação Semântica: Rejeita labels genéricos
    # Normaliza para comparação (remove acentos)
    name_normalized = remove_accents(name)
    
    # Se todas as palavras significativas do nome estão na lista proibida, descarta
    tokens = [t for t in name_normalized.split() if len(t) > 2] # Ignora 'DA', 'DE', 'O' curtos
    
    if not tokens: # Só tinha stopwords
        return None
        
    is_invalid = all(t in INVALID_NAME_TOKENS for t in tokens)
    if is_invalid:
        return None
        
    return name

def normalizer_unicode(text: str) -> str:
    try:
        return text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
    except:
        return text

def find_key_valid_access(text: str) -> Optional[Dict[str, Any]]:
    # Chave pode estar em qualquer lugar (cabeçalho, rodapé)
    extrations = re.findall(KEY_PATTERN, text)
    for extration in extrations:
        validation = nfe_key_validator(extration)
        if validation["valido"]:
            return validation
    return None

def find_cnpjs(text: str) -> List[Dict[str, Any]]:
    extrations = re.findall(CNPJ_PATTERN, text)
    cnpjs_valid = []
    for extration in extrations:
        validation = cnpj_validator(extration)
        if validation["valido"]:
            cnpjs_valid.append(validation)
    return cnpjs_valid

def extract_emission_and_competence(text: str) -> tuple:
    # Datas podem estar espalhadas, mantém busca global ou restrita a HEADER se tivessemos
    # Por hora, mantém global pois datas são menos ambíguas que nomes
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
    if not emission:
        m = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        emission = m.group(1) if m else None
    
    pattern_competence = [
        r'COMPET[EÊ]NCIA.*?(\d{2}/\d{4})',
        r'COMPET[EÊ]NCIA.*?(\d{2}/\d{2}/\d{4})',
        r'COMPET[EÊ]NCIA.*?(\d{2}-\d{4})'
    ]

    for pattern in pattern_competence:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            competence = m.group(1)
            break
    
    return emission, competence

# ==============================================================================
#  BLOCK SEGMENTATION STRATEGY
# ==============================================================================

def extract_blocks(text: str) -> Dict[str, str]:
    """
    Fatia o texto em blocos semânticos baseados em headers conhecidos.
    Estratégia:
    1. Encontrar posições de inicio de cada seção conhecida.
    2. Ordenar cabeçalhos por posição.
    3. Fatiar texto entre header_atual e proximo_header.
    """
    
    # Definição de marcadores de início de bloco
    markers = {
        "ISSUER": [r'PRESTADOR\s+(?:DO|DE)?\s*SERVI[CÇ]O', r'DADOS\s+DO\s+PRESTADOR', r'EMITENTE'],
        "RECIPIENT": [r'TOMADOR\s+(?:DO|DE)?\s*SERVI[CÇ]O', r'DADOS\s+DO\s+TOMADOR', r'DESTINAT[AÁ]RIO'],
        "ITEMS": [r'DISCRIMINA[CÇ][AÃ]O\s+(?:DOS|DE)?\s*(?:SERVI[CÇ]OS|PRODUTOS)', r'DESCRI[CÇ][AÃ]O\s+DOS\s+SERVI[CÇ]OS'],
        "FINANCIALS": [r'VALOR\s+TOTAL', r'TOTAL\s+GERAL', r'TRIBUTA[CÇ][AÃ]O', r'TOTAL\s+DO\s+SERVI[CÇ]O']
    }
    
    # Encontrar todas as ocorrências
    found_headers = [] # (pos, type, match_text)
    
    for block_type, patterns in markers.items():
        for pat in patterns:
            # Usa finditer para pegar todas ocorrências
            for m in re.finditer(pat, text, re.IGNORECASE):
                found_headers.append((m.start(), block_type))
    
    # Ordena por posição no texto
    found_headers.sort(key=lambda x: x[0])
    
    blocks = {
        "ISSUER": "",
        "RECIPIENT": "",
        "ITEMS": "",
        "FINANCIALS": "",
        "HEADER": "" # O que vem antes do primeiro bloco conhecido
    }
    
    # Se não achou nada, retorna tudo vazio (ou tudo como HEADER/UNKNOWN)
    if not found_headers:
        blocks["HEADER"] = text
        return blocks
    
    # O que vem antes do primeiro header é Header/Metadados gerais
    first_pos = found_headers[0][0]
    blocks["HEADER"] = text[:first_pos]
    
    total_len = len(text)
    
    for i, (start_pos, block_type) in enumerate(found_headers):
        # O fim deste bloco é o inicio do próximo header, ou fim do texto
        if i + 1 < len(found_headers):
            end_pos = found_headers[i+1][0]
        else:
            end_pos = total_len
            
        # Extrai conteúdo (incluindo ou não o próprio header? Vamos incluir para contexto regex se precisar, 
        # mas idealmente o regex interno deve ignorar o header. Vamos incluir.)
        # Mas para "extract_name", ter o header "PRESTADOR" atrapalha? 
        # Sim, atrapalha se pegarmos a linha 0. MELHOR: Pular o tamanho do match?
        # A lógica antiga usava regex que consumia o header. Vamos passar o bloco todo.
        
        content = text[start_pos:end_pos]
        
        # Concatena se houver múltiplos blocos do mesmo tipo (raro mas possível, ex: itens quebrados)
        # Para Prestador/Tomador, geralmente só vale o primeiro, mas vamos concatenar por segurança
        # ou melhor: manter o PRIMEIRO bloco achado de cada tipo costuma ser o principal.
        # SE já tem conteudo, talvez seja melhor não sujar.
        # No caso do usuário: "EMITENTE DA NFS-e" apareceu depois.
        # Vamos concatenar com quebra de linha.
        if blocks[block_type]:
            blocks[block_type] += "\n" + content
        else:
            blocks[block_type] = content

    return blocks

# ==============================================================================
#  BLOCK-BASED EXTRACTORS
# ==============================================================================

def extract_party_from_block(block_text: str) -> Optional[Party]:
    """
    Extrai nome e CNPJ de um bloco de texto JÁ ISOLADO (ex: Bloco Prestador).
    Não busca headers globais, assume que o texto é focado.
    """
    if not block_text or not block_text.strip():
        return None
        
    lines = [l.strip() for l in block_text.splitlines() if l.strip()]
    if not lines:
        return None
        
    # Busca CNPJ primeiro para ter certeza da entidade
    valid_cnpjs = find_cnpjs(block_text)
    cnpj = valid_cnpjs[0]["cnpj_formatado"] if valid_cnpjs else None
    
    # Nome: Tenta heurística posicional
    # Linhas iniciais costumam ser o Header (PRESTADOR DE SERVIÇO)
    # Devemos pular linhas que são headers
    
    candidate_name = None
    for line in lines:
        # Se a linha for apenas um CNPJ, ignora (já foi capturado ou é metadado)
        if cnpj_validator(line)["valido"]:
            continue
            
        cleaned = clean_party_name(line)
        if cleaned:
            candidate_name = cleaned
            break
            
    return Party(name=candidate_name, cnpj_cpf=cnpj)

def extract_items_from_block(block_text: str) -> List[Item]:
    """
    Extrai itens apenas do bloco de itens.
    """
    items = []
    if not block_text:
        return items
        
    for linha in block_text.splitlines():
        linha = linha.strip()
        if not linha or len(linha) < 10:
            continue
            
        # Filtros de metadados ainda úteis
        upper_ln = linha.upper()
        if any(token in upper_ln for token in ["TOTAL", "VALOR", "DATA", "COMPETÊNCIA", "DISCRIMINA"]):
            continue

        valores = re.findall(VALUE_PATTERN, linha)
        valores_validos = []
        for valor in valores:
            validacao = monetari_value_validator(valor, fiscal_context=True)
            if validacao["valido"]:
                valores_validos.append(valor)
        
        if valores_validos:
            descricao = linha
            for valor in valores_validos:
                descricao = descricao.replace(valor, '').strip()
            descricao = re.sub(r'R\$\s*', '', descricao).strip()
            
            # Se sobrou nada de descrição, provavlmente era só uma linha de valores (subtotal?)
            if not descricao:
                continue

            items.append(Item(
                description=descricao,
                unit_value=valores_validos[-1],
                raw=linha
            ))
            # DEBUG
            print(f"DEBUG ITEM: Desc='{descricao}' Val='{valores_validos[-1]}'")
        elif len(linha) > 15:
            # Descrição sem valor (continuação)
            items.append(Item(description=linha, raw=linha))
            # DEBUG
            print(f"DEBUG ITEM CONT: '{linha}'")
            
    return items

def extract_total_from_block(block_text: str) -> Optional[str]:
    """
    Busca total no bloco financeiro.
    """
    if not block_text:
        return None
        
    patterns = [
        r'TOTAL\s+GERAL\s*:?\s*R?\$?\s*([\d\.,]+)',
        r'VALOR\s+L[IÍ]QUIDO\s*:?\s*R?\$?\s*([\d\.,]+)',
        r'VALOR\s+TOTAL\s*:?\s*R?\$?\s*([\d\.,]+)',
        r'TOTAL\s*:?\s*R?\$?\s*([\d\.,]+)', 
        r'R\$\s*([\d\.,]+)' # Match agressivo no final do bloco financeiro
    ]
    
    for pattern in patterns:
        m = re.search(pattern, block_text, re.IGNORECASE)
        if m:
            candidato = m.group(1)
            validacao = monetari_value_validator(candidato, fiscal_context=True)
            if validacao["valido"]:
                return validacao["valor_formatado"]
    return None

def extract_from_text(text: str, source_filename: Optional[str] = None) -> InvoiceExtractionResult:
    """
    Parser principal - Versão Segmentada por Blocos.
    """
    text = normalizer_unicode(text)
    
    # 1. Segmentação
    blocks = extract_blocks(text)
    
    # 2. Extração Scoped (com proteção try/except)
    try:
        emission, competence = extract_emission_and_competence(text) # Global scan ok for dates
    except:
        emission, competence = None, None
        
    try:
        chave_validada = find_key_valid_access(text) # Global scan ok for Key
    except:
        chave_validada = None
        
    try:
        # Extrai do bloco especifico
        issuer = extract_party_from_block(blocks["ISSUER"])
    except:
        issuer = None
        
    try:
        recipient = extract_party_from_block(blocks["RECIPIENT"])
    except:
        recipient = None
        
    try:
        # Tenta bloco financeiro, fallback para itens se vazio (alguns layouts misturam)
        total = extract_total_from_block(blocks["FINANCIALS"])
    except:
        total = None
        
    try:
        items = extract_items_from_block(blocks["ITEMS"])
    except:
        items = []

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