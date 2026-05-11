# Proyectos Open-Source Relevantes para Nova

*Descubiertos vía @ManuAGI - AutoGPT Tutorials (video lAAcjj5fISE)*
*Analizados: 2026-05-10*

---

## 1. Archon (⭐ 21K) — Harness Builder

**Repo:** https://github.com/coleam00/Archon
**Lema:** "The first open-source harness builder for AI coding. Make AI coding deterministic and repeatable."

### Arquitectura
```
Platform Adapters (Web, CLI, Telegram, Slack, Discord, GitHub)
        ↓
    Orchestrator (Message Routing & Context Management)
        ↓
  ┌─────┼─────────┐
  ↓     ↓          ↓
Command  Workflow  AI Clients
Handler  Executor  (Claude/Codex)
(Slash)  (YAML)
  └─────┼─────────┘
        ↓
  SQLite/PostgreSQL (7 tablas)
```

### Ideas para Nova
- **Workflows YAML deterministas** = nuestros SKILL.md
- **Platform Adapters** → Nova debería tener adapters para Telegram, Discord, Web
- **7 tablas SQLite** → estructura de persistencia bien definida
- **Message Routing** → similar al G2 Router del Harness Core

---

## 2. OpenSwarm (⭐ 2K) — Enjambre Multi-Agente  

**Repo:** https://github.com/VRSEN/OpenSwarm
**Lema:** "Claude code for everything except coding"
**Base:** Agency Swarm (VRSEN/agency-swarm)

### Características
- **8 agentes especializados** coordinados por orquestador
- Un prompt → deliverables completos
- Instalación en 30 segundos
- 100% customizable y forkable

### Ideas para Nova
- Nova ya es un enjambre (18 agentes). OpenSwarm valida la arquitectura.
- **Especialización**: cada agente tiene UN rol claro
- **Orquestador central**: como MAESTRO en Nova
- **Un prompt → múltiples outputs**: Nova debería poder generar documentos completos

---

## 3. Multica (⭐ 27K) — Compound Skills Platform

**Repo:** https://github.com/multica-ai/multica
**Lema:** "Turn coding agents into real teammates — assign tasks, track progress, compound skills."

### Características Clave
- **Agents as Teammates**: perfiles, tablero, comentarios, blockers
- **Autonomous Execution**: ciclo completo (enqueue → claim → start → complete/fail)
- **Reusable Skills**: cada solución se vuelve una skill reusable
- **Compound Skills**: las skills se acumulan y mejoran con el tiempo
- **Unified Runtimes**: local + cloud

### Arquitectura
```
Next.js Frontend ↔ Go Backend (Chi + WebSocket) ↔ PostgreSQL (pgvector)
```

### Ideas para Nova
- **Compound Skills**: Trace2Skill + evolución continua
- **Agent Lifecycle**: enqueue → claim → start → complete/fail (Nova no tiene esto)
- **Agent Board**: dashboard donde los agentes muestran su estado
- **pgvector**: Nova ya usa Qdrant, pero pgvector es alternativa ligera

---

## Comparación con Nova Homonexus

| Concepto | Archon | OpenSwarm | Multica | Nova |
|----------|--------|-----------|---------|------|
| Harness/Orquestación | ✅ YAML workflows | ✅ Orquestador | ✅ Go Backend | ✅ Harness Core (G1-G8) |
| Multi-agente | ✅ AI Clients | ✅ 8 agentes | ✅ Agents as Teammates | ✅ 18 agentes |
| Skills | ✅ YAML deterministas | ❌ | ✅ Compound Skills | ✅ SKILL.md + Trace2Skill |
| Memoria | ✅ SQLite/PostgreSQL | ❌ | ✅ pgvector | ✅ Qdrant + Hierarchical Memory |
| Determinismo | ✅ "deterministic & repeatable" | ❌ | ✅ Autonomous Execution | ✅ Quantum Skill Corrector |
| Interfaz | Web, CLI, Telegram, Slack | CLI | Web Dashboard | Centinela Dashboard |
| Evolución | ❌ | ❌ | ✅ Compound Skills | ✅ PIA + Evolution Ledger |

---

## Acciones Prioritarias

1. **Adoptar Agent Lifecycle de Multica** — enqueue → claim → start → complete/fail para cada agente
2. **Compound Skills** — cada skill debe mejorar con el uso (métricas de éxito, refinamiento)
3. **Platform Adapters** — Web UI + CLI + Telegram (como Archon)
4. **Message Routing** — mejorar G2 Router inspirado en Archon Orchestrator
