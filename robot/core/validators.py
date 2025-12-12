import re
from typing import Dict, List

def cnpj_validator(cnpj: str) -> Dict[str, any]: ##     VALIDAÇÃO DE CNPJ COM CHECKSUM
    """
    Valida CNPJ com checksum
    Retorna dict com status e metadados.
    """
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    
    if len(cnpj_limpo) != 14:
        return {
            "valido": False,
            "erro": f"CNPJ deve ter 14 dígitos (recebido {len(cnpj_limpo)})",
            "confianca": 100
        }
    
    # Camada 2: Padrão inválido (todos dígitos iguais)
    if cnpj_limpo == cnpj_limpo[0] * 14:
        return {
            "valido": False,
            "erro": "CNPJ com todos dígitos repetidos",
            "confianca": 100
        }
    
    # Camada 3: Checksum (algoritmo oficial da Receita)
    def calcular_digito(base: str, pesos: List[int]) -> int:
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto
    
    # Valida primeiro dígito verificador
    pesos_1 = [5,4,3,2,9,8,7,6,5,4,3,2]
    dv1 = calcular_digito(cnpj_limpo[:12], pesos_1)
    
    if int(cnpj_limpo[12]) != dv1:
        return {
            "valido": False,
            "erro": f"Dígito verificador 1 incorreto (esperado {dv1})",
            "confianca": 99
        }
    
    # Valida segundo dígito verificador
    pesos_2 = [6,5,4,3,2,9,8,7,6,5,4,3,2]
    dv2 = calcular_digito(cnpj_limpo[:13], pesos_2)
    
    if int(cnpj_limpo[13]) != dv2:
        return {
            "valido": False,
            "erro": f"Dígito verificador 2 incorreto (esperado {dv2})",
            "confianca": 99
        }
    
    # Passou em todas validações
    return {
        "valido": True,
        "cnpj_limpo": cnpj_limpo,
        "cnpj_formatado": f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}",
        "tipo": "matriz" if cnpj_limpo[8:12] == "0001" else "filial",
        "confianca": 95  # Não consultou Receita Federal
    }

# VALIDAÇÃO DE CHAVE NF-e

def nfe_key_validator(chave: str) -> Dict[str, any]:
    """
    Valida chave de acesso NF-e (44 dígitos).
    Estrutura: UF(2) + AAMM(4) + CNPJ(14) + Modelo(2)
    """
    chave_limpa = re.sub(r'\D', '', chave)
    
    # Camada 1: Tamanho
    if len(chave_limpa) != 44:
        return {
            "valido": False,
            "erro": f"Chave deve ter 44 dígitos (recebido {len(chave_limpa)})",
            "confianca": 100
        }
    
    # Camada 2: Estrutura dos campos
    uf = chave_limpa[:2]
    ano_mes = chave_limpa[2:6]
    cnpj = chave_limpa[6:20]
    modelo = chave_limpa[20:22]
    dv = chave_limpa[43]
    
    # UF válida (códigos IBGE)
    ufs_validas = {
        '11','12','13','14','15','16','17',  # Norte
        '21','22','23','24','25','26','27','28','29',  # Nordeste
        '31','32','33','35',  # Sudeste
        '41','42','43',  # Sul
        '50','51','52','53'  # Centro-Oeste
    }
    
    if uf not in ufs_validas:
        return {
            "valido": False,
            "erro": f"Código UF inválido: {uf}",
            "confianca": 100
        }
    
    # Camada 3: Plausibilidade temporal
    try:
        ano = int(ano_mes[:2])
        mes = int(ano_mes[2:4])
        
        ano_completo = 2000 + ano if ano >= 8 else 2100 + ano
        
        if not (2008 <= ano_completo <= 2030):
            return {
                "valido": False,
                "erro": f"Ano implausível: {ano_completo}",
                "confianca": 95
            }
        
        if not (1 <= mes <= 12):
            return {
                "valido": False,
                "erro": f"Mês inválido: {mes:02d}",
                "confianca": 100
            }
    except ValueError:
        return {
            "valido": False,
            "erro": "Data malformada na chave",
            "confianca": 100
        }
    
    # Camada 4: Modelo de documento
    if modelo not in ['55', '65']:
        return {
            "valido": False,
            "erro": f"Modelo inválido: {modelo} (esperado 55=NF-e ou 65=NFC-e)",
            "confianca": 95
        }
    
    # Camada 5: Valida CNPJ embutido
    validacao_cnpj = cnpj_validator(cnpj)
    if not validacao_cnpj["valido"]:
        return {
            "valido": False,
            "erro": f"CNPJ inválido na chave: {validacao_cnpj['erro']}",
            "confianca": 99
        }
    
    # Camada 6: Dígito verificador (módulo 11)
    def calcular_dv_nfe(chave_43: str) -> int:
        pesos = [4,3,2,9,8,7,6,5,4,3,2,9,8,7,6,5,4,3,2,9,8,7,6,5,4,3,2,9,8,7,6,5,4,3,2,9,8,7,6,5,4,3,2]
        soma = sum(int(d) * p for d, p in zip(chave_43, pesos))
        resto = soma % 11
        return 0 if resto in [0, 1] else 11 - resto
    
    dv_calculado = calcular_dv_nfe(chave_limpa[:43])
    
    if int(dv) != dv_calculado:
        return {
            "valido": False,
            "erro": f"Dígito verificador incorreto (esperado {dv_calculado}, recebido {dv})",
            "confianca": 99
        }
    
    # Passou em todas validações!
    return {
        "valido": True,
        "chave_limpa": chave_limpa,
        "chave_formatada": f"{chave_limpa[:4]} {chave_limpa[4:8]} {chave_limpa[8:12]} {chave_limpa[12:16]} {chave_limpa[16:20]} {chave_limpa[20:24]} {chave_limpa[24:28]} {chave_limpa[28:32]} {chave_limpa[32:36]} {chave_limpa[36:40]} {chave_limpa[40:44]}",
        "uf": uf,
        "ano_mes": f"{ano_completo}-{mes:02d}",
        "cnpj_emitente": validacao_cnpj["cnpj_formatado"],
        "modelo": "NF-e" if modelo == "55" else "NFC-e",
        "confianca": 90  # Não consultou SEFAZ
    }


# VALIDAÇÃO DE VALORES MONETÁRIOS

def monetari_value_validator(valor: str) -> Dict[str, any]:
    """
    Valida se string é valor monetário plausível.
    Converte para Decimal para evitar float precision.
    """
    from decimal import Decimal, InvalidOperation
    
    valor_limpo = valor.strip().replace('R$', '').replace(' ', '')
    
    if ',' in valor_limpo and '.' in valor_limpo:
    
        valor_limpo = valor_limpo.replace('.', '').replace(',', '.')

    elif ',' in valor_limpo:

        valor_limpo = valor_limpo.replace(',', '.')
    
    try:
        valor_decimal = Decimal(valor_limpo)

    except InvalidOperation:
        return {
            "valido": False,
            "erro": f"Não é um número válido: {valor}",
            "confianca": 100
        }
    
    # Heurísticas de plausibilidade
    if valor_decimal < 0:
        return {
            "valido": False,
            "erro": "Valor negativo",
            "confianca": 100
        }
    
    if valor_decimal > Decimal('1000000000'): 
        return {
            "valido": False,
            "erro": f"Valor absurdo: R$ {valor_decimal:,.2f}",
            "confianca": 90
        }
    
    # Verifica se tem mais de 2 casas decimais (improvável em NF)
    if valor_decimal != valor_decimal.quantize(Decimal('0.01')):
        return {
            "valido": False,
            "erro": "Mais de 2 casas decimais",
            "confianca": 80
        }
    
    return {
        "valido": True,
        "valor_decimal": valor_decimal,
        "valor_formatado": f"R$ {valor_decimal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        "confianca": 95
    }