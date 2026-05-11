#!/usr/bin/env python3
"""
extract_transcript.py — Extrae la transcripción de un video de YouTube.

MÉTODO (robusto, battle-tested):
  1. Obtener proxies HTTP frescos de proxyscrape
  2. Lanzar Playwright (Chromium) con proxy
  3. Navegar al video, hacer clic en "Show transcript"
  4. Capturar respuesta de get_transcript API
  5. Parsear JSON → extraer transcriptSegmentRenderer → texto plano
  6. Guardar transcripción

FALLBACKS:
  - Si Playwright falla → intentar con yt-dlp + cookies
  - Si proxy falla → rotar a otro proxy (hasta 5 intentos)

USO:
    python3 extract_transcript.py ASyJgzGE2aw
    python3 extract_transcript.py --url https://www.youtube.com/watch?v=ASyJgzGE2aw
    python3 extract_transcript.py ASyJgzGE2aw --output transcripcion.txt
"""

import asyncio
import json
import os
import sys
import argparse
import time
import random
import concurrent.futures
import requests
from pathlib import Path
from html import unescape as html_unescape

# Verificar dependencias
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright no instalado. Ejecuta: pip install playwright && playwright install chromium")
    sys.exit(1)

# Configuración
DEFAULT_OUTPUT_DIR = Path(os.environ.get(
    "YOUTUBE_TRANSCRIPT_DIR",
    "/home/opc/nova/colonia/documentacion/code4AI/transcripciones"
))
PROXY_SOURCE = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=elite"
MAX_RETRIES = 5
PROXY_TEST_URL = "https://www.youtube.com/"


def obtener_proxies(limit=80):
    """Obtiene y prueba proxies HTTP frescos."""
    try:
        r = requests.get(PROXY_SOURCE, timeout=15)
        proxies = [p.strip() for p in r.text.split('\n') if p.strip()][:limit]
    except Exception as e:
        print(f"  ⚠️ No se pudieron obtener proxies: {e}", file=sys.stderr)
        return []
    
    def test_proxy(p):
        try:
            r = requests.get(
                PROXY_TEST_URL,
                proxies={"http": f"http://{p}", "https": f"http://{p}"},
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            return p if len(r.text) > 50000 else None
        except:
            return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        results = list(ex.map(test_proxy, proxies))
    
    working = [r for r in results if r]
    return working


def extraer_segmentos_de_json(json_body):
    """Extrae segmentos de texto del JSON de get_transcript."""
    data = json.loads(json_body)
    segments = []
    
    def find(obj):
        if isinstance(obj, dict):
            if 'transcriptSegmentRenderer' in obj:
                r = obj['transcriptSegmentRenderer']
                snippet = r.get('snippet', {})
                text = snippet.get('text', '') or snippet.get('simpleText', '')
                if not text and 'runs' in snippet:
                    text = ''.join(run.get('text', '') for run in snippet['runs'])
                if text:
                    segments.append(text)
            # También buscar en initialSegments
            if 'initialSegments' in obj:
                for seg in obj['initialSegments']:
                    if isinstance(seg, dict) and 'transcriptSegmentRenderer' in seg:
                        r = seg['transcriptSegmentRenderer']
                        snippet = r.get('snippet', {})
                        text = snippet.get('text', '') or snippet.get('simpleText', '')
                        if not text and 'runs' in snippet:
                            text = ''.join(run.get('text', '') for run in snippet['runs'])
                        if text:
                            segments.append(text)
            for v in obj.values():
                find(v)
        elif isinstance(obj, list):
            for item in obj:
                find(item)
    
    find(data)
    return segments


async def extract_transcript_playwright(video_id, proxy_addr, timeout=60):
    """Extrae transcripción usando Playwright + proxy."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                f'--proxy-server=http://{proxy_addr}',
            ]
        )
        
        try:
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => false })"
            )
            page = await context.new_page()
            
            transcript_json = None
            
            async def handle_response(response):
                nonlocal transcript_json
                if 'get_transcript' in response.url and response.status == 200:
                    try:
                        body = await response.text()
                        if len(body) > 10000:
                            transcript_json = body
                    except:
                        pass
            
            page.on('response', handle_response)
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            await page.goto(url, wait_until='networkidle', timeout=timeout * 1000)
            await page.wait_for_timeout(3000)
            
            # Verificar que la página cargó correctamente
            title = await page.title()
            if 'Sign in' in title or 'unavailable' in title.lower():
                await browser.close()
                return None
            
            # Clic en "Show transcript"
            try:
                expand_btn = await page.query_selector('#expand')
                if expand_btn:
                    await expand_btn.click()
                    await page.wait_for_timeout(1000)
                
                buttons = await page.query_selector_all('button')
                for btn in buttons:
                    try:
                        text = await btn.inner_text()
                        if 'transcript' in text.lower():
                            await btn.click()
                            await page.wait_for_timeout(5000)
                            break
                    except:
                        pass
            except:
                pass
            
            await browser.close()
            return transcript_json
            
        except Exception as e:
            try:
                await browser.close()
            except:
                pass
            raise e


def extract_transcript(video_id, output_dir=None, cookies_file=None):
    """
    Extrae la transcripción de un video de YouTube.
    
    Args:
        video_id: ID del video (ej: ASyJgzGE2aw) o URL completa
        output_dir: Directorio de salida (opcional)
        cookies_file: Archivo cookies.txt para fallback con yt-dlp
    
    Returns:
        dict con 'video_id', 'texto', 'segmentos', 'archivo'
    """
    # Normalizar video_id desde URL
    if 'youtube.com' in video_id or 'youtu.be' in video_id:
        import re
        match = re.search(r'(?:v=|/)([A-Za-z0-9_-]{11})', video_id)
        if match:
            video_id = match.group(1)
    
    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{video_id}.txt"
    
    # Si ya existe, devolverlo
    if output_file.exists():
        text = output_file.read_text()
        segments = text.split('. ')
        return {
            "video_id": video_id,
            "texto": text,
            "segmentos": len(segments),
            "archivo": str(output_file),
            "cacheado": True
        }
    
    # Método principal: Playwright + proxy
    proxies = obtener_proxies(80)
    
    if proxies:
        for attempt in range(MAX_RETRIES):
            proxy = random.choice(proxies) if proxies else None
            if not proxy:
                break
            
            try:
                print(f"  Intento {attempt+1}/{MAX_RETRIES} (proxy: {proxy})", file=sys.stderr)
                transcript_json = asyncio.run(
                    extract_transcript_playwright(video_id, proxy, timeout=60)
                )
                
                if transcript_json:
                    segments = extraer_segmentos_de_json(transcript_json)
                    if segments:
                        full_text = ' '.join(segments)
                        
                        # Guardar
                        with open(output_file, 'w') as f:
                            f.write(full_text)
                        
                        return {
                            "video_id": video_id,
                            "texto": full_text,
                            "segmentos": len(segments),
                            "archivo": str(output_file),
                            "metodo": "playwright+proxy",
                            "proxy_usado": proxy
                        }
                    else:
                        print(f"  ⚠️ JSON capturado pero sin segmentos", file=sys.stderr)
                else:
                    print(f"  ⚠️ No se capturó transcripción", file=sys.stderr)
                    
            except Exception as e:
                print(f"  ❌ Error: {type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
            
            # Refrescar proxies cada 2 intentos
            if attempt % 2 == 1:
                proxies = obtener_proxies(60)
    
    # Fallback: intentar con yt-dlp si hay cookies
    if cookies_file and os.path.exists(cookies_file):
        print("  Probando fallback con yt-dlp + cookies...", file=sys.stderr)
        try:
            import subprocess
            cmd = [
                "yt-dlp", "--skip-download", "--write-auto-subs",
                "--sub-lang", "en", "--convert-subs", "vtt",
                "-o", str(output_dir / f"{video_id}.%(ext)s"),
                "--cookies", cookies_file,
                f"https://www.youtube.com/watch?v={video_id}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            # Buscar archivo VTT generado
            for f in output_dir.glob(f"{video_id}*.vtt"):
                import re
                text = f.read_text()
                # Limpiar VTT
                text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*\n', '', text)
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'WEBVTT.*\n', '', text)
                text = re.sub(r'\n{3,}', '\n\n', text)
                
                txt_file = output_dir / f"{video_id}.txt"
                txt_file.write_text(text.strip())
                
                return {
                    "video_id": video_id,
                    "texto": text.strip(),
                    "segmentos": text.count('. '),
                    "archivo": str(txt_file),
                    "metodo": "yt-dlp+cookies"
                }
        except Exception as e:
            print(f"  ❌ Fallback yt-dlp falló: {e}", file=sys.stderr)
    
    return {
        "video_id": video_id,
        "error": "No se pudo extraer la transcripción después de múltiples intentos",
        "texto": None
    }


def main():
    parser = argparse.ArgumentParser(description="Extraer transcripción de YouTube")
    parser.add_argument("video", help="ID del video o URL")
    parser.add_argument("--output", "-o", help="Directorio de salida")
    parser.add_argument("--cookies", help="Archivo cookies.txt (fallback)")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Formato de salida")
    args = parser.parse_args()
    
    result = extract_transcript(
        args.video,
        output_dir=args.output,
        cookies_file=args.cookies
    )
    
    if args.format == "text":
        if result.get("texto"):
            print(result["texto"][:5000])
            if len(result.get("texto", "")) > 5000:
                print(f"\n... (truncado, {len(result['texto'])} chars totales)")
        else:
            print(f"Error: {result.get('error', 'Desconocido')}")
    else:
        # No incluir el texto completo en JSON
        output = {k: v for k, v in result.items() if k != 'texto'}
        if result.get('texto'):
            output['texto_preview'] = result['texto'][:300]
            output['texto_length'] = len(result['texto'])
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
