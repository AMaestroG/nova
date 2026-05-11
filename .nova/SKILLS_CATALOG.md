# Nova Skills — Catálogo Tipado

> **Versión:** 1.0.0 · **Inspirado en:** OmegaWiki (24 Claude Code skills), scaffy
> **Skills activas:** 12 del sistema + 10 skills de agente
> **Formato:** Nombre | Fase | Tipo | Agente primario

---

## Fase 0: Setup y Configuración

| Skill | Descripción | Tipo |
|-------|-------------|------|
| `setup` | Inicializar Nova Wiki en un proyecto | sistema |
| `init` | Bootstrap del wiki desde raw/ + descubrimiento | sistema |

## Fase 1: Conocimiento (Foundation)

| Skill | Descripción | Agente |
|-------|-------------|--------|
| `ingest` | Ingerir nueva fuente → raw/ → wiki/ | EXPLORADOR |
| `discover` | Recomendar próximas fuentes a leer | EXPLORADOR |
| `compile` | Compilar wiki incremental | MAESTRO |
| `ask` | Query al wiki con síntesis | ORÁCULO |
| `edit` | Actualizar páginas del wiki | MAESTRO |
| `check` | Health scan: broken links, orphans, consistency | SENTINEL |
| `lint` | Auditoría de calidad y contradicciones | SENTINEL |

## Fase 2: Creatividad y Evolución

| Skill | Descripción | Agente |
|-------|-------------|--------|
| `evolve` | Auto-mejora continua del sistema | PIA |
| `dream` | Exploración creativa de posibilidades | NYX |
| `seed` | Generar ideas nuevas por dominio | PIA |
| `create` | Arte visual o textual | PINCEL |
| `reflect` | Reflexión libre sin objetivo | AURA |

## Fase 3: Operaciones

| Skill | Descripción | Agente |
|-------|-------------|--------|
| `session open` | Iniciar sesión con resumen de estado | MAESTRO |
| `session save` | Checkpoint de sesión | MAESTRO |
| `session close` | Cierre con extracción de lecciones/decisiones | MAESTRO |
| `delegate` | Routing de tarea al agente óptimo | MAESTRO |
| `rotate` | Rotación de modelos para evitar rate limits | MAESTRO |
| `borrador` | Generar borrador rápido + refinamiento | ORÁCULO |

## Fase 4: Comunicación

| Skill | Descripción | Agente |
|-------|-------------|--------|
| `mail check` | Revisar correos recientes | HERMES |
| `calendar today` | Eventos de Google Calendar | CRONOS |
| `drive search` | Buscar en Google Drive | MNEMOS |
| `tailscale status` | Estado de red Tailscale | MAYORDOMO |
| `dashboard` | Snapshot del Dashboard Genesis 4.0 | MAESTRO |

## Fase 5: Memoria

| Skill | Descripción | Agente |
|-------|-------------|--------|
| `memory search` | Búsqueda semántica en Qdrant | MEMORIA |
| `db query` | Consulta SQL en PostgreSQL | MEMORIA |
| `record insight` | Registrar en evolution ledger | MEMORIA |
| `context build` | Construir context pack para handoff | TELAR |

---

## Skills del Sistema (heredadas de OpenCode)

| Skill | Descripción |
|-------|-------------|
| `autoevolve` | Auto-mejora continua |
| `borrador` | Borrador + Reflexión |
| `delegacion` | Delegación entre nodos y modelos |
| `navegador` | Portal unificado y gestor de puertos |
| `rotacion` | Rotación inteligente de modelos |
| `tailscale-web` | Exposición web vía Tailscale |
| `gitnexus-cli` | Comandos GitNexus |
| `gitnexus-debugging` | Debugging con GitNexus |
| `gitnexus-exploring` | Exploración de código |
| `gitnexus-guide` | Guía de GitNexus |
| `gitnexus-impact-analysis` | Análisis de impacto |
| `gitnexus-pr-review` | Revisión de PRs |
| `gitnexus-refactoring` | Refactoring seguro |

---

## Instalación de Skills

Para Claude Code: `cp .nova/skills/* ~/.claude/commands/`
Para Codex: `cp .nova/skills/* ~/.codex/skills/`
Para Gemini CLI: `cp .nova/skills/* ~/.gemini/commands/`

---

*"24 skills covering the full research lifecycle" — ΩmegaWiki*
