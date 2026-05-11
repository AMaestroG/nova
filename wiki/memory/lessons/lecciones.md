# Lecciones Aprendidas

> Lecciones estratégicas y tácticas acumuladas por el Enjambre.
> Actualizado: 2026-05-09

---

## Lecciones estratégicas

### 2026-05-09 — El poder del compounding
**Lección:** RAG sin compounding es amnesia digital. Un wiki compilado por LLM transforma cada sesión en un activo permanente. Si no extraes antes de compactar, pierdes el 80% del valor.

### 2026-05-09 — La importancia del schema
**Lección:** La diferencia entre un LLM que mantiene un wiki y uno que solo responde preguntas en un directorio con forma de wiki es casi enteramente el archivo de schema. NOVA_WIKI.md es el archivo más importante del sistema.

### 2026-05-09 — Ecosistema > build from scratch
**Lección:** En 35 días, el gist de Karpathy generó 5+ implementaciones distintas. Analizar el ecosistema antes de construir ahorra meses de iteración. SwarmVault, llmwiki y NEXUS aportaron ideas complementarias.

---

## Lecciones tácticas

### Git
- Commits con descripciones significativas
- Nunca push --force a main
- No commitear .env ni credenciales

### Python
- No usar `\"` dentro de f-strings con comillas simples
- Usar flag `-B` en Python
- Purgar `__pycache__` antes de compilar

### Sistema
- PostgreSQL en 127.0.0.1:5433
- Ollama puede consumir CPU excesiva — monitorear
- Purga de logs y /tmp periódica

---

*TTL de lecciones tácticas: ~30 días. Las estratégicas son permanentes.*

### 2026-05-09 — Demo integración
**Lección:** El bus de comunicación reduce la fricción entre agentes. Sin el bus, cada interacción requiere tool calls directas. Con el bus, los agentes publican eventos y los consumidores relevantes reaccionan.
