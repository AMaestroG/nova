---
title: "Compounding Knowledge"
summary: "Conocimiento que se acumula y compone sesión tras sesión, en vez de re-derivarse desde cero cada vez. La diferencia fundamental entre RAG y Wiki Compilation."
kind: concept
sources:
  - llm-wiki-karpathy.md
  - nexus-v5.md
confidence: 0.92
provenanceState: inferred
tags: [knowledge, memory, compounding, rag, wiki]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# Compounding Knowledge

## El problema con RAG

```
RAG:     query → search chunks → answer → forget
Wiki:    sources → compile → wiki → query → save → richer wiki → better answers
```

RAG recupera fragmentos en cada consulta. Cada pregunta redescubre las mismas relaciones desde cero. Nada se acumula. Es como tener amnesia entre sesiones.

## La solución: Compounding

En el patrón [[LLM Wiki Pattern]], el conocimiento **se compila una vez** y se mantiene actualizado. Cuando añades una nueva fuente, el LLM no solo la indexa — la lee, extrae información clave, y la integra en el wiki existente:

1. Actualiza páginas de entidades
2. Revisa resúmenes de temas
3. Marca dónde nuevos datos contradicen claims antiguos
4. Fortalece o cuestiona la síntesis evolutiva

El conocimiento se compila una vez y luego **se mantiene al día**, no se re-deriva en cada consulta.

## El efecto compuesto

- Las referencias cruzadas ya están ahí
- Las contradicciones ya están marcadas
- La síntesis ya refleja todo lo leído
- El wiki se enriquece con cada fuente y cada pregunta

## Aplicación en Nova

Nova tiene 18 agentes generando conocimiento constantemente. Sin compounding:

- Cada sesión empieza desde cero
- Las decisiones se pierden en el historial de chat
- Las lecciones no se acumulan
- El contexto se compacta y se pierde valor

Con compounding (Nova Wiki):

- Las decisiones viven en `memory/decisions/`
- Las lecciones viven en `memory/lessons/`
- Los conceptos viven en `wiki/concepts/`
- Las fuentes viven en `raw/` (inmutables)
- El wiki se enriquece con cada iteración del Enjambre

## Regla de oro

> "Si no extraes antes de compactar, pierdes el 80% del valor." — OpenClaw mini-course

Antes de cualquier compactación de contexto:
1. Lecciones → lessons.md
2. Decisiones → decisions.md
3. Pendientes → pending.md
4. Resumen de sesión → sessions/YYYY-MM-DD.md
