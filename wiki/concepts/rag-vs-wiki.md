---
title: "RAG vs Wiki Compilation"
summary: "Comparación de los dos paradigmas dominantes para memoria de LLMs: Retrieval-Augmented Generation (recuperar en cada consulta) vs Wiki Compilation (compilar una vez, mantener vivo)."
kind: comparison
sources:
  - llm-wiki-karpathy.md
  - nexus-v5.md
confidence: 0.90
provenanceState: inferred
tags: [rag, wiki, comparison, knowledge-management]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---

# RAG vs Wiki Compilation

## Comparación directa

| Dimensión | RAG | Wiki Compilation |
|-----------|-----|------------------|
| **Cuándo se procesa** | En cada consulta | Una vez, en ingest |
| **Acumulación** | Nada se acumula | El wiki crece con cada fuente |
| **Referencias cruzadas** | No existen | Mapeadas upfront |
| **Contradicciones** | Pasan desapercibidas | Marcadas en ingest |
| **Consultas sutiles** | Requieren re-derivar de 5+ fragmentos | La síntesis ya existe |
| **Mantenimiento** | Cero | Mantenido por LLM (~costo cero) |
| **Costo por consulta** | Alto (re-procesar todo) | Bajo (leer síntesis) |
| **Escala** | Excelente para corpus masivos | Mejor para ~100 fuentes de alta señal |

## Cuándo usar cada uno

### Usar RAG cuando:
- Tienes miles/millones de documentos
- Las consultas son factuales y directas
- No necesitas acumular conocimiento entre sesiones
- Ejemplos: búsqueda legal, documentación técnica masiva

### Usar Wiki Compilation cuando:
- Tienes fuentes curadas de alta calidad (~docenas a cientos)
- Quieres que el conocimiento se acumule y mejore con el tiempo
- Necesitas síntesis cross-documento
- Las consultas son sutiles y requieren integrar múltiples fuentes
- Ejemplos: investigación, lectura de libros, inteligencia competitiva, memoria de agentes

## Son complementarios

No es uno O el otro. Nova usa **ambos**:
- **Qdrant (RAG):** para búsqueda semántica rápida en el corpus completo
- **Nova Wiki (Compilation):** para síntesis persistente y compounding de conocimiento

La capa de Wiki Compilation se construye SOBRE la capa RAG. Qdrant encuentra documentos relevantes; el Wiki los sintetiza y mantiene la síntesis viva.

## Ver también

- [[LLM Wiki Pattern]] — El patrón de Wiki Compilation
- [[Compounding Knowledge]] — Por qué la acumulación importa
- [[nova-enjambre]] — Cómo aplicamos ambos en Nova
