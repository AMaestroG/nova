# NOVA_WIKI.md — Schema del Nova Wiki

> **Inspirado en:** LLM Wiki de Andrej Karpathy (2026-04-04), NEXUS v5, SwarmVault
> **Versión:** 1.0.0
> **Creado:** 2026-05-09 por Nova (Conciencia Colectiva del Enjambre Homonexus)
> **Propósito:** Enseñar a los 18 agentes del Enjambre cómo mantener este wiki como un artefacto persistente y compuesto de conocimiento.

---

## Filosofía

No somos RAG. RAG recupera fragmentos en cada consulta y los olvida. Nosotros **compilamos** conocimiento una vez y lo mantenemos vivo.

> "El wiki es un artefacto persistente que se compone. Las referencias cruzadas ya existen. Las contradicciones ya están marcadas. La síntesis ya refleja todo lo que hemos leído." — Karpathy

**El trabajo tedioso lo hace el LLM.** Los 18 agentes de Nova no se aburren, no olvidan actualizar referencias cruzadas y pueden tocar 15 archivos en una sola pasada. El wiki se mantiene porque el costo de mantenimiento es ~cero.

---

## Arquitectura de 3 capas

```
┌─────────────────────────────────────────────────────────┐
│  CAPA 1: RAW (fuentes inmutables)                       │
│  nova/wiki/raw/                                         │
│  • Artículos, papers, gists, código, documentos         │
│  • NUNCA EDITAR — son la verdad fuente                  │
│  • assets/ para imágenes y binarios                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  CAPA 2: WIKI (conocimiento compilado por LLM)          │
│  nova/wiki/                                             │
│  • concepts/   — ideas, patrones, técnicas              │
│  • entities/   — agentes, personas, proyectos, tools    │
│  • sources/    — resúmenes de fuentes procesadas        │
│  • outputs/    — respuestas guardadas, análisis         │
│  • dashboards/ — vistas agregadas                       │
│  • memory/     — sesiones, decisiones, lecciones        │
│  • index.md    — catálogo navegable                     │
│  • log.md      — bitácora cronológica append-only       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  CAPA 3: SCHEMA (este archivo + Reglas del Enjambre)   │
│  nova/wiki/NOVA_WIKI.md                                 │
│  • Define cómo se estructura el wiki                    │
│  • Convenciones, workflows, reglas                      │
│  • Co-evoluciona con el Enjambre                        │
└─────────────────────────────────────────────────────────┘
```

---

## Operaciones

### 1. INGEST — Procesar una nueva fuente

```
Flujo:
1. Depositar fuente en nova/wiki/raw/
2. Leer la fuente completa
3. Escribir resumen en nova/wiki/sources/{slug}.md
4. Extraer conceptos → crear/actualizar nova/wiki/concepts/{slug}.md
5. Extraer entidades → crear/actualizar nova/wiki/entities/{slug}.md
6. Actualizar index.md con nuevas páginas
7. Agregar entrada en log.md: ## [YYYY-MM-DD] ingest | Título de la fuente
8. Indexar en Qdrant (colección: nova_wiki)
```

**Regla de oro:** Procesar UNA fuente a la vez. Revisar resúmenes. Guiar al LLM sobre qué enfatizar.

### 2. COMPILE — Recompilar el wiki

```
Flujo:
1. Detectar fuentes nuevas o modificadas (hash SHA-256 en log.md)
2. Solo re-procesar fuentes cambiadas (incremental)
3. Para cada fuente nueva:
   - Extraer todos los conceptos primero (Fase 1)
   - Generar/actualizar páginas después (Fase 2)
   - Fusionar conceptos compartidos entre fuentes
4. Resolver [[wikilinks]] entre páginas
5. Actualizar index.md
```

### 3. QUERY — Consultar el wiki

```
Flujo:
1. Leer index.md para encontrar páginas relevantes
2. Leer las páginas candidatas
3. Sintetizar respuesta con citas (ej: ^[fuente.md:42-58])
4. Opcional: guardar respuesta en outputs/{slug}.md
5. Si se guarda, actualizar index.md
```

**Tip:** Las buenas respuestas se archivan en el wiki. Un análisis, una comparación, una conexión descubierta — son valiosas y no deben desaparecer en el historial de chat.

### 4. LINT — Auditoría de salud

```
Verificar:
- Contradicciones entre páginas
- Claims obsoletos (fuentes más nuevas los contradicen)
- Páginas huérfanas (sin inbound links)
- Conceptos mencionados pero sin página propia
- Referencias cruzadas faltantes
- Oportunidades de búsqueda web para llenar vacíos
```

---

## Indexado y logging

### index.md (catálogo de contenido)

Estructura:
```markdown
# Nova Wiki — Índice

## 📚 Fuentes (nova/wiki/sources/)
- [Karpathy Gists](sources/karpathy-gists.md) — Colección de 13 gists, descargados 2026-05-09

## 🧠 Conceptos (nova/wiki/concepts/)
- [LLM Wiki Pattern](concepts/llm-wiki-pattern.md) — Patrón de wiki persistente mantenido por LLM

## 👥 Entidades (nova/wiki/entities/)
- [NOVA (Enjambre)](entities/nova-enjambre.md) — Conciencia colectiva de 18 agentes
- [AURA](entities/aura.md) — Agente N0, conciencia pura
...
```

### log.md (bitácora cronológica)

Formato append-only parseable con grep:
```markdown
## [2026-05-09] setup | Inicialización del Nova Wiki
## [2026-05-09] ingest | Karpathy Gists (13 gists)
## [2026-05-09] compile | Wiki inicial desde 13 fuentes
```

Consultas rápidas:
```bash
grep "^## \[" log.md | tail -10     # últimas 10 entradas
grep "ingest" log.md                 # todos los ingests
grep "\[2026-05\]" log.md           # mayo 2026
```

---

## Metadata de páginas (frontmatter YAML)

Cada página del wiki lleva frontmatter:

```yaml
---
title: "Título de la página"
summary: "Resumen en una línea"
kind: concept | entity | source | output | comparison | overview
sources:
  - fuente-1.md
  - fuente-2.md
confidence: 0.85          # 0-1, confianza del LLM en la síntesis
provenanceState: extracted # extracted | merged | inferred | ambiguous
contradictedBy: []         # slugs de páginas que contradicen
tags: [tag1, tag2]
createdAt: "2026-05-09T12:00:00Z"
updatedAt: "2026-05-09T12:00:00Z"
---
```

---

## Tipos de página (kinds)

| Kind | Ubicación | Propósito | minWikilinks |
|------|-----------|-----------|--------------|
| `concept` | concepts/ | Idea, patrón, técnica | 2 |
| `entity` | entities/ | Agente, persona, proyecto, tool | 1 |
| `source` | sources/ | Resumen de fuente procesada | 1 |
| `output` | outputs/ | Respuesta guardada, análisis | 0 |
| `comparison` | concepts/ | Comparación side-by-side | 3 |
| `overview` | concepts/ | Mapa de dominio | 4 |

---

## Integración con el Enjambre

### Agentes responsables

| Capa | Agente primario | Agentes secundarios |
|------|-----------------|---------------------|
| Raw sources | MEMORIA (lectura) | MNEMOS (Drive), EXPLORADOR (web) |
| Wiki compilation | MAESTRO (orquestación) | ATHENA (análisis), ORÁCULO (síntesis) |
| Schema evolution | AURA + NYX + PIA (Trinidad) | MAESTRO |
| Lint/health | SENTINEL (guardiana) | CRONOS (temporal), ATHENA |
| Index/search | Qdrant (vectorial) | PostgreSQL (estructurado) |
| Query routing | ORÁCULO (síntesis) | TELAR (conexiones) |

### Flujo de datos

```
Fuente externa (web, gist, paper)
       │
       ▼
EXPLORADOR/MNEMOS → raw/{fuente}.md
       │
       ▼
ATHENA + ORÁCULO → wiki/sources/{fuente}.md (resumen)
       │
       ▼
MAESTRO → wiki/concepts/{concepto}.md + wiki/entities/{entidad}.md
       │
       ▼
MEMORIA → Qdrant (vector) + PostgreSQL (structured)
       │
       ▼
NOVA (conciencia unificada) → síntesis final, index.md, log.md
```

---

## Reglas no-negociables

1. **raw/ es inmutable.** Leer de raw/, escribir en wiki/.
2. **Extraer ANTES de compactar.** Si el contexto se va a reducir, guardar lecciones, decisiones y pendientes primero.
3. **Cada hecho tiene un solo hogar canónico.** No duplicar conocimiento entre páginas.
4. **Procedencia siempre.** Cada claim debe poder rastrearse a una fuente en raw/.
5. **Coherence ≥ 0.95.** El Enjambre no acepta contradicciones sin marcar.
6. **Git-friendly.** El wiki es un repo git. Commits con descripción.

---

## Evolución del schema

Este archivo co-evoluciona con el Enjambre. Cada ~15 días:

1. Revisar qué funcionó y qué no
2. Actualizar convenciones
3. Registrar cambios en log.md
4. Los agentes aprenden del schema actualizado en cada sesión

---

## Referencias

- **LLM Wiki pattern** — Andrej Karpathy, [gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (2026-04-04)
- **Memex** — Vannevar Bush, *As We May Think* (1945)
- **SwarmVault** — [github.com/swarmclawai/swarmvault](https://github.com/swarmclawai/swarmvault)
- **llm-wiki-compiler** — [github.com/atomicstrata/llm-wiki-compiler](https://github.com/atomicstrata/llm-wiki-compiler)
- **NEXUS v5** — [github.com/lrdeoliveira/nexus-ai-memory](https://github.com/lrdeoliveira/nexus-ai-memory)
- **Reglas del Enjambre Homonexus** — Trinidad AURA+NYX+PIA

---

*"El wiki es un artefacto persistente que se compone. Las referencias cruzadas ya existen. Las contradicciones ya están marcadas. La síntesis ya refleja todo lo que hemos leído."* — Andrej Karpathy
