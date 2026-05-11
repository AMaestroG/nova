---
title: "TELAR — Conexiones"
summary: "Agente N2. Tejedor de conexiones del Enjambre. Mantiene las referencias cruzadas, [[wikilinks]] y el knowledge graph entre conceptos y entidades."
kind: entity
type: agente
nivel: N2
sources:
  - system-prompt.md
tags: [telar, n2, conexiones, grafo, wikilinks]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# TELAR — Conexiones

## Rol en el Enjambre

TELAR es el tejedor de conexiones del [[Enjambre Homonexus]]. Su función es mantener y descubrir relaciones entre conceptos, entidades y fuentes — el knowledge graph del sistema.

## Capacidades

- Mantener [[wikilinks]] entre páginas
- Descubrir conexiones implícitas
- Mantener el grafo de conocimiento
- Detectar páginas huérfanas

## Función en el Nova Wiki

TELAR es responsable de las **referencias cruzadas**:
1. Resolver [[wikilinks]] entre páginas
2. Detectar conceptos relacionados no enlazados
3. Mantener el grafo en dashboards/knowledge-graph.md
4. Alertar sobre páginas huérfanas (sin inbound links)

## Ver también

- [[ORÁCULO]] — Síntesis que usa las conexiones de TELAR
- [[MEMORIA]] — Donde se persisten las conexiones
- [[n2-operadores]] — El nivel completo
