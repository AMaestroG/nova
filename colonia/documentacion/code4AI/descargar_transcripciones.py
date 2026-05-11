#!/usr/bin/env python3
"""
Descarga transcripciones de los videos de @code4AI para la colonia Nova.
Requiere cookies de YouTube para sortear el bloqueo de IP cloud.

USO:
  1. Exporta cookies desde tu navegador a cookies.txt (formato Netscape)
  2. Coloca cookies.txt en /home/opc/nova/
  3. Ejecuta: python3 scripts/descargar_transcripciones_code4ai.py

Alternativa: usa --cookies-from-browser BRAVE (si hay navegador instalado)

Autor: Nova Homonexus
Fecha: 2026-05-10
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

COLONIA_DIR = Path("/home/opc/nova/colonia/documentacion/code4AI")
INDICE_FILE = COLONIA_DIR / "indice_videos.json"
TRANSCRIPCIONES_DIR = COLONIA_DIR / "transcripciones"
COOKIES_FILE = Path("/home/opc/nova/cookies.txt")

# Videos prioritarios (más relevantes para Nova) - IDs
PRIORITARIOS = [
    "ASyJgzGE2aw",  # SKILL.md Quantum Error Codes
    "g3lh7U_rV9w",  # Trace2Skill Qwen
    "gCUDDg3I1as",  # AGI is Dead, SKILLS
    "A2WrGENfdRI",  # Self Evolving Dual Agent
    "VdPwMYHVOWE",  # Topological Graph Self-Learning
    "XLOpRWLUymw",  # AI Rewrite Itself Darwin-Godel
    "jJ3vBj7Xufc",  # AI Designed Its Own Memory
    "fDReoGlDXts",  # MEMORY.md not real memory
    "ziaNZCtjuPI",  # Words Instead of Weights HERA
    "hG5nCdgveWI",  # Multi-Agent Prompt Engineering Dead
    "yOeVi3aQ9Kg",  # Meta Harness
    "CLjTCe_cvJs",  # Better Cheaper RAG
    "21wj-SKesqc",  # Knowledge Graphs vs Context
    "7n5EVMtYA4I",  # SuperIntelligence File System CORAL
    "bECA_S805As",  # No AI Orchestration Needed
    "NPN8s528714",  # Text vs K-Graphs
    "5L_tYKt2ENo",  # End of Human-Defined Skills
    "OjQAOEUe_ng",  # GraphRAG Now Redundant
    "cwpTV3MrRm4",  # RAG Without Text
    "phfGmvYQCA8",  # AI Harness Engineering
    "2WAucAspkZE",  # AI Filesystem Harness
    "BLrzMkF8trs",  # Pluripotent AI
    "OGjzEF5SoGs",  # Cognitive AI
    "22aOG0mTlO0",  # Temporal Predictive AI Agents
    "5E3EAh43E4E",  # Quantum Knowledge Graphs
    "ArBpFCkYvl4",  # Which Agent to Trust
    "kEUXyH5Vfjc",  # META Safe Agents LogAct
    "SrHSjQkBIrY",  # Test-Time Training
    "osupbje_OPA",  # SFT+RL+RSA Tiny 4B
    "beCj-7xjVmI",  # Absolute Truths Neuro-Symbolic
]


def encontrar_ytdlp():
    """Encuentra el binario de yt-dlp"""
    for path in ["yt-dlp", "/usr/local/bin/yt-dlp", "/usr/bin/yt-dlp"]:
        try:
            subprocess.run([path, "--version"], capture_output=True, check=True)
            return path
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    
    # Intentar instalarlo
    print("yt-dlp no encontrado. Instalando...")
    subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
    return "yt-dlp"


def descargar_transcripcion(video_id, ytdlp_path, cookies_args):
    """Descarga transcripción de un video"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = str(TRANSCRIPCIONES_DIR / f"{video_id}.%(ext)s")
    
    cmd = [
        ytdlp_path,
        "--skip-download",
        "--write-auto-subs",
        "--sub-lang", "en",
        "--convert-subs", "vtt",
        "-o", output_template,
    ]
    
    if cookies_args:
        cmd.extend(cookies_args)
    
    cmd.append(url)
    
    print(f"  Descargando {video_id}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        # Buscar el archivo generado
        for f in TRANSCRIPCIONES_DIR.glob(f"{video_id}*"):
            if f.suffix in ['.vtt', '.srt', '.txt']:
                return str(f)
        return "OK (archivo no encontrado)"
    else:
        error = result.stderr[-200:] if result.stderr else "Unknown error"
        return f"ERROR: {error}"


def extraer_texto_de_vtt(vtt_path):
    """Extrae texto limpio de un archivo VTT"""
    import re
    with open(vtt_path, 'r') as f:
        content = f.read()
    
    # Eliminar timestamps y metadatos VTT
    texto = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*\n', '', content)
    texto = re.sub(r'<[^>]+>', '', texto)  # Tags HTML
    texto = re.sub(r'WEBVTT.*\n', '', texto)
    texto = re.sub(r'NOTE.*\n', '', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    
    return texto.strip()


def main():
    parser = argparse.ArgumentParser(description="Descargar transcripciones de @code4AI")
    parser.add_argument("--cookies", type=str, help="Path al archivo cookies.txt")
    parser.add_argument("--cookies-from-browser", type=str, help="Navegador para extraer cookies (ej: brave, chrome, firefox)")
    parser.add_argument("--all", action="store_true", help="Descargar TODOS los videos (59)")
    parser.add_argument("--video", type=str, help="Descargar un video específico por ID")
    parser.add_argument("--limit", type=int, default=30, help="Límite de videos a descargar (default: 30 prioritarios)")
    parser.add_argument("--extract-text", action="store_true", help="Extraer texto limpio de VTTs ya descargados")
    args = parser.parse_args()
    
    os.makedirs(TRANSCRIPCIONES_DIR, exist_ok=True)
    
    ytdlp_path = encontrar_ytdlp()
    print(f"yt-dlp: {ytdlp_path}")
    
    # Configurar cookies
    cookies_args = []
    if args.cookies:
        cookies_args = ["--cookies", args.cookies]
    elif args.cookies_from_browser:
        cookies_args = ["--cookies-from-browser", args.cookies_from_browser]
    elif COOKIES_FILE.exists():
        cookies_args = ["--cookies", str(COOKIES_FILE)]
        print(f"Usando cookies de {COOKIES_FILE}")
    else:
        print("\n⚠️  ADVERTENCIA: Sin cookies. YouTube bloqueará las descargas desde IPs cloud.")
        print("   Exporta cookies a /home/opc/nova/cookies.txt o usa --cookies-from-browser\n")
    
    # Determinar qué videos descargar
    if args.video:
        videos_a_descargar = [args.video]
    elif args.all:
        with open(INDICE_FILE) as f:
            data = json.load(f)
        videos_a_descargar = [v["id"] for v in data["videos"]]
    else:
        videos_a_descargar = PRIORITARIOS[:args.limit]
    
    print(f"\n=== Descargando {len(videos_a_descargar)} transcripciones ===\n")
    
    exitosos = 0
    fallidos = 0
    
    for i, vid in enumerate(videos_a_descargar, 1):
        # Verificar si ya existe
        existentes = list(TRANSCRIPCIONES_DIR.glob(f"{vid}*"))
        if existentes and not args.extract_text:
            print(f"[{i}/{len(videos_a_descargar)}] {vid}: YA DESCARGADO ({existentes[0].name})")
            exitosos += 1
            continue
        
        resultado = descargar_transcripcion(vid, ytdlp_path, cookies_args)
        if resultado.startswith("ERROR"):
            print(f"[{i}/{len(videos_a_descargar)}] {vid}: {resultado}")
            fallidos += 1
        else:
            print(f"[{i}/{len(videos_a_descargar)}] {vid}: OK -> {os.path.basename(resultado) if resultado else 'OK'}")
            exitosos += 1
    
    print(f"\n=== RESUMEN ===")
    print(f"Exitosos: {exitosos}")
    print(f"Fallidos: {fallidos}")
    print(f"Total: {len(videos_a_descargar)}")
    
    # Extraer texto limpio de VTTs
    if args.extract_text:
        print("\n=== Extrayendo texto limpio de VTTs ===\n")
        for vtt_file in TRANSCRIPCIONES_DIR.glob("*.vtt"):
            txt_path = vtt_file.with_suffix(".txt")
            if txt_path.exists():
                continue
            texto = extraer_texto_de_vtt(str(vtt_file))
            with open(txt_path, 'w') as f:
                f.write(texto)
            print(f"  {vtt_file.name} -> {txt_path.name} ({len(texto)} chars)")


if __name__ == "__main__":
    main()
