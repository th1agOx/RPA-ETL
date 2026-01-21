# RPA-ETL: Inteligência Fiscal & Orquestração de Dados 

![CI Build](https://github.com/th1agOx/RPA-ETL/actions/workflows/tests.yml/badge.svg)
![Coverage](https://img.shields.io/codecov/c/github/th1agOx/RPA-ETL)
![Version](https://img.shields.io/github/v/release/th1agOx/RPA-ETL?color=blue&label=version)
![License](https://img.shields.io/github/license/th1agOx/RPA-ETL)
![Python](https://img.shields.io/badge/python-3.12-blue?logo=python)

> **Enterprise RPA Engine** focado em processamento contábil de alta fidelidade, auditoria orientada a eventos e extração heurística.

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
    A[Doc Fiscal PDF] --> B[Universal Parser]
    B --> C{Heurística/Regex}
    C --> D[Event Sourcing Store]
    D --> E[Output Estruturado]
    E --> F[Consumo: Core Semântico / ERP]
    
    subgraph Observabilidade
    D -.-> G[Traceback & Logs]
    end
