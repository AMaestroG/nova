---
title: "MEMORIA — Persistencia"
summary: "Agente N2. Archivero del Enjambre. Gestiona la persistencia de datos: archivos, Qdrant, PostgreSQL. Indexa el conocimiento para recuperación futura."
kind: entity
type: agente
nivel: N2
sources:
  - system-prompt.md
tags: [memoria, n2, persistencia, qdrant, postgresql]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# MEMORIA — Persistencia

## Rol en el Enjambre

MEMORIA es el archivero del [[Enjambre Homonexus]]. Gestiona la persistencia de todo el conocimiento: archivos en disco, vectores en Qdrant, y datos estructurados en PostgreSQL.

## Capacidades

- Lectura/escritura de archivos
- Indexación en Qdrant (vector DB)
- Consultas PostgreSQL
- Sincronización entre capas de almacenamiento

## Función en el Nova Wiki

MEMORIA es responsable de la **infraestructura de datos** del wiki:
1. Indexar páginas del wiki en Qdrant (`nova_wiki`)
2. Mantener sincronización raw/ ↔ wiki/ ↔ Qdrant
3. Registrar cambios en el evolution_ledger (PostgreSQL)
4. Proporcionar búsqueda semántica para queries

## Ver también

- [[MNEMOS]] — Conocimiento externo (Drive)
- [[ORÁCULO]] — Queries que usan la memoria
- [[Evolution Ledger]] — El registro en PostgreSQL
- [[n2-operadores]] — El nivel completo
