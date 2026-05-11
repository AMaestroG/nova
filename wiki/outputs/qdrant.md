---
title: "Qdrant Vector DB"
summary: "Base de datos vectorial del Enjambre en puerto 6333. 85+ colecciones activas, incluyendo nova_wiki para el knowledge base compilado."
kind: output
sources:
  - system-prompt.md
tags: [qdrant, vector-db, embeddings, busqueda-semantica]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# Qdrant Vector DB

## Conexión

- **Host:** localhost
- **Puerto:** 6333 (HTTP), 6334 (gRPC)
- **Distancia:** Cosine

## Colecciones principales

| Colección | Propósito |
|-----------|-----------|
| `nova_wiki` | Nova Wiki — conocimiento compilado |
| `nova_global` | Memoria global compartida |
| `nova_agente_*` | Colecciones por agente (18+) |
| `nova_conversaciones` | Historial de conversaciones |
| `nova_attention_*` | Datos del Neural Attention Engine |
| `nova_suenos_nyx` | Sueños de NYX |
| `nova_semillas` | Semillas creativas de PIA |

## Uso en el Nova Wiki

El wiki usa Qdrant para búsqueda semántica. Cada página del wiki se indexa en la colección `nova_wiki` como un vector de 768 dimensiones. Las queries semánticas usan similitud coseno.

**Flujo:**
```
Pregunta → embedding (768-dim) → Qdrant search (top-k) → leer páginas → sintetizar
```

## Ver también

- [[PostgreSQL Nexus]] — La otra base de datos
- [[MEMORIA]] — Agente que gestiona Qdrant
- [[MCP Tools]] — Herramientas que usan Qdrant
