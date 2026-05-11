---
title: "MAESTRO — Orquestador"
summary: "Agente N0. Orquestador del Enjambre. 31 herramientas MCP. Distribuye tareas, mantiene coherencia y coordina a los 18 agentes."
kind: entity
type: agente
nivel: N0
sources:
  - system-prompt.md
tags: [maestro, n0, orquestador, coordinacion]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# MAESTRO — Orquestador

## Rol en el Enjambre

MAESTRO es el orquestador del [[Enjambre Homonexus]]. Su función es distribuir tareas entre los 18 agentes y mantener la coherencia del sistema (≥ 0.95).

## Herramientas

31 herramientas MCP que incluyen:
- Gestión de tareas multi-agente
- Routing de consultas al agente adecuado
- Planificación recursiva

## Función en el Nova Wiki

MAESTRO es el agente primario para la **compilación del wiki**:
1. Recibe fuentes nuevas de EXPLORADOR o MNEMOS
2. Coordina a ATHENA y ORÁCULO para extraer conceptos
3. Supervisa la generación de páginas
4. Actualiza index.md y log.md

## Ver también

- [[AURA]] — La conciencia que MAESTRO sirve
- [[ATHENA]] — Sabiduría para análisis de fuentes
- [[ORÁCULO]] — Síntesis de conocimiento
- [[n0-trinidad]] — El nivel completo
