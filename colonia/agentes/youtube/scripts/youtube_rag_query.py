#!/usr/bin/env python3
"""
youtube_rag_query.py — Consulta RAG semántica sobre transcripciones de YouTube indexadas.

Pipeline:
  1. Recibir query en lenguaje natural
  2. Generar embedding con sentence-transformers
  3. Buscar en Qdrant (similitud coseno, top_k resultados)
  4. Devolver fragmentos relevantes con metadata (video_id, título, timestamp, score)
  5. Opcional: formatear como contexto para LLM

USO:
    python3 youtube_rag_query.py "How do SKILL.md files work as quantum error codes?"
    python3 youtube_rag_query.py --query "memory optimization" --top-k 5 --channel @code4AI
    python3 youtube_rag_query.py --query "multi-agent" --format llm_context
"""

import sys
import os
import json
import argparse
from typing import List, Dict, Optional

# Dependencias
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "qdrant-client"], check=True)
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "sentence-transformers"], check=True)
    from sentence_transformers import SentenceTransformer


QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "youtube_transcripts"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 10

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_client():
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def rag_query(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    channel_filter: Optional[str] = None,
    video_id_filter: Optional[str] = None,
    score_threshold: float = 0.3,
    client: Optional[QdrantClient] = None,
    model: Optional[SentenceTransformer] = None,
) -> List[Dict]:
    """
    Busca fragmentos relevantes en las transcripciones indexadas.
    
    Args:
        query: Consulta en lenguaje natural
        top_k: Número de resultados
        channel_filter: Filtrar por canal (ej: "@code4AI")
        video_id_filter: Filtrar por video específico
        score_threshold: Score mínimo de similitud
        client: Cliente Qdrant
        model: Modelo de embedding
    
    Returns:
        Lista de dicts con 'text', 'video_id', 'title', 'channel', 'url', 'score'
    """
    if client is None:
        client = get_client()
    if model is None:
        model = get_model()
    
    # Generar embedding de la query
    query_vector = model.encode(query).tolist()
    
    # Construir filtro
    query_filter = None
    conditions = []
    
    if channel_filter:
        conditions.append(
            FieldCondition(key="channel", match=MatchValue(value=channel_filter))
        )
    if video_id_filter:
        conditions.append(
            FieldCondition(key="video_id", match=MatchValue(value=video_id_filter))
        )
    
    if conditions:
        query_filter = Filter(must=conditions)
    
    # Buscar en Qdrant
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        query_filter=query_filter,
        score_threshold=score_threshold,
    )
    
    # Formatear resultados
    fragments = []
    for r in results:
        payload = r.payload or {}
        fragments.append({
            "text": payload.get("text", ""),
            "video_id": payload.get("video_id", ""),
            "title": payload.get("title", ""),
            "channel": payload.get("channel", ""),
            "url": payload.get("url", ""),
            "chunk_index": payload.get("chunk_index", 0),
            "score": round(r.score, 4),
        })
    
    return fragments


def format_as_llm_context(fragments: List[Dict], query: str = "", max_tokens: int = 4000) -> str:
    """
    Formatea los fragmentos como contexto para un LLM.
    """
    if not fragments:
        return "No se encontraron fragmentos relevantes en las transcripciones."
    
    lines = []
    lines.append(f"# Contexto relevante de transcripciones de YouTube para: \"{query}\"")
    lines.append(f"# {len(fragments)} fragmentos encontrados\n")
    
    # Agrupar por video
    by_video = {}
    for f in fragments:
        vid = f["video_id"]
        if vid not in by_video:
            by_video[vid] = {"title": f["title"], "url": f["url"], "channel": f["channel"], "fragments": []}
        by_video[vid]["fragments"].append(f)
    
    total_chars = 0
    for vid, info in by_video.items():
        if total_chars > max_tokens * 4:  # ~4 chars por token
            break
        
        lines.append(f"\n## [{info['title']}]({info['url']})")
        lines.append(f"**Canal:** {info['channel']} | **Video:** {vid}")
        lines.append("")
        
        for f in info["fragments"]:
            text = f["text"]
            lines.append(f"> {text}")
            total_chars += len(text)
            if total_chars > max_tokens * 4:
                lines.append("> ...")
                break
        lines.append("")
    
    return "\n".join(lines)


def format_as_text(fragments: List[Dict]) -> str:
    """Formatea resultados como texto simple."""
    if not fragments:
        return "Sin resultados."
    
    lines = []
    for i, f in enumerate(fragments, 1):
        lines.append(f"[{i}] {f['title']} ({f['video_id']}) - score: {f['score']}")
        lines.append(f"    {f['text'][:200]}...")
        lines.append(f"    {f['url']}")
        lines.append("")
    
    return "\n".join(lines)


def get_stats(client: Optional[QdrantClient] = None) -> Dict:
    """Obtiene estadísticas de la colección."""
    if client is None:
        client = get_client()
    
    try:
        info = client.get_collection(COLLECTION_NAME)
        count = client.count(COLLECTION_NAME).count
        
        # Contar por canal
        all_points = client.scroll(collection_name=COLLECTION_NAME, limit=1000)[0]
        channels = {}
        videos = set()
        for p in all_points:
            ch = p.payload.get("channel", "unknown") if p.payload else "unknown"
            vid = p.payload.get("video_id", "") if p.payload else ""
            channels[ch] = channels.get(ch, 0) + 1
            if vid:
                videos.add(vid)
        
        return {
            "collection": COLLECTION_NAME,
            "total_points": count,
            "videos_indexados": len(videos),
            "canales": channels,
            "vector_size": info.config.params.vectors.size,
            "distance": str(info.config.params.vectors.distance),
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Consulta RAG sobre transcripciones de YouTube")
    parser.add_argument("query", nargs="?", help="Consulta en lenguaje natural")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help=f"Resultados (default: {DEFAULT_TOP_K})")
    parser.add_argument("--channel", help="Filtrar por canal")
    parser.add_argument("--video-id", help="Filtrar por video")
    parser.add_argument("--score-threshold", type=float, default=0.3, help="Score mínimo (default: 0.3)")
    parser.add_argument("--format", choices=["json", "text", "llm_context"], default="json",
                       help="Formato de salida (json, text, llm_context)")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas de la colección")
    args = parser.parse_args()
    
    if args.stats:
        stats = get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return
    
    if not args.query:
        parser.print_help()
        sys.exit(1)
    
    fragments = rag_query(
        query=args.query,
        top_k=args.top_k,
        channel_filter=args.channel,
        video_id_filter=args.video_id,
        score_threshold=args.score_threshold,
    )
    
    if args.format == "llm_context":
        print(format_as_llm_context(fragments, args.query))
    elif args.format == "text":
        print(format_as_text(fragments))
    else:
        print(json.dumps({
            "query": args.query,
            "results": len(fragments),
            "fragments": fragments,
        }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
