from robot.core.parser import (
    extract_blocks, 
    clean_party_name, 
    extract_from_text,
    extract_party_from_block
)

def test_clean_party_name_filters_generics():
    """Testa se clean_party_name rejeita nomes genéricos da lista proibida."""
    # Casos que devem ser rejeitados (None)
    assert clean_party_name("DO SERVIÇO") is None
    assert clean_party_name("PRESTADOR DO SERVIÇO") is None
    assert clean_party_name("TOMADOR") is None
    assert clean_party_name("DADOS DO TOMADOR") is None
    assert clean_party_name("CNPJ / CPF") is None # Contém CNPJ e CPF que são tokens invalidos
    
    # Casos que devem ser aceitos normalizados
    assert clean_party_name("Empresa Real LTDA") == "EMPRESA REAL LTDA"
    assert clean_party_name("DO SERVIÇO SOLUCOES") == "DO SERVIÇO SOLUCOES" # Tem tokens válidos "SOLUCOES"
    assert clean_party_name("PRESTADOR SERVICOS TI S.A.") == "PRESTADOR SERVICOS TI S.A"

def test_extract_blocks_segmentation():
    """Testa se o texto é fatiado corretamente nos blocos."""
    texto = """
    PREFEITURA MUNICIPAL DE X
    
    PRESTADOR DO SERVIÇO
    EMPRESA OK
    CNPJ: 00.000.000/0000-00
    
    TOMADOR DO SERVIÇO
    CLIENTE OK
    
    DISCRIMINAÇÃO DOS SERVIÇOS
    Item 1 R$ 100,00
    
    VALOR TOTAL DA NOTA
    R$ 100,00
    """
    
    blocks = extract_blocks(texto)
    
    assert "EMPRESA OK" in blocks["ISSUER"]
    assert "CLIENTE OK" in blocks["RECIPIENT"]
    assert "Item 1" in blocks["ITEMS"]
    assert "R$ 100,00" in blocks["FINANCIALS"]
    
    # Garante que um bloco não invade o outro (ex: Tomador não tem dados do Prestador)
    assert "EMPRESA OK" not in blocks["RECIPIENT"]

def test_real_pdf_block_priority():
    """
    Simula caso real onde 'PRESTADOR DO SERVIÇO' aparece antes do nome.
    A lógica antiga pegava 'PRESTADOR DO SERVIÇO' como nome se estivesse na primeira linha capturada.
    A nova deve filtrar isso.
    """
    texto = """
    EMITENTE DA NFS-e
    Prestador do Serviço
    CNPJ / CPF / NIF
    53.601.438/0001-91
    
    Nome / Nome Empresarial
    PEST COMBAT GESTAO AMBIENTAL LTDA
    
    Endereço
    RUA X, 123
    """
    
    # Extrai apenas o bloco issuer manualmente para teste unitario da funcao
    blocks = extract_blocks(texto)
    issuer_block = blocks["ISSUER"]
    
    party = extract_party_from_block(issuer_block)
    
    assert party is not None
    assert party.name == "PEST COMBAT GESTAO AMBIENTAL LTDA"
    assert party.name != "PRESTADOR DO SERVIÇO"
    assert party.name != "EMITENTE DA NFS-E"

def test_full_extraction_orchestration():
    """Testa o fluxo completo via extract_from_text."""
    texto = """
    EMITENTE
    EMPRESA TOP
    CNPJ: 11.111.111/0001-11
    
    DESTINATÁRIO
    CLIENTE TOP
    CNPJ: 22.222.222/0001-22
    
    DISCRIMINAÇÃO DOS SERVIÇOS
    Servico 1 R$ 500,00
    
    TOTAL GERAL
    R$ 500,00
    """
    
    result = extract_from_text(texto)
    
    assert result.issuer.name == "EMPRESA TOP"
    assert result.recipient.name == "CLIENTE TOP"
    assert len(result.items) == 1
    assert result.financials.total == "R$ 500,00"
