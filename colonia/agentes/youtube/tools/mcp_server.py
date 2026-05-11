#!/usr/bin/env python3
"""
mcp_server.py — Servidor MCP (Model Context Protocol) para el agente YOUTUBE.

Expone 4 herramientas via stdin/stdout JSON-RPC:
  - youtube_search_channel: Buscar videos de un canal
  - youtube_extract_transcript: Extraer transcripción
  - youtube_index_transcript: Indexar en Qdrant
  - youtube_rag_query: Consultar conocimiento indexado

Formato: JSON-RPC 2.0 sobre stdin/stdout
"""

import sys
import json
import os
import traceback

# Agregar scripts al path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from search_channel import search_channel as _search_channel
from extract_transcript import extract_transcript as _extract_transcript
from index_transcript import index_transcript, index_from_file, batch_index
from youtube_rag_query import rag_query, get_stats


def handle_request(request):
    """Maneja una solicitud JSON-RPC."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})
    
    handlers = {
        "youtube_search_channel": handle_search_channel,
        "youtube_extract_transcript": handle_extract_transcript,
        "youtube_index_transcript": handle_index_transcript,
        "youtube_rag_query": handle_rag_query,
        "youtube_stats": handle_stats,
        "tools/list": handle_list_tools,
        "initialize": handle_initialize,
    }
    
    handler = handlers.get(method)
    if not handler:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Método no encontrado: {method}"}}
    
    try:
        result = handler(params)
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}


def handle_initialize(params):
    return {
        "protocolVersion": "1.0",
        "serverInfo": {
            "name": "youtube-agent",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {}
        }
    }


def handle_list_tools(params):
    return {
        "tools": [
            {
                "name": "youtube_search_channel",
                "description": "Busca y lista todos los videos de un canal de YouTube. Devuelve ID, título, duración, URL.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "URL del canal o @handle (ej: @code4AI)"},
                        "limit": {"type": "integer", "description": "Máximo de videos (default: 200)"}
                    },
                    "required": ["channel"]
                }
            },
            {
                "name": "youtube_extract_transcript",
                "description": "Extrae la transcripción automática de un video de YouTube. Usa Playwright + proxies.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string", "description": "ID del video o URL completa"},
                        "cookies_file": {"type": "string", "description": "Archivo cookies.txt (opcional, fallback)"}
                    },
                    "required": ["video_id"]
                }
            },
            {
                "name": "youtube_index_transcript",
                "description": "Indexa una transcripción en la base vectorial Qdrant para consulta RAG.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string"},
                        "title": {"type": "string"},
                        "text": {"type": "string", "description": "Texto de la transcripción"},
                        "channel": {"type": "string", "description": "Nombre del canal"}
                    },
                    "required": ["video_id", "title", "text"]
                }
            },
            {
                "name": "youtube_rag_query",
                "description": "Consulta semántica sobre transcripciones de YouTube indexadas. Devuelve fragmentos relevantes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Consulta en lenguaje natural"},
                        "top_k": {"type": "integer", "description": "Resultados (default: 10)"},
                        "channel": {"type": "string", "description": "Filtrar por canal"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "youtube_stats",
                "description": "Estadísticas de la colección de transcripciones indexadas.",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
    }


def handle_search_channel(params):
    channel = params.get("channel", "")
    limit = params.get("limit", 200)
    result = _search_channel(channel, limit=limit)
    # Truncar para no saturar
    if len(result.get("videos", [])) > 50:
        result["videos_truncados"] = True
        result["videos"] = result["videos"][:50]
    return result


def handle_extract_transcript(params):
    video_id = params.get("video_id", "")
    cookies_file = params.get("cookies_file")
    result = _extract_transcript(video_id, cookies_file=cookies_file)
    # No devolver el texto completo en la respuesta (muy grande)
    if result.get("texto"):
        result["texto_preview"] = result["texto"][:500]
        result["texto_length"] = len(result["texto"])
        del result["texto"]
    return result


def handle_index_transcript(params):
    video_id = params.get("video_id", "")
    title = params.get("title", "")
    text = params.get("text", "")
    channel = params.get("channel", "")
    url = params.get("url", "")
    
    result = index_transcript(
        video_id=video_id,
        title=title,
        text=text,
        channel=channel,
        url=url,
    )
    return result


def handle_rag_query(params):
    query = params.get("query", "")
    top_k = params.get("top_k", 10)
    channel = params.get("channel")
    
    fragments = rag_query(query=query, top_k=top_k, channel_filter=channel)
    
    return {
        "query": query,
        "results": len(fragments),
        "fragments": fragments,
    }


def handle_stats(params):
    return get_stats()


def main():
    """Loop principal: leer JSON-RPC de stdin, responder por stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            sys.stderr.write(f"JSON inválido: {line[:100]}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()
