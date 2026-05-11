#!/usr/bin/env python3
"""
youtube_pipeline.py — Pipeline completo: buscar → extraer → indexar → consultar.

Flujo principal orquestado por el agente YOUTUBE.

USO:
    # Indexar canal completo
    python3 youtube_pipeline.py pipeline --channel @code4AI --limit 10
    
    # Solo buscar
    python3 youtube_pipeline.py search --channel @code4AI
    
    # Solo extraer
    python3 youtube_pipeline.py extract --video-id ASyJgzGE2aw
    
    # Solo indexar (transcripciones ya extraídas)
    python3 youtube_pipeline.py index --transcript-dir ./transcripciones --indice indice_videos.json
    
    # Consultar
    python3 youtube_pipeline.py query "How do SKILL.md files work?"
    
    # Indexar con modo ligero (sin embeddings, solo texto)
    python3 youtube_pipeline.py index-light --transcript-dir ./transcripciones
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from search_channel import search_channel
from extract_transcript import extract_transcript


def cmd_search(args):
    """Buscar videos de un canal."""
    result = search_channel(args.channel, limit=args.limit)
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Índice guardado en: {args.output}")
    
    print(f"\nCanal: {result.get('canal', '?')}")
    print(f"Videos: {result.get('total_videos', 0)}")
    
    for v in result.get('videos', [])[:10]:
        print(f"  {v['id']} | {v['titulo'][:70]} | {v['duracion_s']}s")
    
    if result.get('total_videos', 0) > 10:
        print(f"  ... y {result['total_videos'] - 10} más")
    
    return result


def cmd_extract(args):
    """Extraer transcripción de un video."""
    result = extract_transcript(
        args.video_id,
        output_dir=args.output_dir or str(SCRIPT_DIR.parent.parent.parent / "documentacion" / "code4AI" / "transcripciones"),
        cookies_file=args.cookies,
    )
    
    if result.get("texto"):
        print(f"\n✅ Transcripción extraída: {result['video_id']}")
        print(f"   Archivo: {result.get('archivo', '?')}")
        print(f"   Tamaño: {result.get('texto_length', len(result.get('texto', '')))} chars")
        print(f"   Segmentos: {result.get('segmentos', '?')}")
        if result.get('texto'):
            print(f"\nPreview:\n{result['texto'][:500]}...")
    else:
        print(f"\n❌ Error: {result.get('error', 'Desconocido')}")
    
    return result


def cmd_index(args):
    """Indexar transcripciones en Qdrant."""
    from index_transcript import batch_index
    
    results = batch_index(
        args.indice,
        args.transcript_dir,
    )
    
    total = sum(r.get('points_created', 0) for r in results)
    errors = [r for r in results if 'error' in r]
    
    print(f"\nIndexación completada:")
    print(f"  Videos procesados: {len(results)}")
    print(f"  Puntos creados: {total}")
    print(f"  Errores: {len(errors)}")
    
    if errors:
        for e in errors:
            print(f"  ❌ {e.get('video_id', '?')}: {e.get('error', '?')}")
    
    return results


def cmd_index_light(args):
    """Indexar en modo ligero (sin embeddings, usando búsqueda de texto)."""
    import requests
    import hashlib
    import time
    
    transcript_dir = Path(args.transcript_dir)
    indice_file = Path(args.indice) if args.indice else None
    
    # Cargar índice si existe
    videos_meta = {}
    if indice_file and indice_file.exists():
        with open(indice_file) as f:
            data = json.load(f)
        for v in data.get('videos', []):
            videos_meta[v['id']] = v
    
    QDRANT_URL = "http://localhost:6333"
    COLLECTION = "youtube_transcripts"
    
    # Asegurar colección
    r = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}")
    if r.status_code != 200:
        requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION}",
            json={
                "vectors": {"size": 1, "distance": "Cosine"},
                "hnsw_config": {"m": 8, "ef_construct": 50},
            }
        )
        print(f"Colección '{COLLECTION}' creada (modo ligero)")
    
    total = 0
    for f in sorted(transcript_dir.glob("*.txt")):
        if f.name.startswith('_'):
            continue
        
        video_id = f.stem
        text = f.read_text()
        lines = [l for l in text.split('\n') if not l.startswith('#')]
        text = '\n'.join(lines).strip()
        
        if not text:
            continue
        
        meta = videos_meta.get(video_id, {})
        title = meta.get('titulo', meta.get('title', video_id))
        
        # Chunking simple
        words = text.split()
        chunk_size = 200  # palabras
        chunks = []
        for i in range(0, len(words), chunk_size - 20):
            chunk = ' '.join(words[i:i+chunk_size])
            if chunk:
                chunks.append(chunk)
        
        print(f"  {video_id}: {len(chunks)} chunks (modo ligero)")
        
        points = []
        for idx, chunk in enumerate(chunks[:50]):  # Limitar a 50 chunks en modo ligero
            point_id = hashlib.md5(f"{video_id}_light_{idx}".encode()).hexdigest()
            points.append({
                "id": point_id,
                "vector": [0.0],  # Vector dummy
                "payload": {
                    "video_id": video_id,
                    "title": title,
                    "channel": meta.get('canal', '@unknown'),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "chunk_index": idx,
                    "text": chunk,
                    "indexed_at": time.time(),
                    "index_mode": "light",
                }
            })
        
        # Upsert
        if points:
            requests.put(
                f"{QDRANT_URL}/collections/{COLLECTION}/points?wait=true",
                json={"points": points}
            )
            total += len(points)
    
    print(f"\n✅ Total: {total} puntos (modo ligero)")
    
    # Verificar
    r = requests.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/count", json={})
    if r.status_code == 200:
        print(f"   Puntos en colección: {r.json()['result']['count']}")
    
    return total


def cmd_query(args):
    """Consultar conocimiento indexado."""
    # Intentar importar; si falla, usar modo texto
    try:
        from youtube_rag_query import rag_query, format_as_llm_context
        fragments = rag_query(
            query=args.query,
            top_k=args.top_k,
            channel_filter=args.channel,
        )
        
        if args.format == "llm_context":
            print(format_as_llm_context(fragments, args.query))
        else:
            for i, f in enumerate(fragments, 1):
                print(f"[{i}] {f['title']} (score: {f['score']})")
                print(f"    {f['text'][:300]}...")
                print(f"    {f['url']}\n")
    except ImportError:
        print("⚠️  Qdrant no disponible. Usando búsqueda en archivos...")
        cmd_grep(args)


def cmd_grep(args):
    """Búsqueda de respaldo: grep sobre archivos de transcripción."""
    import re
    transcript_dir = Path(os.environ.get(
        "YOUTUBE_TRANSCRIPT_DIR",
        "/home/opc/nova/colonia/documentacion/code4AI/transcripciones"
    ))
    
    query_words = args.query.lower().split()
    results = []
    
    for f in transcript_dir.glob("*.txt"):
        if f.name.startswith('_'):
            continue
        
        text = f.read_text().lower()
        score = sum(1 for w in query_words if w in text)
        if score > 0:
            # Encontrar fragmentos relevantes
            for w in query_words:
                idx = text.find(w)
                if idx >= 0:
                    start = max(0, idx - 150)
                    end = min(len(text), idx + 300)
                    fragment = text[start:end]
                    results.append({
                        "video_id": f.stem,
                        "score": score,
                        "fragment": fragment,
                    })
                    break
    
    results.sort(key=lambda r: r["score"], reverse=True)
    
    for i, r in enumerate(results[:args.top_k], 1):
        print(f"[{i}] {r['video_id']} (score: {r['score']})")
        print(f"    ...{r['fragment']}...")
        print()


def cmd_pipeline(args):
    """Pipeline completo: buscar → extraer → indexar."""
    channel = args.channel
    limit = args.limit
    
    print(f"=== PIPELINE YOUTUBE: {channel} ===\n")
    
    # 1. Buscar
    print("1/3 BUSCANDO videos del canal...")
    search_result = search_channel(channel, limit=limit)
    videos = search_result.get('videos', [])
    print(f"   {len(videos)} videos encontrados\n")
    
    # 2. Extraer transcripciones
    print("2/3 EXTRAYENDO transcripciones...")
    output_dir = args.output_dir or str(
        SCRIPT_DIR.parent.parent.parent / "documentacion" / "code4AI" / "transcripciones"
    )
    
    extraidos = 0
    for i, v in enumerate(videos, 1):
        vid = v['id']
        print(f"  [{i}/{len(videos)}] {v['titulo'][:60]}")
        
        result = extract_transcript(vid, output_dir=output_dir)
        if result.get('texto'):
            extraidos += 1
        else:
            print(f"    ⚠️ Falló: {result.get('error', '?')}")
    
    print(f"\n   {extraidos}/{len(videos)} transcripciones extraídas\n")
    
    # 3. Indexar
    if extraidos > 0:
        print("3/3 INDEXANDO en Qdrant...")
        # Guardar índice actualizado
        indice_path = Path(output_dir).parent / "indice_videos.json"
        with open(indice_path, 'w') as f:
            json.dump(search_result, f, indent=2, ensure_ascii=False)
        
        # Indexar en modo ligero
        cmd_index_light(argparse.Namespace(
            transcript_dir=output_dir,
            indice=str(indice_path),
        ))
    
    print(f"\n=== PIPELINE COMPLETADO ===")


def main():
    parser = argparse.ArgumentParser(description="YouTube Pipeline - Agente YOUTUBE de Nova")
    sub = parser.add_subparsers(dest="command", help="Comandos")
    
    # search
    p_search = sub.add_parser("search", help="Buscar videos de un canal")
    p_search.add_argument("--channel", required=True, help="@handle o URL del canal")
    p_search.add_argument("--limit", type=int, default=200)
    p_search.add_argument("--output", "-o", help="Archivo JSON de salida")
    
    # extract
    p_extract = sub.add_parser("extract", help="Extraer transcripción")
    p_extract.add_argument("--video-id", required=True, help="ID o URL del video")
    p_extract.add_argument("--output-dir", help="Directorio de salida")
    p_extract.add_argument("--cookies", help="Archivo cookies.txt")
    
    # index
    p_index = sub.add_parser("index", help="Indexar en Qdrant (embeddings)")
    p_index.add_argument("--indice", required=True, help="Archivo JSON de índice")
    p_index.add_argument("--transcript-dir", required=True, help="Directorio con .txt")
    
    # index-light
    p_light = sub.add_parser("index-light", help="Indexar en Qdrant (modo ligero, sin embeddings)")
    p_light.add_argument("--transcript-dir", required=True)
    p_light.add_argument("--indice", help="Archivo JSON de índice")
    
    # query
    p_query = sub.add_parser("query", help="Consultar conocimiento indexado")
    p_query.add_argument("query", help="Consulta en lenguaje natural")
    p_query.add_argument("--top-k", type=int, default=10)
    p_query.add_argument("--channel", help="Filtrar por canal")
    p_query.add_argument("--format", choices=["text", "llm_context"], default="text")
    
    # pipeline (full)
    p_pipe = sub.add_parser("pipeline", help="Pipeline completo")
    p_pipe.add_argument("--channel", required=True)
    p_pipe.add_argument("--limit", type=int, default=10)
    p_pipe.add_argument("--output-dir")
    
    args = parser.parse_args()
    
    if args.command == "search":
        cmd_search(args)
    elif args.command == "extract":
        cmd_extract(args)
    elif args.command == "index":
        cmd_index(args)
    elif args.command == "index-light":
        cmd_index_light(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "pipeline":
        cmd_pipeline(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
