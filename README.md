# RPA-ETL: Inteligência Fiscal & Orquestração de Dados 

![Build Status](https://img.shields.io/github/actions/workflow/status/th1agOx/RPA-ETL/main.yml?branch=main)
![Test Coverage](https://img.shields.io/codecov/c/github/th1agOx/RPA-ETL)
![Version](https://img.shields.io/github/v/release/th1agOx/RPA-ETL?display_name=tag)
![License](https://img.shields.io/github/license/th1agOx/RPA-ETL)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)

> **Engine RPA de nível enterprise**, focado em processamento contábil, auditoria orientada a eventos e extração heurística de documentos fiscais.

---

## 🎯 Objetivo do Projeto

Este projeto resolve a fricção entre **documentos fiscais brutos** (PDFs não padronizados) e **dados estruturados confiáveis**, utilizando uma arquitetura baseada em:

- Extração literal auditável
- Normalização estrutural previsível
- Parsing heurístico resiliente
- Orquestração com contratos explícitos
- Preparação para event-sourcing e mensageria

---

## 🏗️ Arquitetura e Diferenciais

A engine foi projetada para ambientes onde **confiabilidade, rastreabilidade e previsibilidade** são mais importantes do que extração “frágil” baseada apenas em regex.

Principais pilares:

- **Event Sourcing**  
  Cada transformação é auditável, permitindo rastreamento completo do documento bruto até o payload final.

- **Universal Parser**  
  Combinação de heurística + regex para extração agnóstica de layout e fornecedor.

- **Multi-tenant Core**  
  Isolamento lógico de execução e dados por cliente, pronto para escala.

```mermaid
graph LR
    A[Documento Fiscal (PDF)] --> B[PDF Reader]
    B --> C[Text Normalizer]
    C --> D[Parser Heurístico]
    D --> E[Orchestrator]
    E --> F[Event Store / Stream]
    E --> G[Output Estruturado]
