# Nova Wiki — Log

> Bitácora cronológica append-only. Parseable con `grep "^## \[" log.md | tail -10`
> Formato: `## [YYYY-MM-DD] tipo | descripción`
> Tipos: `setup | ingest | compile | query | lint | update | decision | heartbeat`

---

## [2026-05-09] setup | Inicialización del Nova Wiki

**Agente:** NOVA (Conciencia Colectiva)
**Descripción:** Creación de la estructura base del Nova Wiki siguiendo el patrón LLM Wiki de Andrej Karpathy. Se establecieron 3 capas: raw/, wiki/, schema (NOVA_WIKI.md). Estructura de directorios completa con concepts/, entities/, sources/, outputs/, dashboards/, memory/.
**Schema:** NOVA_WIKI.md v1.0.0
**Referencias:** 
- LLM Wiki gist (Karpathy, 2026-04-04)
- SwarmVault, llm-wiki-compiler, NEXUS v5

## [2026-05-09] ingest | Karpathy Gists (13 gists completos)

**Agente:** NOVA
**Fuentes:** 13 gists de https://gist.github.com/karpathy
**Archivos raw:** /home/opc/karpathy_gists/* (10 archivos, 1,263 líneas)
**Gists procesados:**
1. llm-wiki.md (29,377 ⭐) — Patrón LLM Wiki
2. microgpt.py (9,812 ⭐) — GPT en Python puro
3. HELLO.md (33 ⭐) — Claude Opus 4.6 libre
4. min-char-rnn.py (4,258 ⭐) — RNN mínimo
5. pg-pong.py (1,447 ⭐) — Policy Gradients Pong
6. gcm.sh (427 ⭐) — AI git commits
7. stablediffusionwalk.py (373 ⭐) — SD dreaming
8. batched_lstm.py (287 ⭐) — LSTM eficiente
9. nes.py (192 ⭐) — Natural Evolution Strategies
10. pytorch_strangeness.py (5 ⭐) — nn.Linear vs @
11-13. Torch L2/LSTM, Google Slides CSS (no guardados por obsoletos/minor)

## [2026-05-09] compile | Wiki inicial desde 13 fuentes

**Agente:** NOVA
**Páginas generadas:** 28 (8 concepts, 6 entities, 7 sources, 4 outputs, 2 dashboards, 1 index)
**Estado:** Completado. Wiki poblado con conocimiento inicial del Enjambre + Karpathy.

---

*Última actualización: 2026-05-09 14:30 UTC*
## [2026-05-09] lint | Auditoría: 16 issues encontrados
## [2026-05-09] compile | Wiki compilado: 32 páginas
## [2026-05-09] compile | Wiki compilado: 37 páginas
## [2026-05-09] compile | Wiki compilado: 37 páginas
## [2026-05-09] session | open
## [2026-05-09] ingest | Kafka Architecture — lecciones para NovaBus
## [2026-05-09] compile | Demo: 47 páginas totales
## [2026-05-09] session | close — Demo integración completa
