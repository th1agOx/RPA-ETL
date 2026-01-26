📌 Contrato interno (Parser → Validators)

Exemplo (ilustrativo):

ParsedFiscalDocument = {
  "emission_date": str,   # "DD/MM/YYYY HH:MM:SS"
  "cnpj_emissor": str,
  "total_bruto": str,     # string monetária normalizada
  "itens": list[dict],
}


Regra:

Parser só extrai e organiza

Validators só validam e anotam confiança

Parser NÃO converte para float

Validators NÃO reformatam texto