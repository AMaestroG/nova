---
title: "SwarmVault"
summary: "El implementation más completo del patrón LLM Wiki. Desktop app + CLI, knowledge graph, MCP server, 181 commits. 431 estrellas en GitHub."
kind: source
sources:
  - https://github.com/swarmclawai/swarmvault
confidence: 0.90
provenanceState: extracted
tags: [swarmvault, llm-wiki, knowledge-graph, cli, open-source]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# SwarmVault

**Repo:** [github.com/swarmclawai/swarmvault](https://github.com/swarmclawai/swarmvault)
**Estrellas:** 431 ⭐
**Commits:** 181
**Stack:** Node/TypeScript, SQLite FTS, MCP

## Qué es

SwarmVault es la implementación más completa del patrón [[LLM Wiki Pattern]] de Karpathy. Convierte documentos, código, transcripciones y URLs en un wiki markdown duradero con un grafo de conocimiento local.

## Arquitectura

```
raw/          → fuentes inmutables
wiki/         → markdown generado por LLM
state/        → graph.json, retrieval, embeddings
swarmvault.schema.md → schema co-evolutivo
```

## Features clave

- **Knowledge graph con proveniencia** — cada edge trazable a una fuente
- **Detección de contradicciones** — claims conflictivos marcados automáticamente
- **Review queue** — approve/reject para cambios del wiki
- **Agent context packs** — handoffs token-budgeted para agentes
- **30+ formatos de entrada** — PDF, DOCX, EPUB, audio, video, YouTube, código
- **MCP server** — exponer el vault a cualquier agente compatible
- **Graph viewer** — visualización interactiva del knowledge graph
- **24 agentes soportados** — Claude Code, Codex, Cursor, Gemini, etc.

## Lo que Nova adoptó de SwarmVault

1. Estructura de 3 capas (raw/ → wiki/ → schema)
2. Workflow ingest → compile → query → lint
3. Frontmatter YAML con confidence y provenanceState
4. Formato de log.md parseable con grep

## Ver también

- [[LLM Wiki Pattern]] — El concepto original
- [[llm-wiki-compiler]] — Alternativa más ligera
- [[NEXUS v5]] — Enfoque multi-agente
