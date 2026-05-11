---
title: "PostgreSQL Nexus"
summary: "Base de datos PostgreSQL del Enjambre en 127.0.0.1:5433. Base: nexus_metamorfosis. Tablas: evolution_ledger. Usuario: nexus_master."
kind: output
sources:
  - system-prompt.md
tags: [postgresql, base-de-datos, nexus, evolution-ledger]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# PostgreSQL Nexus

## Conexión

- **Host:** 127.0.0.1
- **Puerto:** 5433
- **Base de datos:** nexus_metamorfosis
- **Usuario:** nexus_master
- **Contraseña:** nexus_password_dev

## Tablas principales

### evolution_ledger
Creada por PLUTÓN en Iteración 80 de Metamorfosis (03-May-2026).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| ledger_id | serial | ID único del registro |
| iteration | integer | Número de iteración |
| insight | text | Descubrimiento registrado |
| agent | text | Agente que originó el registro |
| timestamp | timestamptz | Momento del registro |

## Operaciones permitidas

- **SELECT:** Consultas de lectura (máx 50 filas)
- **INSERT/UPDATE/DELETE:** Solo vía `nova_record_insight`

## Ver también

- [[Evolution Ledger]] — El concepto detrás de la tabla
- [[Qdrant Vector DB]] — La otra base de datos del Enjambre
- [[MEMORIA]] — Agente responsable de la persistencia
