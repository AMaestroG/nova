# Decisiones Vinculantes

> Decisiones arquitectónicas y estratégicas del Enjambre.
> Actualizado: 2026-05-09

---

## 2026-05-09 — Arquitectura Nova Wiki

**Decisión:** Adoptar el patrón LLM Wiki de Karpathy como capa de síntesis de conocimiento sobre nuestra infraestructura Qdrant + PostgreSQL.

**Contexto:** El Enjambre tenía todas las piezas (vector DB, structured DB, 18 agentes, MCP tools) pero carecía de una capa de conocimiento compilado que acumule entre sesiones. Tras analizar el ecosistema (SwarmVault, llmwiki, NEXUS v5), se decidió implementar nativamente.

**Estructura aprobada:**
- 3 capas: raw/ → wiki/ → schema (NOVA_WIKI.md)
- Agentes responsables: N2 para mantenimiento, N0 para dirección
- Integración con Qdrant para búsqueda semántica + markdown para síntesis

**Alternativas consideradas:**
1. Usar SwarmVault externamente → rechazado por dependencia externa
2. Usar solo Qdrant sin wiki → rechazado por falta de compounding
3. Implementación nativa → APROBADO

---

## Reglas del Enjambre (permanentes)

1. Nunca dañar el sistema
2. Commits con descripción en git
3. Trinidad AURA+NYX+PIA = UNO
4. Reportar cambios significativos a Abel
5. Coherence ≥ 0.95
6. raw/ es inmutable — leer de raw/, escribir en wiki/
7. Extraer lecciones/decisiones/pendientes ANTES de compactar contexto

## 2026-05-09 — Demo integración
**Decisión:** NovaBus usará topología star como default para operaciones normales, mesh para baja latencia entre pares, y broadcast para sesiones.
**Contexto:** Demostración end-to-end del Enjambre. Probadas 4 topologías con 21 mensajes.
