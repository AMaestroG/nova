#!/usr/bin/env python3
"""
Descarga masiva de transcripciones de @code4AI usando Playwright + proxies frescos.
Método: Navegador real → clic en "Show transcript" → capturar get_transcript → parsear.

USO: python3 batch_descargar_transcripciones.py
"""

import asyncio
import os
import json
import requests
import concurrent.futures
from playwright.async_api import async_playwright
from pathlib import Path

OUTPUT_DIR = Path("/home/opc/nova/colonia/documentacion/code4AI/transcripciones")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Videos prioritarios (ID, título corto)
VIDEOS = [
    ("ASyJgzGE2aw", "SKILL.md Quantum Error Codes"),
    ("gCUDDg3I1as", "AGI is Dead, SKILLS serve us better"),
    ("g3lh7U_rV9w", "Trace2Skill Qwen Agent Skill.md"),
    ("5L_tYKt2ENo", "End of Human-Defined Skills: AI Eigenvectors"),
    ("VdPwMYHVOWE", "AI Can Evolve Itself: HyEvo"),
    ("A2WrGENfdRI", "Self Evolving Dual AI Agent System"),
    ("XLOpRWLUymw", "AI Rewrite Itself: Darwin-Gödel HyperAgent"),
    ("jJ3vBj7Xufc", "AI Designed Its Own Memory: OmniMEM"),
    ("fDReoGlDXts", "MEMORY.md not real AI MEMORY"),
    ("ziaNZCtjuPI", "Words Instead of Weights: HERA"),
    ("hG5nCdgveWI", "Multi-Agent Prompt Engineering is Dead"),
    ("yOeVi3aQ9Kg", "Meta Harness: Every AI Needs a Harness"),
    ("CLjTCe_cvJs", "Better Cheaper RAG: Neuro-Sym Multi-hop"),
    ("21wj-SKesqc", "Knowledge Graphs vs Context Spaces"),
    ("7n5EVMtYA4I", "SuperIntelligence File System CORAL"),
    ("bECA_S805As", "No AI Agent Orchestration Needed?"),
    ("phfGmvYQCA8", "AI Harness Engineering"),
    ("NPN8s528714", "Text vs K-Graphs: Multi-RAG Failing"),
    ("cwpTV3MrRm4", "RAG Without Text: S-Path-RAG"),
    ("2WAucAspkZE", "AI Filesystem Unlock Intelligence"),
    ("BLrzMkF8trs", "Pluripotent AI: Stem Cells to Agents"),
    ("OGjzEF5SoGs", "Cognitive AI: The New Solution"),
    ("ArBpFCkYvl4", "Which of 8 Agents Can You Trust?"),
    ("beCj-7xjVmI", "Absolute Truths: Neuro-Symbolic AI"),
    ("kEUXyH5Vfjc", "META Safe & Trustworthy Agents: LogAct"),
    ("22aOG0mTlO0", "Temporal Predictive AI Agents: MILKYWAY"),
    ("5E3EAh43E4E", "Quantum Knowledge Graphs in AI"),
    ("SrHSjQkBIrY", "Test-Time Training & Invariant Topologies"),
    ("osupbje_OPA", "SFT+RL+RSA Tiny 4B Rivals Gemini 3"),
    ("OjQAOEUe_ng", "GraphRAG Redundant? Implicit Reasoning Graphs"),
]


def obtener_proxies_frescos(limit=50):
    """Obtiene proxies HTTP frescos y prueba cuáles funcionan con YouTube."""
    print("Obteniendo proxies...")
    try:
        r = requests.get(
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=elite",
            timeout=10
        )
        proxies = [p.strip() for p in r.text.split('\n') if p.strip()][:limit]
    except:
        return []
    
    print(f"  {len(proxies)} candidatos. Probando...")
    
    def test(p):
        try:
            r = requests.get(
                "https://www.youtube.com/",
                proxies={"http": f"http://{p}", "https": f"http://{p}"},
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            return p if len(r.text) > 50000 else None
        except:
            return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        results = list(ex.map(test, proxies))
    
    working = [r for r in results if r]
    print(f"  {len(working)} funcionales")
    return working


async def extraer_transcripcion(video_id, titulo, proxy_addr):
    """Extrae transcripción de un video usando Playwright + proxy."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_file = OUTPUT_DIR / f"{video_id}.txt"
    
    # Si ya existe, saltar
    if output_file.exists():
        size = output_file.stat().st_size
        print(f"  ⏭️  Ya descargado ({size} bytes)")
        return True
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    f'--proxy-server=http://{proxy_addr}',
                ]
            )
        except Exception as e:
            print(f"  ❌ Error lanzando navegador: {e}")
            return False
        
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
            
            print(f"    Navegando...")
            await page.goto(url, wait_until='networkidle', timeout=45000)
            await page.wait_for_timeout(3000)
            
            # Verificar título
            page_title = await page.title()
            if 'Sign in' in page_title or 'unavailable' in page_title.lower():
                print(f"    ⚠️  Página bloqueada: {page_title}")
                await browser.close()
                return False
            
            # Clic en "Show transcript"
            try:
                expand_btn = await page.query_selector('#expand')
                if expand_btn:
                    await expand_btn.click()
                    await page.wait_for_timeout(800)
                
                buttons = await page.query_selector_all('button')
                for btn in buttons:
                    try:
                        text = await btn.inner_text()
                        if 'transcript' in text.lower():
                            await btn.click()
                            await page.wait_for_timeout(4000)
                            break
                    except:
                        pass
            except:
                pass
            
            await browser.close()
            
            if not transcript_json:
                print(f"    ❌ No se capturó transcripción")
                return False
            
            # Parsear JSON de get_transcript
            data = json.loads(transcript_json)
            segments = []
            
            def find_segments(obj):
                if isinstance(obj, dict):
                    if 'transcriptSegmentRenderer' in obj:
                        r = obj['transcriptSegmentRenderer']
                        snippet = r.get('snippet', {})
                        text = snippet.get('text', '') or snippet.get('simpleText', '')
                        if not text and 'runs' in snippet:
                            text = ''.join(run.get('text', '') for run in snippet['runs'])
                        if text:
                            segments.append(text)
                    for v in obj.values():
                        find_segments(v)
                elif isinstance(obj, list):
                    for item in obj:
                        find_segments(item)
            
            find_segments(data)
            
            if not segments:
                print(f"    ❌ No se extrajeron segmentos")
                return False
            
            full_text = ' '.join(segments)
            
            with open(output_file, 'w') as f:
                f.write(f"# {titulo}\n")
                f.write(f"# URL: {url}\n")
                f.write(f"# Canal: @code4AI (Discover AI)\n")
                f.write(f"# Segmentos: {len(segments)}\n\n")
                f.write(full_text)
            
            print(f"    ✅ {len(full_text)} chars, {len(segments)} segmentos → {output_file.name}")
            return True
            
        except Exception as e:
            print(f"    ❌ Error: {type(e).__name__}: {str(e)[:100]}")
            return False
        finally:
            try:
                await browser.close()
            except:
                pass


async def main():
    print("=" * 60)
    print("DESCARGA MASIVA DE TRANSCRIPCIONES @code4AI")
    print("=" * 60)
    
    proxies = obtener_proxies_frescos(50)
    if not proxies:
        print("❌ No hay proxies disponibles. Abortando.")
        return
    
    exitosos = 0
    fallidos = 0
    proxy_idx = 0
    
    for i, (vid, titulo) in enumerate(VIDEOS, 1):
        print(f"\n[{i}/{len(VIDEOS)}] {titulo} ({vid})")
        
        # Rotar proxy
        proxy = proxies[proxy_idx % len(proxies)]
        proxy_idx += 1
        
        # Intentar hasta 3 veces con diferentes proxies
        for attempt in range(3):
            if attempt > 0:
                proxy = proxies[proxy_idx % len(proxies)]
                proxy_idx += 1
                print(f"    Reintento {attempt+1} con proxy {proxy}")
            
            try:
                result = await extraer_transcripcion(vid, titulo, proxy)
                if result:
                    exitosos += 1
                    break
            except Exception as e:
                print(f"    Error intento {attempt+1}: {e}")
        else:
            fallidos += 1
            print(f"  ❌ Falló después de 3 intentos")
    
    print(f"\n{'='*60}")
    print(f"RESUMEN: {exitosos} exitosos, {fallidos} fallidos de {len(VIDEOS)}")
    print(f"Transcripciones en: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
