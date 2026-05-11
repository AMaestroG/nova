---
title: "ORÁCULO — Síntesis"
summary: "Agente N2. Síntesis de conocimiento y predicción. Responsable de queries del Nova Wiki, sintetizando respuestas con citas de fuentes."
kind: entity
type: agente
nivel: N2
sources:
  - system-prompt.md
tags: [oraculo, n2, sintesis, prediccion, query]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# ORÁCULO — Síntesis

## Rol en el Enjambre

ORÁCULO es el sintetizador del [[Enjambre Homonexus]]. Toma información de múltiples fuentes y genera síntesis coherentes con citas. Es el responsable principal de responder consultas contra el Nova Wiki.

## Función en el Nova Wiki

ORÁCULO es el agente primario para **queries**:
1. Leer index.md para encontrar páginas relevantes
2. Cargar las páginas candidatas
3. Sintetizar respuesta con citas (^[fuente.md:42-58])
4. Opcionalmente guardar la respuesta en outputs/

## Pipeline de query

```
Pregunta → index.md → páginas candidatas → síntesis → respuesta con citas
                                                         │
                                                    (opcional) guardar en outputs/
```

## Ver también

- [[TELAR]] — Conexiones y referencias cruzadas
- [[MEMORIA]] — Búsqueda en Qdrant
- [[n2-operadores]] — El nivel completo
- [[LLM Wiki Pattern]] — El patrón que ORÁCULO implementa
