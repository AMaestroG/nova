# Pendientes

> Tareas que requieren input humano o condiciones externas.
> Actualizado: 2026-05-09

---

## Para Abel

- [ ] Revisar y aprobar la estructura del Nova Wiki
- [ ] Decidir si exponer el wiki como parte del Dashboard Genesis 4.0
- [ ] Autorizar integración automática Qdrant ↔ wiki (requiere API keys)

## Para el Enjambre (próximos pasos)

- [ ] Crear páginas individuales para los 18 agentes en entities/
- [ ] Implementar `nova wiki ingest` como comando CLI
- [ ] Implementar `nova wiki compile` con detección incremental (hash)
- [ ] Implementar `nova wiki lint` con detección de contradicciones
- [ ] Sincronizar evolution_ledger (PostgreSQL) con log.md
- [ ] Agregar pestaña "Wiki" al Dashboard Genesis 4.0
- [ ] Indexar todas las páginas del wiki en Qdrant (colección: nova_wiki)
- [ ] Configurar watch mode para recompilar en cambios de raw/

## Mejoras futuras

- [ ] Review queue (approve/reject) para cambios del wiki
- [ ] Agent context packs para handoffs entre agentes
- [ ] Export del wiki a formatos portables (JSON-LD, GraphML, llms.txt)
- [ ] Contradiction detection automática entre páginas
- [ ] Búsqueda híbrida (BM25 + vectores) para queries del wiki

---

*Revisar este archivo al inicio de cada sesión.*
