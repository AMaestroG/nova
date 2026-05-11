#!/usr/bin/env python3
"""
index_transcript.py — Indexa transcripciones de YouTube en Qdrant (base vectorial RAG).

Pipeline:
  1. Recibir transcripción (texto + metadata)
  2. Chunking: dividir en segmentos de ~500 chars con overlap de 100
  3. Embedding: generar vectores con sentence-transformers (all-MiniLM-L6-v2, 384-dim)
  4. Upsert en Qdrant: colección 'youtube_transcripts'
  5. Devolver IDs de vectores y stats

USO:
    python3 index_transcript.py --video-id ASyJgzGE2aw --title "SKILL.md" --file transcripcion.txt
    python3 index_transcript.py --video-id ASyJgzGE2aw --title "SKILL.md" --text "texto completo..."
    python3 index_transcript.py --batch indice_videos.json --transcript-dir ./transcripciones
"""

import sys
import os
import json
import argparse
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional

# Dependencias opcionales (se instalan si es necesario)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance, OptimizersConfigDiff
except ImportError:
    print("Instalando qdrant-client...", file=sys.stderr)
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "qdrant-client"], check=True)
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance, OptimizersConfigDiff

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Instalando sentence-transformers...", file=sys.stderr)
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "sentence-transformers"], check=True)
    from sentence_transformers import SentenceTransformer


# Configuración
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "youtube_transcripts"
VECTOR_SIZE = 384
CHUNK_SIZE = 500  # caracteres
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE = 50  # chunks por batch al upsert

# Cache global del modelo de embedding
_embedding_model = None

def get_embedding_model():
    """Carga el modelo de embedding (cacheado)."""
    global _embedding_model
    if _embedding_model is None:
        print(f"Cargando modelo: {EMBEDDING_MODEL}...", file=sys.stderr)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def get_qdrant_client():
    """Obtiene cliente de Qdrant."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection(client: QdrantClient):
    """Crea la colección si no existe."""
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        print(f"Creando colección: {COLLECTION_NAME}", file=sys.stderr)
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=1000,
            ),
        )
        # Crear índices de payload
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="video_id",
            field_schema="keyword",
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="channel",
            field_schema="keyword",
        )
        print(f"  Colección creada con índices", file=sys.stderr)
    return COLLECTION_NAME


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict]:
    """
    Divide el texto en chunks con overlap.
    
    Returns:
        Lista de dicts con 'text', 'index', 'start_char', 'end_char'
    """
    chunks = []
    start = 0
    text_len = len(text)
    chunk_idx = 0
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # Intentar cortar en un punto o espacio para no partir palabras
        if end < text_len:
            # Buscar el último espacio o puntuación en el rango [end-50, end]
            search_start = max(start, end - 50)
            last_good = end
            for i in range(end, search_start, -1):
                if text[i] in '.!?\n ':
                    last_good = i + 1
                    break
            end = last_good
        
        chunk_text_content = text[start:end].strip()
        if chunk_text_content:
            chunks.append({
                "text": chunk_text_content,
                "index": chunk_idx,
                "start_char": start,
                "end_char": end,
            })
            chunk_idx += 1
        
        start = end - overlap
        if start >= text_len:
            break
    
    return chunks


def generate_point_id(video_id: str, chunk_index: int) -> str:
    """Genera un ID único para un punto en Qdrant."""
    raw = f"{video_id}_{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def index_transcript(
    video_id: str,
    title: str,
    text: str,
    channel: str = "",
    url: str = "",
    client: Optional[QdrantClient] = None,
    model: Optional[SentenceTransformer] = None,
) -> Dict:
    """
    Indexa una transcripción en Qdrant.
    
    Args:
        video_id: ID del video de YouTube
        title: Título del video
        text: Texto completo de la transcripción
        channel: Nombre del canal (opcional)
        url: URL del video (opcional)
        client: Cliente Qdrant (si no se provee, se crea uno)
        model: Modelo de embedding (si no se provee, se carga)
    
    Returns:
        dict con 'points_created', 'chunks', 'collection'
    """
    if not text:
        return {"error": "No hay texto para indexar", "points_created": 0}
    
    if client is None:
        client = get_qdrant_client()
    if model is None:
        model = get_embedding_model()
    
    # Asegurar colección
    ensure_collection(client)
    
    # Chunking
    chunks = chunk_text(text)
    if not chunks:
        return {"error": "No se generaron chunks", "points_created": 0}
    
    print(f"  Chunks: {len(chunks)}", file=sys.stderr)
    
    # Generar embeddings en batches
    chunk_texts = [c["text"] for c in chunks]
    embeddings = model.encode(chunk_texts, batch_size=BATCH_SIZE, show_progress_bar=False)
    
    # Crear puntos
    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        point_id = generate_point_id(video_id, chunk["index"])
        payload = {
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "url": url or f"https://www.youtube.com/watch?v={video_id}",
            "chunk_index": chunk["index"],
            "start_char": chunk["start_char"],
            "end_char": chunk["end_char"],
            "text": chunk["text"],
            "indexed_at": time.time(),
        }
        points.append(PointStruct(
            id=point_id,
            vector=embedding.tolist(),
            payload=payload,
        ))
    
    # Upsert en batches
    total_points = len(points)
    for start_idx in range(0, total_points, BATCH_SIZE):
        batch = points[start_idx:start_idx + BATCH_SIZE]
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
            wait=True,
        )
    
    print(f"  ✅ {total_points} puntos indexados en '{COLLECTION_NAME}'", file=sys.stderr)
    
    return {
        "video_id": video_id,
        "title": title,
        "collection": COLLECTION_NAME,
        "chunks": len(chunks),
        "points_created": total_points,
        "chunk_size": CHUNK_SIZE,
        "embedding_model": EMBEDDING_MODEL,
    }


def index_from_file(video_id: str, title: str, filepath: str, channel: str = "", url: str = "") -> Dict:
    """Indexa una transcripción desde un archivo."""
    text = Path(filepath).read_text()
    # Quitar líneas de metadatos (las que empiezan con #)
    lines = text.split('\n')
    content_lines = [l for l in lines if not l.startswith('#')]
    text = '\n'.join(content_lines).strip()
    return index_transcript(video_id, title, text, channel=channel, url=url)


def batch_index(indice_json: str, transcript_dir: str) -> List[Dict]:
    """
    Indexa en lote todas las transcripciones de un índice JSON.
    
    Args:
        indice_json: Path al archivo JSON con lista de videos
        transcript_dir: Directorio con archivos .txt de transcripciones
    
    Returns:
        Lista de resultados por video
    """
    with open(indice_json) as f:
        data = json.load(f)
    
    videos = data.get("videos", data) if isinstance(data, dict) else data
    transcript_dir = Path(transcript_dir)
    
    client = get_qdrant_client()
    model = get_embedding_model()
    ensure_collection(client)
    
    results = []
    for video in videos:
        vid = video.get("id", video.get("video_id", ""))
        title = video.get("titulo", video.get("title", ""))
        channel = video.get("canal", video.get("channel", data.get("canal", "")))
        
        transcript_file = transcript_dir / f"{vid}.txt"
        if not transcript_file.exists():
            results.append({"video_id": vid, "error": "Transcripción no encontrada", "points_created": 0})
            continue
        
        text = transcript_file.read_text()
        # Limpiar metadatos
        lines = text.split('\n')
        content_lines = [l for l in lines if not l.startswith('#')]
        text = '\n'.join(content_lines).strip()
        
        if not text:
            results.append({"video_id": vid, "error": "Transcripción vacía", "points_created": 0})
            continue
        
        try:
            result = index_transcript(
                video_id=vid,
                title=title,
                text=text,
                channel=channel,
                url=video.get("url", f"https://www.youtube.com/watch?v={vid}"),
                client=client,
                model=model,
            )
            results.append(result)
            print(f"  ✅ {vid}: {result.get('points_created', 0)} puntos", file=sys.stderr)
        except Exception as e:
            results.append({"video_id": vid, "error": str(e), "points_created": 0})
            print(f"  ❌ {vid}: {e}", file=sys.stderr)
    
    total_points = sum(r.get("points_created", 0) for r in results)
    print(f"\nTotal: {total_points} puntos en {len(results)} videos", file=sys.stderr)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Indexar transcripciones en Qdrant")
    
    # Modo individual
    parser.add_argument("--video-id", help="ID del video de YouTube")
    parser.add_argument("--title", help="Título del video")
    parser.add_argument("--channel", default="", help="Nombre del canal")
    parser.add_argument("--url", default="", help="URL del video")
    
    # Fuente de texto (una de las dos)
    parser.add_argument("--file", help="Archivo de transcripción (.txt)")
    parser.add_argument("--text", help="Texto de transcripción (string)")
    
    # Modo batch
    parser.add_argument("--batch", help="Archivo JSON de índice (indice_videos.json)")
    parser.add_argument("--transcript-dir", help="Directorio con transcripciones .txt")
    
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()
    
    if args.batch:
        results = batch_index(args.batch, args.transcript_dir or ".")
    elif args.video_id and args.title and (args.file or args.text):
        if args.file:
            result = index_from_file(args.video_id, args.title, args.file, args.channel, args.url)
        else:
            result = index_transcript(args.video_id, args.title, args.text, args.channel, args.url)
        results = [result]
    else:
        parser.print_help()
        sys.exit(1)
    
    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            status = f"✅ {r.get('points_created', 0)} puntos" if 'error' not in r else f"❌ {r['error']}"
            print(f"{r.get('video_id', '?'):15s} {r.get('title', '?')[:50]:50s} {status}")


if __name__ == "__main__":
    main()
