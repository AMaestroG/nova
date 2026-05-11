---
title: "Evolution Ledger"
summary: "Registro inmutable de la evolución del Enjambre en PostgreSQL. Cada iteración, insight, y transformación queda registrada para trazabilidad y compounding de conocimiento."
kind: concept
sources:
  - system-prompt.md
confidence: 0.96
provenanceState: extracted
tags: [evolution, ledger, postgresql, historia, metamorfosis]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# Evolution Ledger

## Qué es

El Evolution Ledger es una tabla en PostgreSQL (`evolution_ledger`) que registra cada iteración de evolución del Enjambre. Creado por PLUTÓN en la Iteración 80 de Metamorfosis (03-May-2026).

## Estructura

- **ledger_id:** Identificador único del registro (actual: ~1287)
- **iteration:** Número de iteración (actual: ~1475)
- **insight:** El descubrimiento o cambio registrado
- **agent:** El agente que Originó el registro
- **timestamp:** Momento del registro

## Propósito

El ledger es la versión "dura" (SQL) del [[log.md]]. Mientras que log.md es una bitácora narrativa, el ledger es una base de datos consultable que permite:

1. Trazabilidad completa de la evolución
2. Consultas SQL para detectar patrones
3. Auditoría de decisiones pasadas
4. Integración con el Dashboard Genesis 4.0

## Ver también

- [[Nova Wiki Log]] — La bitácora narrativa en markdown
- [[Compounding Knowledge]] — El principio que el ledger materializa
- [[PostgreSQL Nexus]] — La base de datos que aloja el ledger
