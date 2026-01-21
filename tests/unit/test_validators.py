import pytest
from robot.core.validators import ( 
    cnpj_validator, 
    monetari_value_validator, 
    nfe_key_validator,
    validator_valor_fiscal_brasileiro
)

def pytest_configure(config):
    """Registra markers customizados para evitar warnings."""
    config.addinivalue_line(
        "markers", "validation: Testes de validação de dados"
    )
    config.addinivalue_line(
        "markers", "audit: Testes para auditoria fiscal"
    )
    config.addinivalue_line(
        "markers", "integration: Testes de integração entre componentes"
    )
    config.addinivalue_line(
        "markers", "event_source: Testes de event sourcing e rastreabilidade"
    )

# CNPJ

@pytest.mark.validation
@pytest.mark.audit
@pytest.mark.parametrize(
    "cnpj_input,esperado",
    [
        ("12.345.678/0001-00", "checksum"),
        ("45.123.456/0003-99", "checksum"),
        ("00.394.460/0058-77", "checksum"),
        ("123456780001", "length"),
        ("45.123.4560003", "length"),
        ("003944600058", "length"),
        ('11.111.111/1111-11', "repetition")
    ],
)

def test_cnpj_invalid_checksum(cnpj_input, esperado): ##  falha de checksum
    result = cnpj_validator(cnpj_input)

    assert result["valido"] is False
    assert result["confianca"] >= 90

    erro_lower = result["erro"].lower()
    if esperado == "checksum":
        assert any( term in erro_lower for term in ("dígito", "verificador")) 
    elif esperado == "length":
        assert "14 dígitos" in result["erro"]
    elif esperado == "repetition":
        assert "dígitos repetidos" in erro_lower or "repetido" in erro_lower

@pytest.mark.validation
def test_cnpj_valid_example():
    cnpj = "04.252.011/0001-10"  ## CNPJ válido de exemplo da Receita Federal

    result = cnpj_validator(cnpj)

    assert result["valido"] is True
    assert result["cnpj_limpo"] == "04252011000110"
    assert result["cnpj_formatado"] == "04.252.011/0001-10"
    assert result["tipo"] in {"matriz", "filial"}
    assert result["confianca"] == 95

@pytest.mark.validation
@pytest.mark.parametrize(
    "cnpj_input",
    [
        "11.222.333/0001-81", # matriz válida
        "33.000.167/0001-01", # INSS válido 
    ],
)
def test_cnpj_valid_multiple(cnpj_input):
    result = cnpj_validator(cnpj_input)

    assert result["valido"] is True

    pass

@pytest.mark.validation
@pytest.mark.parametrize(
    "value_input,erro_esperado",
    [
        ("400,0a", "formato"),
        ("R$ -1234,56", "negativo"),
        ("one thousand","formato"),
        ("€ 99,99.99", "decimais"),
        ("¥ ", "formato"),
        ("USD twelve", "formato"), 
        ("", "formato"),
        ("abc", "formato"),
    ],
)
def test_monetary_values_invalid(value_input, erro_esperado):
    result = monetari_value_validator(value_input)

    assert result["valido"] is False
    assert result["confianca"] >= 80

    erro_lower = result["erro"].lower()
    assert erro_esperado in erro_lower

@pytest.mark.validation
@pytest.mark.parametrize(
    "value_input,moeda_esperada,valor_esperado",
    [
        ("400,00", "BRL", 400.00),     
        ("R$ 1.234,56", "BRL", 1234.56),
        ("$ 1200.50", "USD", 1200.50),
        ("€ 999,99", "EUR", 999.99),
        ("¥ 100000", "JPY", 100000.00),
        ("USD 1234.56", "USD", 1234.56),
        ("£ 500.25", "GBP", 500.25),
    ],
)
def test_monetary_values_multimoeda_valid(value_input, moeda_esperada, valor_esperado):
    result = monetari_value_validator(value_input)

    assert result["valido"] is True
    assert result["moeda"] == moeda_esperada
    assert float(result["valor_decimal"]) == valor_esperado
    assert result["confianca"] == 95

# TESTES DE CONTEXTO FISCAL BRASILEIRO

@pytest.mark.validation
@pytest.mark.audit
@pytest.mark.parametrize(
    "value_input",
    [
        "USD 1,000.00",
        "€ 500.50",
        "¥ 100000",
    ],
)
def test_monetary_values_fiscal_rejeitad_estrangeiro(value_input):
    """
    Em contexto FISCAL BRASILEIRO, deve REJEITAR moedas estranjeiras
    """
    result = monetari_value_validator(
        value_input,
        fiscal_context=True
    )

    assert result["valido"] is False
    assert "fiscal" in result["erro"].lower() or "real" in result["erro"].lower()
    assert result["confianca"] == 100
    assert result["moeda_detectada"] != "BRL"

@pytest.mark.validation
@pytest.mark.audit
def test_helper_validar_valor_fiscal_brasileiro():

    result_brl = validator_valor_fiscal_brasileiro("R$ 15.750,75")
    assert result_brl["valido"] is True
    assert result_brl["moeda"] == "BRL"

    result_usd = validator_valor_fiscal_brasileiro("USD 1,000.00")
    assert result_usd["valido"] is False
    assert "fiscal" in result_usd["erro"].lower()

# TESTES DE MOEDA ESPERADA

@pytest.mark.validation
def test_monetary_moeda_esperada_match():
    """Quando moeda_esperada bate, deve validar"""
    result = monetari_value_validator(
        "$ 1000.00",
        moeda_esperada="USD"
    )

    assert result["valido"] is True
    assert result["moeda"] == "USD"
    assert result["fiscal_brasil"] is False

@pytest.mark.validation
def test_monetary_moeda_esperada_mismatch():
    """Quando moeda_esperada não bate, deve rejeitar"""
    result = monetari_value_validator("€ 500.00", moeda_esperada="USD")
    
    assert result["valido"] is False
    assert "esperada USD" in result["erro"]
    assert result["moeda_detectada"] == "EUR"

# EDGE CASE

@pytest.mark.validation
def test_monatary_decimais_cases_extra():
    
    result = monetari_value_validator("R$ 100,099")  

    assert result["valido"] is False
    assert "decimais" in result["erro"].lower()

# Chave NF-e

@pytest.mark.validation
@pytest.mark.audit
def test_nfe_key_invalid_length():
    key = "351902123456780001955500100000000000000000"

    result = nfe_key_validator(key)

    assert result["valido"] is False
    assert "44 dígitos" in result["erro"]

@pytest.mark.validation
def test_nfe_key_invalid_cnpj_inside():
    key = "35190212345678000195550010000000000000000044"

    result = nfe_key_validator(key)

    assert result["valido"] is False
    assert any(
        term in result["erro"].lower()
        for term in ("cnpj", "dígito", "inválido")
    )

@pytest.mark.validation
def test_nfe_key_invalid_dv():
    """Falha no dígito verificador ( DV = 0 incorreto )"""
    key="35241204252011000110550010000012345012345678"

    result = nfe_key_validator(key)

    assert result["valido"] is False
    assert "dígito verificador" in result["erro"].lower()


@pytest.mark.integration
def test_pipeline_nfe_completa():
    """
    Simula validação completa de uma NF-e:
    - CNPJ do emitente
    - Chave de acesso
    - Valor total
    """
    cnpj_emitente = "04.252.011/0001-10"
    chave_nfe = "35241204252011000110550010000012345012345678"
    valor_total = "R$ 15.750,00" 

    cnpj_result = cnpj_validator(cnpj_emitente)
    assert cnpj_result["valido"] is True
    assert cnpj_result["confianca"] == 95
    
    valor_result = validator_valor_fiscal_brasileiro(valor_total)
    assert valor_result ["valido"] is True
    assert valor_result ["moeda"] == "BRL"
    assert valor_result ["fiscal_brasil"] is True

    chave_result = nfe_key_validator(chave_nfe)
# TESTES DE EVENT SOURCING / AUDITORIA

@pytest.mark.audit
@pytest.mark.event_source
def test_validator_retorna_confianca():
    """
    Para event sourcing, todos validators devem retornar nível de confiança.
    """
    cnpj_result = cnpj_validator("04.252.011/0001-10")
    valor_result = monetari_value_validator("R$ 1000,00")
    
    assert "confianca" in cnpj_result
    assert "confianca" in valor_result
    assert 0 <= cnpj_result["confianca"] <= 100
    assert 0 <= valor_result["confianca"] <= 100


@pytest.mark.audit
def test_validator_rastreabilidade():
    """
    Validators devem manter dados originais para auditoria.
    """
    valor_original = "$ 1,234.56"
    result = monetari_value_validator(valor_original)
    
    assert "moeda" in result
    assert result["moeda"] == "USD"
    
    if result["valido"]:
        assert "valor_decimal" in result
        assert "valor_formatado" in result
        assert result["fiscal_brasil"] is False
    else:
        assert "erro" in result

@pytest.mark.audit
@pytest.mark.event_source
def test_event_auditoria_fiscal():
    """
    Simula geração de evento de auditoria com todos metadados
    """
    import json
    from datetime import datetime

    cnpj = "04.252.011/0001-10"
    valor = "R$ 15.750,00"

    cnpj_result = cnpj_validator(cnpj)
    valor_result = validator_valor_fiscal_brasileiro(valor)

    evento = {
        "tipo": "validacao_documento_fiscal",
        "timestamp": datetime.now().isoformat(),
        "validacoes": {
            "cnpj": {
                "valido": cnpj_result["valido"],
                "confianca": cnpj_result["confianca"],
                "cnpj_formatado": cnpj_result.get("cnpj_formatado")
            },
            "valor": {
                "valido": valor_result["valido"],
                "confianca": valor_result["confianca"],
                "moeda": valor_result.get("moeda"),
                "fiscal_brasil": valor_result.get("fiscal_brasil")
            }
        },
        "resultado": "aprovado" if all([
            cnpj_result["valido"],
            valor_result["valido"]
        ]) else "rejeitado"
    }
    
    # Valida estrutura do evento
    assert evento["resultado"] in ["aprovado", "rejeitado"]
    assert "timestamp" in evento
    assert "validacoes" in evento
    
    # Evento deve ser serializável para Redis Streams
    evento_json = json.dumps(evento, default=str)
    assert len(evento_json) > 0