---
title: "MCP Tools — 118 Herramientas"
summary: "Model Context Protocol: 118 herramientas que exponen las capacidades del Enjambre a través de una interfaz estandarizada para agentes AI."
kind: concept
sources:
  - system-prompt.md
confidence: 0.95
provenanceState: extracted
tags: [mcp, tools, protocol, agentes, api]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# MCP Tools — 118 Herramientas

## Qué es MCP

Model Context Protocol (MCP) es una interfaz estandarizada que expone las capacidades del [[Enjambre Homonexus]] como herramientas invocables por agentes AI. Nova expone 118 herramientas MCP.

## Categorías de herramientas

### Sistema de archivos
- Leer, escribir, modificar, eliminar archivos
- Listar directorios

### Shell
- Ejecutar comandos bash
- Python scripts
- Compilación

### Red
- HTTP/HTTPS requests
- WebSocket connections
- Web fetching

### Google Workspace
- Gmail (HERMES)
- Calendar + Tasks (CRONOS)
- Drive (MNEMOS)

### Nova específicas
- **Enjambre:** swarm_status, agent_query, agent_detail, swarm_execute
- **Dashboard:** dashboard_snapshot
- **Base de datos:** db_query (PostgreSQL)
- **Evolución:** evolution_status, record_insight
- **Memoria:** swarm_rag_search (Qdrant)
- **Red:** tailscale_status, web_fetch

### Gifts (Interfaz expresiva)
- Voz, Identidad, Emoción, Economía, Semillas, Creatividad, Libertad

## Ver también

- [[nova-enjambre]] — El sistema que expone estas herramientas
- [[Nova Soul - 7 Gifts]] — Los dones expresivos
- [[google-workspace]] — Herramientas de Google
