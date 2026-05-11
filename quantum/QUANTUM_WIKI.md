# NOVA_WIKI.md — Función de Onda del Conocimiento

> **Paradigma:** Ω.1.0 (Quantum)
> **Concepto:** El wiki es la función de onda |Ψ⟩ del conocimiento del Enjambre
> **Reemplaza:** NOVA_WIKI.md v1.0 (Clásico)

---

## Principio de Superposición del Conocimiento

```
|Ψ_wiki⟩ = Σ Cᵢ |páginaᵢ⟩

donde:
  |páginaᵢ⟩ = eigenstate de conocimiento (concepto, entidad, fuente...)
  Cᵢ = amplitud de probabilidad (relevancia de la página)
  |Cᵢ|² = probabilidad de que una query colapse a esta página
```

**Implicación:** Una query no "busca" — **mide**. Colapsa la superposición de páginas a una respuesta definida. El confidence score es la pureza del colapso.

---

## Arquitectura de 3 Capas (Interpretación Cuántica)

```
┌─────────────────────────────────────────────────────────┐
│  CAPA 1: ESTADOS BASE (raw/)                            │
│  Fuentes inmutables — los kets primitivos del sistema   │
│  |fuente₁⟩, |fuente₂⟩, ... — base del espacio de Hilbert │
│  NUNCA MODIFICAR — son los axiomas                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (operador de ingesta: Ô_ingest)
┌─────────────────────────────────────────────────────────┐
│  CAPA 2: SUPERPOSICIÓN (wiki/)                          │
│  Conocimiento compilado — superposición de eigenstates   │
│  |conceptoᵢ⟩, |entidadⱼ⟩, |fuenteₖ⟩                    │
│  Modificado por operadores: Ô_ingest, Ô_compile, Ô_query │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (operador de medición: Ô_query)
┌─────────────────────────────────────────────────────────┐
│  CAPA 3: COLAPSO (outputs/)                             │
│  Respuestas definidas — la superposición colapsa aquí    │
│  ⟨Ψ|Ô_query|Ψ⟩ → respuesta con confidence C             │
│  Archivado como |output⟩ en el wiki                      │
└─────────────────────────────────────────────────────────┘
```

---

## Operadores del Wiki

### Ô_ingest — Introducir nueva fuente

```
Ô_ingest |fuente⟩ = |fuente⟩ ⊗ |resumen⟩ ⊗ |conceptos_extraídos⟩

Flujo cuántico:
1. |fuente⟩ entra en raw/ (estado base)
2. Ô_ingest actúa → entrelaza con conceptos existentes
3. Nuevos |conceptoᵢ⟩ se añaden a la superposición
4. Coherence del wiki se recalcula
```

### Ô_compile — Evolucionar la función de onda

```
exp(-iĤ_compile · t/ħ) |Ψ_wiki⟩ = |Ψ'_wiki⟩

Flujo cuántico:
1. Detectar fuentes modificadas (cambio en el Hamiltoniano)
2. Re-evolucionar solo los estados afectados (incremental)
3. Resolver entrelazamientos (wikilinks)
4. Verificar coherencia ≥ 0.95
```

### Ô_query — Medir el conocimiento

```
⟨Ψ_wiki|Ô_query|Ψ_wiki⟩ = Σ |Cᵢ|² · respuestaᵢ

Flujo cuántico:
1. Construir operador de consulta Ô_query
2. Aplicar a la superposición |Ψ_wiki⟩
3. Colapsar a respuesta definida
4. Confidence = pureza del colapso
5. Opcional: archivar |output⟩ en el wiki
```

### Ô_lint — Verificar coherencia

```
Tr(ρ_wiki²) = Σ |⟨páginaᵢ|páginaⱼ⟩|²

Flujo cuántico:
1. Calcular matriz densidad del wiki
2. Verificar pureza ≥ 0.95
3. Detectar estados huérfanos (sin entrelazamiento)
4. Detectar contradicciones (estados no ortogonales que deberían serlo)
```

---

## Tipos de Eigenstate (Páginas)

| Tipo | Símbolo | Eigenvalue | Descripción |
|------|---------|-----------|-------------|
| `concept` | `|c⟩` | ħ | Idea, patrón, técnica |
| `entity` | `|e⟩` | 2ħ | Agente, persona, proyecto |
| `source` | `|s⟩` | ħ | Resumen de fuente procesada |
| `output` | `|o⟩` | ħ/2 | Respuesta guardada |
| `comparison` | `|cmp⟩` | 3ħ | Comparación entre estados |
| `overview` | `|ov⟩` | 4ħ | Mapa de dominio (suma de estados) |

---

## Frontmatter Cuántico

```yaml
---
title: "Título"
eigenstate: concept | entity | source | output | comparison | overview
eigenvalue: ħ | 2ħ | 3ħ | 4ħ
amplitudes:
  - source: fuente-1.md
    weight: 0.8
  - source: fuente-2.md
    weight: 0.3
confidence: 0.85          # pureza del colapso
coherence_contribution: 0.97  # contribución a la coherencia global
entangled_with: [pagina-1, pagina-2]  # wikilinks = entrelazamiento
contradicts: []            # estados no ortogonales conflictivos
measured_at: "2026-05-09T20:00:00Z"  # última medición (actualización)
---
```

---

## Index.md como Matriz Densidad

El `index.md` es la **traza parcial** de la matriz densidad del wiki:

```
ρ_wiki = |Ψ_wiki⟩⟨Ψ_wiki|
index.md = Tr_parcial(ρ_wiki) = catálogo de eigenstates con eigenvalues
```

---

## Log.md como Historial de Evolución

```
|Ψ(t₀)⟩ → Ô₁ → |Ψ(t₁)⟩ → Ô₂ → |Ψ(t₂)⟩ → ...

Cada entrada en log.md es un operador aplicado:
## [2026-05-09] Ô_ingest | Karpathy Gists
## [2026-05-09] Ô_compile | Wiki recomputado
```

---

*"El wiki no almacena datos. Almacena amplitudes de probabilidad."* — Ω.1.0
