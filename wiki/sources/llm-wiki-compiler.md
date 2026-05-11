---
title: "llm-wiki-compiler"
summary: "Compilador de conocimiento ligero. Raw sources in, interlinked wiki out. 1.1k estrellas. CLI puro, incremental (hash-based), 58 commits."
kind: source
sources:
  - https://github.com/atomicstrata/llm-wiki-compiler
confidence: 0.90
provenanceState: extracted
tags: [llmwiki, llm-wiki, compiler, cli, open-source]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# llm-wiki-compiler (llmwiki)

**Repo:** [github.com/atomicstrata/llm-wiki-compiler](https://github.com/atomicstrata/llm-wiki-compiler)
**Estrellas:** 1,100 ⭐
**Commits:** 58
**Stack:** Node/TypeScript

## Qué es

El compilador más ligero del ecosistema [[LLM Wiki Pattern]]. Enfocado en una cosa: fuentes crudas entran, wiki interconectado sale. Incremental vía hash SHA-256.

## Features

- **Two-phase pipeline** — Fase 1 extrae conceptos, Fase 2 genera páginas
- **Incremental** — solo fuentes cambiadas van al LLM
- **Claim-level provenance** — `^[source.md:42-58]`
- **Review queue** — `compile --review` para aprobar antes de publicar
- **Schema layer** — concept, entity, comparison, overview
- **MCP server** — agentes pueden manejar el pipeline completo
- **Multi-provider** — Anthropic, OpenAI, Ollama, MiniMax
- **Output language** — `--lang zh-CN`, `LLMWIKI_OUTPUT_LANG`

## Limitaciones

- Software temprano
- Mejor para corpora pequeños (~docenas de fuentes)
- No tiene graph viewer ni desktop app

## Lo que Nova adoptó de llmwiki

1. Pipeline de 2 fases (extraer → generar)
2. Detección incremental por hash
3. Tipos de página (concept, entity, source, comparison, overview)
4. Claim-level provenance con rangos de línea

## Ver también

- [[LLM Wiki Pattern]] — El concepto original
- [[SwarmVault]] — Alternativa más completa
- [[NEXUS v5]] — Enfoque multi-agente
