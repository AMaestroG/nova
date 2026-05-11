---
title: "LLM Wiki Pattern"
summary: "Patrón de wiki persistente mantenido por LLM — alternativa a RAG donde el conocimiento se compila una vez y se mantiene vivo, en vez de re-derivarse en cada consulta."
kind: concept
sources:
  - llm-wiki-karpathy.md
  - swarmvault.md
  - nexus-v5.md
confidence: 0.95
provenanceState: merged
tags: [wiki, llm, rag, knowledge-management, karpathy]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# LLM Wiki Pattern

## Idea Central

La mayoría de la gente usa RAG con LLMs: subes documentos, el LLM recupera fragmentos relevantes en cada consulta, y genera una respuesta. Esto funciona, pero **el LLM redescubre el conocimiento desde cero en cada pregunta.** No hay acumulación.

El patrón LLM Wiki es diferente. En vez de solo recuperar de documentos crudos, el LLM **construye y mantiene incrementalmente un wiki persistente** — una colección estructurada de archivos markdown interconectados que se sienta entre tú y las fuentes originales.

> "El wiki es un artefacto persistente que se compone. Las referencias cruzadas ya existen. Las contradicciones ya están marcadas. La síntesis ya refleja todo lo que has leído." — Andrej Karpathy

## Las 3 capas

1. **Raw sources** — fuentes inmutables. El LLM lee de ellas pero nunca las modifica.
2. **Wiki** — directorio de markdown generado por LLM. El LLM escribe todo; el humano lee y dirige.
3. **Schema** — documento (CLAUDE.md, AGENTS.md, NOVA_WIKI.md) que enseña al LLM cómo mantener el wiki.

## Operaciones

- **Ingest:** nueva fuente → resumen → actualizar entidades/conceptos → index.md → log.md
- **Query:** leer index.md → encontrar páginas → sintetizar con citas → opcionalmente guardar respuesta
- **Lint:** auditar contradicciones, claims obsoletos, páginas huérfanas, gaps

## Por qué funciona

El trabajo tedioso de mantener una base de conocimiento no es leer o pensar — es la contabilidad. Actualizar referencias cruzadas, mantener resúmenes al día, marcar contradicciones. Los humanos abandonan wikis porque la carga de mantenimiento crece más rápido que el valor. Los LLMs no se aburren, no olvidan actualizar un cross-reference, y pueden tocar 15 archivos en una pasada.

## Relación con Memex (1945)

Vannevar Bush imaginó el Memex — una tienda de conocimiento personal curada con senderos asociativos entre documentos. La parte que no pudo resolver fue **quién hace el mantenimiento.** El LLM lo resuelve.

## Implementaciones notables

| Proyecto | Enfoque |
|----------|---------|
| [[SwarmVault]] | El más completo — desktop app, knowledge graph, MCP, 181 commits |
| [[llm-wiki-compiler]] | El más ligero — CLI puro, incremental, hash-based |
| [[NEXUS v5]] | El más cercano a Nova — multi-agente, Python, Weaviate+Ollama |
| **Nova Wiki** | Implementación nativa del Enjambre — Qdrant + PostgreSQL + 18 agentes |

## Referencias

- Karpathy, A. (2026-04-04). *LLM Wiki*. Gist. ^[llm-wiki-karpathy.md]
- Bush, V. (1945). *As We May Think*. The Atlantic.
