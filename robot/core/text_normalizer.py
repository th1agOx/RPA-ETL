import re
from typing import List

CLEAN_REPLACEMENTS = [     
    ('\xa0', ' '),
    ('\u200b', ''),
    ('\r\n', '\n'),
]

def normalize_whitespace(text: str) -> str: ##     Eliminar espaços em branco preserva quebras de linha (Universal)
    text = re.sub(r'[ \t\f\v]+', ' ', text)
    
    text = re.sub(r'\n{2,}', '\n\n', text)  

    return text.strip()

def join_split_numbers(text: str) -> str: ##     Junta de forma conservadora pequenos tokens separadas (Sequencial Character)
    text = re.sub(r'(?<=\d)\s+(?=\d)', '', text) 

    return text

def normalize_commas_and_dots(text: str) -> str: ##     Identação de valore monetário & pontos extras entre decimais (Heurística)  
    
    text = re.sub(r'(\d)\s*,\s*(\d{2})', r'\1,\2', text)
    
    text = re.sub(r'(?<=\d)\s*\.\s*(?=\d{3}\b)', '', text)

    return text

def strip_lines_noise(lines: List[str]) -> List[str]: ##     Filtra linhas não-informativas
    out = []
    siglas_validas = {
        'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA',
        'MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN',
        'RS','RO','RR','SC','SP','SE','TO',
        'NF','RG','IE','IM','CPF'
    }
    
    for ln in lines:
        ln_strip = ln.strip()

        if ln_strip.upper() in siglas_validas:
            out.append(ln_strip)
            continue

        if len(ln_strip) < 3 and not re.search(r'\d', ln_strip):
            continue
        out.append(ln_strip)

    return out

def fix_date_spacing(text: str) -> str: 
    """
    Garante espaço entre data e hora quando coladas pelo processo de normalização.
    Ex: 15/12/202410:30:00 -> 15/12/2024 10:30:00
    """
    return re.sub(
        r'(\d{2}/\d{2}/\d{4})(\d{2}:\d{2}:\d{2})',
        r'\1 \2',
        text
    )

def normalize_text(text: str) -> str: 
    if not isinstance(text, str ):
        raise TypeError(
            f"normalize_text espera receber uma string, mas recebeu {type(text).__name__}"
        )
         
    for pat, repl in CLEAN_REPLACEMENTS:
        text = text.replace(pat, repl)

    text = normalize_whitespace(text)

    text = join_split_numbers(text)

    text = fix_date_spacing(text)
    
    text = normalize_commas_and_dots(text)

    lines = text.splitlines()
    
    lines = strip_lines_noise(lines)

    seen = set()
    dedup_lines = []
    for l in lines:
        if l in seen:
            continue
        dedup_lines.append(l)
        seen.add(l)

    return "\n".join(dedup_lines)