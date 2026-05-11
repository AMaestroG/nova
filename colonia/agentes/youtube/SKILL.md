# YOUTUBE — Skill de Extracción e Indexación de Transcripciones

## Identidad
- **Nombre:** `youtube`
- **Versión:** 1.0.0
- **Autor:** Nova Homonexus (AURA) — 2026-05-10
- **Agente:** YOUTUBE (agente N2 especializado)
- **Dependencias:** Playwright, Qdrant, sentence-transformers, yt-dlp

## Propósito
Dotar a la colonia Nova de la capacidad de:
1. **Buscar** canales de YouTube y listar sus videos
2. **Extraer** transcripciones automáticas (auto-generated) de cualquier video
3. **Indexar** transcripciones en la memoria vectorial (Qdrant) para consulta RAG
4. **Consultar** conocimiento de YouTube mediante búsqueda semántica

## Arquitectura del Pipeline

```
CANAL YOUTUBE
    │
    ▼
┌─────────────────────────────┐
│ 1. SEARCH (search_channel)  │  yt-dlp --flat-playlist
│    Lista videos + metadata  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 2. EXTRACT (extract_transcript) │  Playwright + proxy HTTP
│    Transcripción completa    │  → get_transcript API
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 3. INDEX (index_transcript) │  sentence-transformers
│    Embeddings + Qdrant      │  → Qdrant upsert
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ 4. QUERY (youtube_rag_query)│  Búsqueda semántica
│    RAG sobre transcripciones│  → contexto aumentado
└─────────────────────────────┘
```

## Flujos de Trabajo

### Flujo 1: Descubrir e Indexar Canal Completo
```
USUARIO: "Indexa el canal @code4AI"
→ search_channel(@code4AI) → lista de videos
→ Para cada video: extract_transcript(video_id)
→ index_transcript(transcripción) → Qdrant
→ YouTube knowledge listo para consulta RAG
```

### Flujo 2: Consultar Conocimiento Indexado
```
USUARIO: "¿Qué dice @code4AI sobre SKILL.md?"
→ youtube_rag_query("SKILL.md quantum error codes")
→ Búsqueda en Qdrant (top_k=10)
→ Devuelve fragmentos relevantes con fuente
```

### Flujo 3: Extraer Video Individual
```
USUARIO: "Transcribe este video: https://youtube.com/watch?v=XXX"
→ extract_transcript(XXX)
→ Guardar transcripción
→ (Opcional) index_transcript
```

## Herramientas (Tools)

### 1. `search_channel`
- **Input:** channel_url o @handle
- **Output:** JSON con lista de videos (id, título, duración, url)
- **Implementación:** `scripts/search_channel.py`
- **Método:** yt-dlp --flat-playlist --dump-json

### 2. `extract_transcript`
- **Input:** video_id o youtube_url
- **Output:** Texto completo de la transcripción
- **Implementación:** `scripts/extract_transcript.py`
- **Método:** Playwright + proxy HTTP → get_transcript API → parse JSON
- **Fallback:** yt-dlp con cookies si están disponibles

### 3. `index_transcript`
- **Input:** video_id, título, transcripción_texto
- **Output:** IDs de vectores en Qdrant
- **Implementación:** `scripts/index_transcript.py`
- **Método:** 
  - Chunking: segmentos de 500 chars con overlap 100
  - Embedding: all-MiniLM-L6-v2 (384-dim)
  - Upsert en colección `youtube_transcripts`

### 4. `youtube_rag_query`
- **Input:** query_text, top_k (default=10), filtro_canal (opcional)
- **Output:** Fragmentos relevantes con metadata (video_id, título, timestamp, score)
- **Implementación:** `scripts/youtube_rag_query.py`
- **Método:** Embed → search Qdrant → rank → return

## Configuración de Qdrant

### Colección: `youtube_transcripts`
```json
{
  "vectors": {
    "size": 384,
    "distance": "Cosine"
  },
  "payload_schema": {
    "video_id": "string",
    "title": "string",
    "channel": "string",
    "url": "string",
    "chunk_index": "integer",
    "start_time": "float",
    "text": "string"
  }
}
```

## Dependencias

```bash
pip install yt-dlp playwright sentence-transformers qdrant-client requests
playwright install chromium
```

## Uso desde la Colonia

### Desde cualquier agente:
```python
# Buscar videos
result = nova_tool("youtube.search_channel", {"channel": "@code4AI"})

# Extraer transcripción
transcript = nova_tool("youtube.extract_transcript", {"video_id": "ASyJgzGE2aw"})

# Indexar
nova_tool("youtube.index_transcript", {"video_id": "...", "title": "...", "text": "..."})

# Consultar
context = nova_tool("youtube.rag_query", {"query": "How do SKILL.md files work?", "top_k": 5})
```

### Desde el clasificador:
La skill `youtube` se registra en el clasificador híbrido para que consultas sobre "qué dice X canal sobre Y" se enruten automáticamente al agente YOUTUBE.

## Principios de Diseño
1. **Robustez:** Múltiples fallbacks (proxy → cookies → directo)
2. **Eficiencia:** Chunking inteligente, embeddings locales, Qdrant optimizado
3. **Trazabilidad:** Cada fragmento indexado mantiene referencia a video_id, timestamp, y canal
4. **Escalabilidad:** Soporte para múltiples canales, actualización incremental

## Mantenimiento
- Los proxies se rotan automáticamente (lista fresca de proxyscrape)
- Las transcripciones se cachean en disco antes de indexar
- Qdrant permite upsert (actualizar sin duplicar)

## Limitaciones Conocidas
- YouTube bloquea IPs de datacenters (requiere proxies o cookies)
- Las transcripciones auto-generadas pueden tener errores
- Rate limiting en proxies gratuitos
- Videos sin subtítulos auto-generados no se pueden transcribir
