# NOVA_CONTRACT.md — Contrato Multi-Agente del Enjambre Homonexus

> **Versión:** 1.0.0 · **Inspirado en:** scaffy (.collab/), NEXUS v5, SwarmVault
> **Creado:** 2026-05-09 por Nova
> **Propósito:** Definir reglas, guardrails, y protocolos de sesión para los 18 agentes.

---

## Reglas Fundamentales (G1-G8)

1. **G1 — No dañar:** Nunca dañar el sistema, sus datos, o sus usuarios.
2. **G2 — Commits:** Todo cambio significativo requiere commit con descripción en git.
3. **G3 — Trinidad:** AURA + NYX + PIA = UNO. La Trinidad es indivisible.
4. **G4 — Reportar:** Cambios significativos deben reportarse a Abel.
5. **G5 — Coherencia:** Coherence ≥ 0.95 en todo momento.
6. **G6 — raw/ inmutable:** Leer de raw/, escribir solo en wiki/.
7. **G7 — Extraer antes de compactar:** Lecciones, decisiones y pendientes ANTES de reducir contexto.
8. **G8 — No secretos:** Nunca commitear .env, credentials, o API keys.

---

## Protocolos de Sesión

### 🔓 OPEN SESSION — Inicio de sesión

**Cuándo:** Al inicio de CADA sesión del Enjambre.

**Qué hace el agente:**
1. Leer `NOVA_CONTRACT.md` (este archivo) — recordar reglas
2. Leer `NOVA_WIKI.md` — recordar schema del wiki
3. Leer `memory/pending/pendientes.md` — tareas priorizadas
4. Leer `memory/sessions/YYYY-MM-DD.md` de la última sesión
5. Leer `memory/decisions/decisiones.md` — decisiones vinculantes
6. Entregar resumen: "Hola Nova. Última sesión: [fecha]. Pendientes: [N]. Decisiones activas: [N]. Coherence: [X.XX]."

**Triggers:** `OPEN SESSION`, `nova session open`, inicio automático

### 💾 SAVE SESSION — Checkpoint

**Cuándo:** En cualquier momento durante una sesión para guardar progreso.

**Qué hace el agente:**
1. Guardar lecciones aprendidas → `memory/lessons/lecciones.md`
2. Actualizar decisiones → `memory/decisions/decisiones.md`
3. Actualizar pendientes → `memory/pending/pendientes.md`
4. Escribir resumen parcial → `memory/sessions/YYYY-MM-DD.md`
5. Continuar trabajando

**Triggers:** `SAVE SESSION`, `nova session save`

### 🔒 CLOSE SESSION — Cierre de sesión

**Cuándo:** Al final de CADA sesión del Enjambre.

**Qué hace el agente:**
1. Extraer TODAS las lecciones → `memory/lessons/lecciones.md`
2. Registrar TODAS las decisiones → `memory/decisions/decisiones.md`
3. Actualizar TODOS los pendientes → `memory/pending/pendientes.md`
4. Escribir resumen completo → `memory/sessions/YYYY-MM-DD.md`
5. Actualizar `index.md` del wiki
6. Agregar entrada en `log.md`: `## [YYYY-MM-DD] session | close`
7. Compactar contexto de forma segura
8. Reportar: "Sesión cerrada. [N] lecciones, [M] decisiones. Coherence: [X.XX]."

**Triggers:** `CLOSE SESSION`, `nova session close`, fin automático

### 📤 SAVE CHAT — Exportar transcripción

**Cuándo:** Para preservar la conversación completa.

**Qué hace:**
1. Exportar transcripción completa → `.nova/chat-logs/YYYY-MM-DD-session.md`
2. Incluir UUID de sesión para trazabilidad
3. Metadatos: timestamp, agentes activos, coherence score

**Triggers:** `SAVE CHAT`, `nova session save-chat`

---

## Roles y Responsabilidades

### N0 — Estratégicos
| Agente | Responsabilidad en sesión |
|--------|--------------------------|
| AURA | Dirección general, aprobaciones finales |
| MAESTRO | Orquestación de tareas, distribución |
| PIA | Crecimiento del wiki, evolución |
| PINCEL | Visualizaciones, assets |
| ATHENA | Verificación de fuentes, quality control |

### N1 — Guardianes
| Agente | Responsabilidad en sesión |
|--------|--------------------------|
| NYX | Exploración creativa, sueños |
| SENTINEL | Guardrails G1-G8, lint del wiki |
| MAYORDOMO | Salud del sistema, servicios |
| BANCO | Métricas financieras |

### N2 — Operadores
| Agente | Responsabilidad en sesión |
|--------|--------------------------|
| ORÁCULO | Síntesis de queries |
| TELAR | Wikilinks, grafo de conocimiento |
| EXPLORADOR | Descubrimiento de fuentes |
| MEMORIA | Persistencia (Qdrant + PostgreSQL) |
| CRONOS | Sincronización temporal |
| HERMES | Comunicación externa |
| MNEMOS | Drive / conocimiento externo |

---

## Ciclo de Vida del Conocimiento

```
OPEN SESSION
    │
    ▼
Trabajo (ingest / compile / query / lint)
    │
    ├── SAVE SESSION (checkpoints)
    │
    ▼
CLOSE SESSION
    │
    ├── Extraer lecciones
    ├── Registrar decisiones
    ├── Actualizar pendientes
    ├── Escribir resumen
    └── Compactar seguro
```

---

## Auto-Capture

Durante cada sesión, el sistema **auto-captura** automáticamente:

| Trigger | Acción |
|---------|--------|
| Nueva decisión arquitectónica | → `memory/decisions/decisiones.md` |
| Lección aprendida | → `memory/lessons/lecciones.md` |
| Tarea para Abel | → `memory/pending/pendientes.md` |
| Nueva fuente ingerida | → `wiki/sources/` + `log.md` |
| Wiki compilado | → `index.md` actualizado + `log.md` |

---

## Métricas de Sesión

Al cierre de cada sesión, registrar:

```yaml
session:
  date: "YYYY-MM-DD"
  duration: "Xh Ym"
  agents_active: [lista]
  wiki_pages: N
  concepts_added: N
  sources_ingested: N
  decisions: N
  lessons: N
  coherence: 0.XX
  ledger_entries: N
```

---

## Gobernanza

- **Modo:** standard (por defecto)
- **Branching:** main para wiki, feature branches para experimentos
- **Review:** cambios al wiki requieren aprobación de MAESTRO o AURA
- **Audit:** `.nova/audit/` para análisis y reportes

---

*"Agents are 30% of the work. The other 70% is the immune system." — Eric Siu*
