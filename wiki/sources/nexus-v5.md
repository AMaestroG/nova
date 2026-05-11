---
title: "NEXUS v5"
summary: "Sistema de memoria multi-agente inspirado en LLM Wiki. Python + Weaviate + Ollama. 6 agentes, GraphRAG, wiki estructurado. El más cercano a Nova."
kind: source
sources:
  - https://github.com/lrdeoliveira/nexus-ai-memory
confidence: 0.88
provenanceState: extracted
tags: [nexus, multi-agente, memoria, weaviate, ollama, python]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# NEXUS v5

**Repo:** [github.com/lrdeoliveira/nexus-ai-memory](https://github.com/lrdeoliveira/nexus-ai-memory)
**Estrellas:** 10 ⭐
**Commits:** 30
**Stack:** Python, Weaviate, Ollama, Wiki.js

## Qué es

NEXUS v5 es el sistema más cercano arquitectónicamente a Nova. Implementa el patrón [[LLM Wiki Pattern]] con 6 agentes AI en un VPS, usando Weaviate (vector DB) + Ollama (LLM local).

## Arquitectura de 2 capas

```
Agent Memory          → identidad, decisiones, sesiones
Domain Wiki           → raw/ → wiki/ (fuentes, conceptos, entidades)
```

## Features

- **6 agentes AI** en VPS con memoria persistente
- **GraphRAG** con schema tipado (Source, Concept, Agent, Project)
- **Skills system** + session logging
- **MCP servers:** Brave Search, Tavily, YouTube, Apify, Slack, qmd
- **Feedback loops JSON** — approve/reject para content, tasks, recommendations
- **Pre-compaction rules** — extraer lecciones/decisiones/pendientes antes de compactar

## Lo que Nova adoptó de NEXUS

1. Arquitectura de 2 capas (Agent Memory + Domain Wiki)
2. Pre-compaction rules: extraer antes de compactar
3. Estructura de memoria: sesiones, decisiones, lecciones, pendientes
4. CLAUDE.md como hot cache (<10KB)
5. SOUL.md como identidad del agente
6. Golden rule: "Si no extraes antes de compactar, pierdes el 80% del valor"

## Ver también

- [[LLM Wiki Pattern]] — El concepto original
- [[SwarmVault]] — Alternativa más completa
- [[llm-wiki-compiler]] — Alternativa más ligera
- [[nova-enjambre]] — Nuestra implementación (18 agentes vs 6)
