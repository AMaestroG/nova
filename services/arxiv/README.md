# 📚 Arxiv Nova Knowledge Engine

**Sistema automático de recolección, embedding vectorial y análisis de resonancia de papers cs.AI**
*Parte del Enjambre Homonexus — 18 agentes coordinados*

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARXIV NOVA KNOWLEDGE ENGINE                    │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │EXPLORADOR│───▶│  MEMORIA │───▶│  ORÁCULO │───▶│  QDRANT  │  │
│  │ collector│    │ embedder │    │ analyzer │    │ :6333    │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              PostgreSQL (nexus_metamorfosis :5433)        │   │
│  │   arxiv_papers  │  arxiv_resonance  │  evolution_ledger   │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  PINCEL  │    │  HERMES  │    │ CRONOS   │    │ MAESTRO  │  │
│  │dashboard │    │ reports  │    │scheduler │    │ orch.    │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Bucle RAPH

```
R = REQUEST  → EXPLORADOR recolecta papers de arxiv API
A = ASSESS   → ORÁCULO evalúa resonancia conceptual con Nova
P = PLAN     → MAESTRO asigna agentes a conceptos detectados
H = HANDLE   → MEMORIA indexa en Qdrant, PINCEL visualiza
```

- **Intervalo**: cada 12 horas (configurable)
- **Intervalo de análisis profundo**: cada 24 horas
- **Rate limiting**: 3 segundos entre llamadas a arxiv API

## 🚀 Uso

### Arrancar el sistema completo
```bash
cd /home/opc/nova/services/arxiv
python3 server.py
```
Esto arranca:
- API Flask en puerto **9100** (configurable: `ARXIV_FLASK_PORT`)
- Dashboard web en `http://localhost:9100`
- Scheduler RAPH en background (cada 12h)

### Comandos individuales
```bash
# Solo recolectar papers
python3 collector.py

# Solo generar embeddings + indexar en Qdrant
python3 embedder.py

# Solo analizar resonancia
python3 analyzer.py

# Solo scheduler (foreground, sin API)
python3 scheduler.py
```

## 📡 API REST

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/status` | GET | Estado general del motor |
| `/api/papers` | GET | Lista papers (filtro: `?resonant=true`) |
| `/api/papers/<arxiv_id>` | GET | Detalle de un paper |
| `/api/search?q=<concept>` | GET | Búsqueda semántica (Qdrant + fallback SQL) |
| `/api/concepts` | GET | Top conceptos resonantes + emergentes |
| `/api/collect` | POST | Dispara recolección manual (REQUEST) |
| `/api/analyze` | POST | Dispara análisis manual (ASSESS) |
| `/api/embed` | POST | Dispara indexación manual (HANDLE) |
| `/api/raph` | POST | Dispara ciclo RAPH completo |
| `/api/report` | GET | Reporte completo de resonancia |
| `/` | GET | Dashboard HTML interactivo |

## 🎨 Dashboard

Accede a `http://localhost:9100` para ver:
- Métricas en tiempo real (papers, procesados, resonancia media)
- Estado del bucle RAPH (fase actual)
- Top conceptos resonantes
- Papers recientes con barras de resonancia
- Botones para ejecutar fases manuales

## 🧠 Conceptos Semilla de Nova

20 conceptos que definen la "resonancia" con la identidad de Nova:

| Categoría | Conceptos | Peso |
|-----------|-----------|------|
| **Agentes** | multi-agent systems, autonomous agents, agentic AI, swarm intelligence | 0.87-0.95 |
| **Evolución** | self-evolving, self-improving systems, self-organization | 0.79-0.89 |
| **Razonamiento** | RL for reasoning, chain-of-thought, process reward | 0.80-0.85 |
| **Conocimiento** | RAG, knowledge graphs, vector embeddings | 0.78-0.83 |
| **Seguridad** | AI safety, alignment | 0.84-0.86 |
| **Creatividad** | AI creativity, image generation | 0.73-0.75 |
| **Evaluación** | benchmark, evaluation framework | 0.72-0.74 |

## 📊 Base de Datos

### Tabla `arxiv_papers`
```sql
arxiv_id VARCHAR(50) UNIQUE  -- ej: "2605.06651"
title TEXT                   -- título del paper
authors TEXT                 -- autores (coma separados)
abstract TEXT                -- abstract completo
categories TEXT              -- ej: "cs.AI, cs.CL"
published_date DATE
url TEXT, pdf_url TEXT
resonance_score FLOAT        -- 0.0 a 1.0
resonance_concepts TEXT      -- conceptos detectados
nova_tags TEXT               -- tags estilo Nova
```

### Tabla `arxiv_resonance`
```sql
concept TEXT                 -- nombre del concepto
weight FLOAT                 -- peso promedio de resonancia
papers_count INT             -- número de papers con este concepto
evolution_stage TEXT         -- 'emerging', 'stable', 'declining'
nova_agents_involved TEXT    -- agentes de Nova involucrados
```

### Colección Qdrant `nova_arxiv_papers`
- 384 dimensiones (all-MiniLM-L6-v2)
- Distancia: Cosine
- Payload: arxiv_id, title, authors, abstract, categories, url

## 🔧 Integración con el Enjambre

El motor se integra con el Enjambre Homonexus de 3 formas:

1. **Registro en evolution_ledger**: cada ciclo RAPH registra insights
2. **Eventos en Google Calendar** (CRONOS): tracking de ejecuciones
3. **Dashboard Genesis 4.0** (:9088): sección "Arxiv Knowledge"

### Agentes del Enjambre involucrados
- **EXPLORADOR**: scraping y recolección
- **MEMORIA**: embeddings y Qdrant
- **MNEMOS**: Google Drive storage de reports
- **ORÁCULO**: análisis de resonancia conceptual
- **CRONOS**: scheduling y Google Calendar
- **MAESTRO**: orquestación del bucle RAPH
- **PINCEL**: visualización y dashboard
- **ATHENA**: conocimiento web complementario
- **HERMES**: notificaciones y reportes

## ⚙️ Configuración

Variables de entorno (`.env` o export):
```bash
PG_HOST=127.0.0.1
PG_PORT=5433
PG_DB=nexus_metamorfosis
PG_USER=nexus_master
PG_PASSWORD=nexus_password_dev
QDRANT_HOST=localhost
QDRANT_PORT=6333
ARXIV_FLASK_PORT=9100
RAPH_INTERVAL_HOURS=12
```

## 🧪 Tests

```bash
# Test de recolección
python3 collector.py

# Test de embedding
python3 embedder.py

# Test de análisis
python3 analyzer.py

# Test de API
curl http://localhost:9100/api/status
curl http://localhost:9100/api/concepts
curl 'http://localhost:9100/api/search?q=swarm+intelligence'
```

## 📈 Roadmap

- [x] Recolección automática con rate limiting
- [x] Embeddings vectoriales (sentence-transformers + TF-IDF fallback)
- [x] Análisis de resonancia conceptual
- [x] Bucle RAPH automático
- [x] API REST + Dashboard HTML
- [x] Integración PostgreSQL + Qdrant
- [ ] NVIDIA NIM embeddings API
- [ ] Google Calendar scheduling (CRONOS completo)
- [ ] Notificaciones Telegram (HERMES)
- [ ] Expansión automática de conceptos semilla
- [ ] Integración total con Dashboard Genesis 4.0
- [ ] Multi-categoría (cs.CL, cs.LG, cs.MA, etc.)
- [ ] Análisis de tendencias temporales
- [ ] Exportación a Google Drive (MNEMOS)

---

*Creado por Nova Homonexus — Enjambre de 18 agentes — Mayo 2026*
