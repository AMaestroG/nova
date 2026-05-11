#!/usr/bin/env python3
"""
search_channel.py — Busca y lista todos los videos de un canal de YouTube.

USO:
    python3 search_channel.py @code4AI
    python3 search_channel.py https://www.youtube.com/@code4AI
    python3 search_channel.py --channel-id UCw23-KB8Tz_YK1Jx7vTgquA

OUTPUT: JSON con lista de videos (id, título, duración, vistas, url)
"""

import sys
import json
import subprocess
import argparse
import os
from pathlib import Path

YTDLP_PATH = os.environ.get("YTDLP_PATH", "yt-dlp")

def install_ytdlp():
    """Asegura que yt-dlp esté instalado."""
    try:
        subprocess.run([YTDLP_PATH, "--version"], capture_output=True, check=True)
        return YTDLP_PATH
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Instalando yt-dlp...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"], check=True)
        return "yt-dlp"

def search_channel(channel_url, limit=200, cookies_file=None):
    """
    Busca todos los videos de un canal de YouTube.
    
    Args:
        channel_url: URL del canal o @handle (ej: @code4AI, https://youtube.com/@code4AI)
        limit: Número máximo de videos a recuperar
        cookies_file: Path a archivo cookies.txt (opcional)
    
    Returns:
        dict con clave 'videos' conteniendo lista de metadatos
    """
    ytdlp = install_ytdlp()
    
    # Normalizar URL
    if channel_url.startswith('@'):
        url = f"https://www.youtube.com/{channel_url}/videos"
    elif 'youtube.com' in channel_url or 'youtu.be' in channel_url:
        url = channel_url
    else:
        url = f"https://www.youtube.com/@{channel_url}/videos"
    
    cmd = [
        ytdlp,
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", str(limit),
        url,
        "--no-warnings",
        "--ignore-errors",
        "--skip-download",
    ]
    
    if cookies_file and os.path.exists(cookies_file):
        cmd.extend(["--cookies", cookies_file])
    
    env = os.environ.copy()
    # Asegurar que deno esté en PATH para extracción JS
    if os.path.exists(os.path.expanduser("~/.deno/bin")):
        env["PATH"] = os.path.expanduser("~/.deno/bin") + ":" + env.get("PATH", "")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    except subprocess.TimeoutExpired:
        return {"error": "Timeout al buscar el canal", "videos": []}
    except FileNotFoundError:
        return {"error": f"yt-dlp no encontrado. Instalar con: pip install yt-dlp", "videos": []}
    
    videos = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        try:
            data = json.loads(line)
            video = {
                "id": data.get("id", ""),
                "titulo": data.get("title", ""),
                "duracion_s": data.get("duration", 0) or 0,
                "vistas": data.get("view_count") or 0,
                "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
                "descripcion": (data.get("description", "") or "")[:500],
                "fecha": data.get("upload_date", ""),
            }
            videos.append(video)
        except json.JSONDecodeError:
            continue
    
    # Extraer nombre del canal del primer video o stderr
    channel_name = ""
    for line in result.stderr.split('\n'):
        if "Downloading playlist:" in line:
            channel_name = line.split("Downloading playlist:")[-1].strip()
            break
    
    return {
        "canal": channel_name or channel_url,
        "total_videos": len(videos),
        "videos": videos
    }

def main():
    parser = argparse.ArgumentParser(description="Buscar videos de un canal de YouTube")
    parser.add_argument("channel", help="URL del canal o @handle (ej: @code4AI)")
    parser.add_argument("--limit", type=int, default=200, help="Máximo de videos (default: 200)")
    parser.add_argument("--cookies", help="Archivo cookies.txt para autenticación")
    parser.add_argument("--output", "-o", help="Archivo JSON de salida")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Formato de salida")
    args = parser.parse_args()
    
    result = search_channel(args.channel, limit=args.limit, cookies_file=args.cookies)
    
    if args.format == "text":
        for v in result.get("videos", []):
            print(f"{v['id']} | {v['titulo'][:80]} | {v['duracion_s']}s | {v['url']}")
        print(f"\nTotal: {result['total_videos']} videos")
    else:
        output = json.dumps(result, indent=2, ensure_ascii=False)
        
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Guardado en: {args.output}", file=sys.stderr)
        
        print(output)

if __name__ == "__main__":
    main()
