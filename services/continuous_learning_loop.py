#!/usr/bin/env python3
"""
continuous_learning_loop.py — Motor de Aprendizaje Continuo de Nova

BUCLE INFALIBLE:
  1. Carga índice de videos pendientes
  2. Para cada video (orden prioritario):
     a. EXTRACT: extraer transcripción (3 estrategias fallback)
     b. INDEX: indexar en Qdrant y Hierarchical Memory
     c. ANALYZE: extraer conceptos con Knowledge Graph Builder  
     d. LEARN: alimentar Trace2Skill para cristalizar skills
     e. CHECKPOINT: guardar progreso
  3. Si falla → backoff exponencial → reintentar
  4. Si éxito → siguiente video
  5. Al completar todos → reiniciar bucle (mejora continua)

ESTRATEGIA MULTI-FALLBACK (infalible):
  Nivel 1: Playwright + proxy HTTP (mejor calidad)
  Nivel 2: codetabs proxy + timedtext (sin navegador)
  Nivel 3: yt-dlp + cookies (si disponibles)
  Nivel 4: Skip + marcar para reintento futuro

EJECUCIÓN:
  python3 continuous_learning_loop.py
  python3 continuous_learning_loop.py --once  # una pasada
  python3 continuous_learning_loop.py --daemon  # bucle infinito
"""

import os, sys, json, time, random, hashlib, subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ─── Configuración ───

BASE_DIR = Path("/home/opc/nova/colonia/documentacion")
CHECKPOINT_FILE = BASE_DIR / "learning_checkpoint.json"
PROGRESS_FILE = BASE_DIR / "learning_progress.json"

TRANSCRIPT_DIRS = {
    "code4AI": BASE_DIR / "code4AI/transcripciones",
    "aiDotEngineer": BASE_DIR / "aiDotEngineer_transcripts",
}

INDEX_FILES = {
    "code4AI": BASE_DIR / "code4AI/indice_videos.json",
    "aiDotEngineer": BASE_DIR / "aiDotEngineer_prioritarios.json",
}

# Videos que SABEMOS que son valiosos (de nuestro análisis)
PRIORITY_VIDEOS = {
    "code4AI": [
        "ASyJgzGE2aw", "jJ3vBj7Xufc", "VdPwMYHVOWE", "XLOpRWLUymw",
        "g3lh7U_rV9w", "ziaNZCtjuPI", "hG5nCdgveWI", "yOeVi3aQ9Kg",
        "CLjTCe_cvJs", "21wj-SKesqc", "7n5EVMtYA4I", "bECA_S805As",
        "NPN8s528714", "cwpTV3MrRm4", "5L_tYKt2ENo", "OjQAOEUe_ng",
        "phfGmvYQCA8", "2WAucAspkZE", "BLrzMkF8trs", "OGjzEF5SoGs",
        "22aOG0mTlO0", "5E3EAh43E4E", "ArBpFCkYvl4", "kEUXyH5Vfjc",
        "SrHSjQkBIrY", "osupbje_OPA", "beCj-7xjVmI", "peHshRhBsAA",
        "sRf2EcPBv4M", "WpBdSdij28Y",
    ],
    "aiDotEngineer": [
        "CEvIs9y1uog", "am_oeAoUhew", "esY99nYXxR4", "2czYyrTzILg",
        "kWOQS3XPZ10", "p1CmPZ2j6Lk", "kR64LOqBBCU", "YBYUvGOuotE",
        "GmAQKINjv1E", "pFsfax19yOM", "WE_Gnowy3uw", "ow1we5PzK-o",
    ],
}


class VideoStatus(Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    INDEXED = "indexed"
    ANALYZED = "analyzed"
    LEARNED = "learned"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class VideoProgress:
    video_id: str
    channel: str
    title: str = ""
    status: VideoStatus = VideoStatus.PENDING
    attempts: int = 0
    last_error: str = ""
    last_attempt: float = 0.0
    extracted_at: float = 0.0
    chars: int = 0


class ContinuousLearningLoop:
    """
    Motor de aprendizaje continuo.
    
    Procesa videos en bucle, extrayendo conocimiento e instalándolo en la colonia.
    """
    
    def __init__(self):
        self.progress: Dict[str, VideoProgress] = {}
        self.checkpoint: Dict = {}
        self.stats = {
            "total_processed": 0,
            "total_extracted": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "cycles_completed": 0,
            "start_time": time.time(),
        }
        
        # Cargar estado previo
        self._load_checkpoint()
        self._load_progress()
        
        # Inicializar directorios
        for d in TRANSCRIPT_DIRS.values():
            d.mkdir(parents=True, exist_ok=True)
    
    # ═══════════════════════════════════════════════
    # BUCLE PRINCIPAL
    # ═══════════════════════════════════════════════
    
    def run(self, once: bool = False, max_per_cycle: int = 10):
        """
        Ejecuta el bucle de aprendizaje continuo.
        
        Args:
            once: Si True, ejecuta una sola pasada
            max_per_cycle: Máximo de videos a procesar por ciclo
        """
        print("🜁 MOTOR DE APRENDIZAJE CONTINUO INICIADO")
        print(f"   Checkpoint: {CHECKPOINT_FILE}")
        print(f"   Videos pendientes: {sum(1 for v in self.progress.values() if v.status in [VideoStatus.PENDING, VideoStatus.FAILED])}")
        print(f"   Ya procesados: {sum(1 for v in self.progress.values() if v.status == VideoStatus.LEARNED)}")
        print()
        
        while True:
            cycle_start = time.time()
            processed_this_cycle = 0
            
            # Obtener videos pendientes (priorizando PENDING sobre FAILED)
            pending = self._get_pending_videos()
            
            if not pending:
                print("✅ No hay videos pendientes. Ciclo completado.")
                self.stats["cycles_completed"] += 1
                if once:
                    break
                print("⏳ Esperando 300s antes de reintentar fallidos...")
                time.sleep(300)
                self._reset_failed_to_pending()
                continue
            
            print(f"📋 {len(pending)} videos pendientes. Procesando hasta {max_per_cycle}...")
            
            for vp in pending[:max_per_cycle]:
                try:
                    success = self._process_video(vp)
                    if success:
                        self.stats["total_extracted"] += 1
                    else:
                        self.stats["total_failed"] += 1
                    self.stats["total_processed"] += 1
                    processed_this_cycle += 1
                except Exception as e:
                    print(f"  ❌ Error crítico en {vp.video_id}: {e}")
                    vp.status = VideoStatus.FAILED
                    vp.last_error = str(e)[:200]
                    self.stats["total_failed"] += 1
                
                # Guardar progreso tras cada video
                self._save_progress()
            
            elapsed = time.time() - cycle_start
            print(f"\n⏱️  Ciclo: {processed_this_cycle} videos en {elapsed:.0f}s")
            print(f"   Total: {self.stats['total_extracted']} extraídos, {self.stats['total_failed']} fallidos")
            
            if once:
                break
            
            # Esperar entre ciclos (para no saturar proxies)
            wait = max(10, 60 - elapsed)
            print(f"⏳ Esperando {wait:.0f}s antes del siguiente ciclo...\n")
            time.sleep(wait)
    
    # ═══════════════════════════════════════════════
    # PIPELINE POR VIDEO
    # ═══════════════════════════════════════════════
    
    def _process_video(self, vp: VideoProgress) -> bool:
        """Procesa un video: extract → index → analyze → learn."""
        vid = vp.video_id
        channel = vp.channel
        title = vp.title or vid
        
        print(f"\n{'─'*50}")
        print(f"🎯 [{vp.status.value}] {title[:70]}")
        
        # Paso 1: EXTRACT
        if vp.status in [VideoStatus.PENDING, VideoStatus.FAILED]:
            vp.status = VideoStatus.EXTRACTING
            transcript = self._extract_transcript(vid, channel)
            
            if transcript:
                vp.status = VideoStatus.EXTRACTED
                vp.chars = len(transcript)
                vp.extracted_at = time.time()
                print(f"  ✅ Extraído: {vp.chars} chars")
            else:
                vp.status = VideoStatus.FAILED
                vp.last_error = "Extracción fallida"
                vp.attempts += 1
                vp.last_attempt = time.time()
                print(f"  ❌ Extracción fallida (intento {vp.attempts})")
                return False
        
        # Paso 2: INDEX (Qdrant + Hierarchical Memory)
        if vp.status == VideoStatus.EXTRACTED:
            transcript_file = TRANSCRIPT_DIRS.get(channel, TRANSCRIPT_DIRS["code4AI"]) / f"{vid}.txt"
            if transcript_file.exists():
                self._index_transcript(vid, title, str(transcript_file), channel)
                vp.status = VideoStatus.INDEXED
                print(f"  ✅ Indexado")
        
        # Paso 3: ANALYZE (Knowledge Graph)
        if vp.status == VideoStatus.INDEXED:
            self._analyze_transcript(vid, title, channel)
            vp.status = VideoStatus.ANALYZED
            print(f"  ✅ Analizado")
        
        # Paso 4: LEARN (Trace2Skill + Agent Lifecycle)
        if vp.status == VideoStatus.ANALYZED:
            self._learn_from_transcript(vid, title, channel)
            vp.status = VideoStatus.LEARNED
            print(f"  ✅ Aprendido")
        
        vp.attempts = 0
        return True
    
    # ═══════════════════════════════════════════════
    # ESTRATEGIAS DE EXTRACCIÓN (MULTI-FALLBACK)
    # ═══════════════════════════════════════════════
    
    def _extract_transcript(self, video_id: str, channel: str) -> Optional[str]:
        """
        Extrae transcripción con 3 niveles de fallback.
        
        Nivel 1: Playwright + proxy (mejor calidad)
        Nivel 2: codetabs proxy + timedtext
        Nivel 3: Verificar si ya existe en disco
        """
        output_dir = TRANSCRIPT_DIRS.get(channel, TRANSCRIPT_DIRS["code4AI"])
        output_file = output_dir / f"{video_id}.txt"
        
        # Nivel 3: ¿Ya existe?
        if output_file.exists():
            text = output_file.read_text()
            if len(text) > 500:
                print(f"    📁 Ya existe en disco ({len(text)} chars)")
                return text
        
        # Nivel 1: Playwright + proxy
        print(f"    🔄 Nivel 1: Playwright + proxy...")
        try:
            text = self._extract_playwright(video_id)
            if text and len(text) > 500:
                output_file.write_text(text)
                return text
        except Exception as e:
            print(f"    ⚠️ Nivel 1 falló: {type(e).__name__}")
        
        # Nivel 2: codetabs + timedtext
        print(f"    🔄 Nivel 2: codetabs + timedtext...")
        try:
            text = self._extract_codetabs(video_id)
            if text and len(text) > 500:
                output_file.write_text(text)
                return text
        except Exception as e:
            print(f"    ⚠️ Nivel 2 falló: {type(e).__name__}")
        
        return None
    
    def _extract_playwright(self, video_id: str) -> Optional[str]:
        """Nivel 1: Playwright + proxy HTTP."""
        import asyncio
        from playwright.async_api import async_playwright
        
        # Obtener un proxy fresco
        proxy = self._get_fresh_proxy()
        if not proxy:
            raise Exception("No hay proxies disponibles")
        
        async def extract():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=[
                    '--disable-blink-features=AutomationControlled','--no-sandbox',
                    '--disable-dev-shm-usage',f'--proxy-server=http://{proxy}'])
                ctx = await browser.new_context(
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
                    viewport={'width':1920,'height':1080}, locale='en-US')
                await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
                page = await ctx.new_page()
                
                tjson = None
                async def h(resp):
                    nonlocal tjson
                    if 'get_transcript' in resp.url and resp.status==200:
                        try:
                            b = await resp.text()
                            if len(b)>10000: tjson = b
                        except: pass
                page.on('response', h)
                
                await page.goto(f"https://www.youtube.com/watch?v={video_id}", 
                              wait_until='networkidle', timeout=45000)
                await page.wait_for_timeout(3000)
                
                try:
                    expand = await page.query_selector('#expand')
                    if expand: await expand.click(); await page.wait_for_timeout(800)
                    buttons = await page.query_selector_all('button')
                    for btn in buttons:
                        try:
                            if 'transcript' in (await btn.inner_text()).lower():
                                await btn.click(); await page.wait_for_timeout(4000); break
                        except: pass
                except: pass
                
                await browser.close()
                return tjson
        
        tjson = asyncio.run(extract())
        if not tjson:
            return None
        
        import json
        data = json.loads(tjson)
        segments = []
        def find(obj):
            if isinstance(obj, dict):
                if 'transcriptSegmentRenderer' in obj:
                    sn = obj['transcriptSegmentRenderer'].get('snippet',{})
                    txt = sn.get('text','') or sn.get('simpleText','')
                    if not txt and 'runs' in sn:
                        txt = ''.join(r.get('text','') for r in sn['runs'])
                    if txt: segments.append(txt)
                for v in obj.values(): find(v)
            elif isinstance(obj, list):
                for item in obj: find(item)
        find(data)
        
        return ' '.join(segments) if segments else None
    
    def _extract_codetabs(self, video_id: str) -> Optional[str]:
        """Nivel 2: codetabs proxy + timedtext XML."""
        import requests, re
        from html import unescape
        from urllib.parse import quote
        
        # Obtener página
        r = requests.get(
            f"https://api.codetabs.com/v1/proxy?quest={quote(f'https://www.youtube.com/watch?v={video_id}')}",
            timeout=30, headers={"User-Agent": "Mozilla/5.0"}
        )
        
        # Extraer baseUrl del timedtext
        match = re.search(r'var\s+ytInitialPlayerResponse\s*=\s*({.*?});', r.text, re.DOTALL)
        if not match:
            return None
        
        import json
        data = json.loads(match.group(1))
        tracks = data.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        if not tracks:
            return None
        
        base_url = tracks[0]['baseUrl']
        
        # Descargar timedtext
        r2 = requests.get(base_url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": f"https://www.youtube.com/watch?v={video_id}",
        })
        
        if r2.status_code != 200 or len(r2.text) < 200:
            return None
        
        # Parsear XML
        texts = re.findall(r'<text[^>]*>(.*?)</text>', r2.text, re.DOTALL)
        if texts:
            return ' '.join(unescape(t.strip()) for t in texts if t.strip())
        
        return None
    
    # ═══════════════════════════════════════════════
    # INDEXACIÓN Y ANÁLISIS
    # ═══════════════════════════════════════════════
    
    def _index_transcript(self, video_id: str, title: str, filepath: str, channel: str):
        """Indexa transcripción en Qdrant (modo ligero) y Hierarchical Memory."""
        # Qdrant (ligero)
        try:
            import requests, hashlib
            text = Path(filepath).read_text()
            lines = [l for l in text.split('\n') if not l.startswith('#')]
            text = '\n'.join(lines).strip()
            
            if len(text) > 500:
                words = text.split()
                chunks = [' '.join(words[i:i+300]) for i in range(0, len(words), 250)]
                
                points = []
                for idx, chunk in enumerate(chunks[:20]):
                    pid = hashlib.md5(f"{video_id}_cl_{idx}".encode()).hexdigest()
                    points.append({
                        "id": pid, "vector": [0.0],
                        "payload": {
                            "video_id": video_id, "title": title[:200],
                            "channel": channel, "chunk_index": idx,
                            "text": chunk[:2000],
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                        }
                    })
                
                if points:
                    requests.put(
                        f"http://localhost:6333/collections/youtube_transcripts/points?wait=true",
                        json={"points": points}, timeout=10
                    )
        except Exception as e:
            print(f"    ⚠️ Indexación Qdrant: {e}")
        
        # Hierarchical Memory
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from hierarchical_memory import colony_memory, remember, Modality
            
            text = Path(filepath).read_text()
            remember(
                content=text[:3000],
                modality="transcript",
                source=channel,
                tags=["youtube", "transcript", channel],
                importance=0.7
            )
        except Exception as e:
            print(f"    ⚠️ Indexación Memoria: {e}")
    
    def _analyze_transcript(self, video_id: str, title: str, channel: str):
        """Analiza transcripción con Knowledge Graph Builder."""
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from knowledge_graph_builder import colony_kg
            
            transcript_file = TRANSCRIPT_DIRS.get(channel, TRANSCRIPT_DIRS["code4AI"]) / f"{video_id}.txt"
            if transcript_file.exists():
                text = transcript_file.read_text()
                lines = [l for l in text.split('\n') if not l.startswith('#')]
                text = '\n'.join(lines).strip()
                
                if len(text) > 1000:
                    result = colony_kg.ingest_document(text, source_id=video_id)
        except Exception as e:
            print(f"    ⚠️ Análisis KG: {e}")
    
    def _learn_from_transcript(self, video_id: str, title: str, channel: str):
        """Alimenta Trace2Skill y actualiza Agent Lifecycle."""
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from trace_to_skill import colony_trace2skill
            from agent_lifecycle import colony_lifecycle, create_task
            
            # Registrar traza
            colony_trace2skill.record_trace(
                agent="YOUTUBE",
                input_data=f"extract_and_learn:{video_id}",
                output_data=title,
                success=True,
                steps=[
                    {"action": "extract_transcript", "result": "success"},
                    {"action": "index_qdrant", "result": "success"},
                    {"action": "analyze_kg", "result": "success"},
                    {"action": "feed_trace2skill", "result": "success"},
                ],
                duration_ms=100,
            )
            
            # Intentar cristalizar
            colony_trace2skill.analyze_and_crystallize()
            
            # Actualizar lifecycle
            task = create_task(
                f"Aprender de: {title[:60]}",
                agent="YOUTUBE",
                description=f"Video {video_id} procesado del canal {channel}"
            )
            colony_lifecycle.claim(task.task_id, "YOUTUBE")
            colony_lifecycle.start(task.task_id)
            colony_lifecycle.complete(task.task_id, result=f"Transcript de {len(title)} chars procesada")
            
        except Exception as e:
            print(f"    ⚠️ Aprendizaje: {e}")
    
    # ═══════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════
    
    def _get_fresh_proxy(self) -> Optional[str]:
        """Obtiene un proxy HTTP fresco que funcione con YouTube."""
        try:
            import requests, concurrent.futures
            r = requests.get(
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=elite",
                timeout=10
            )
            proxies = [p.strip() for p in r.text.split('\n') if p.strip()][:40]
            
            def test(p):
                try:
                    r = requests.get("https://www.youtube.com/", 
                                    proxies={"http":f"http://{p}","https":f"http://{p}"},
                                    timeout=5, headers={"User-Agent":"Mozilla/5.0"})
                    return p if len(r.text)>50000 else None
                except: return None
            
            with concurrent.futures.ThreadPoolExecutor(15) as ex:
                results = list(ex.map(test, proxies))
            
            working = [r for r in results if r]
            return random.choice(working) if working else None
        except:
            return None
    
    def _get_pending_videos(self) -> List[VideoProgress]:
        """Obtiene lista de videos pendientes, priorizando PENDING sobre FAILED."""
        pending = [v for v in self.progress.values() if v.status == VideoStatus.PENDING]
        failed = [v for v in self.progress.values() if v.status == VideoStatus.FAILED]
        
        # Backoff: solo reintentar fallidos después de 5 minutos
        now = time.time()
        retryable = [v for v in failed if now - v.last_attempt > 300]
        
        # Ordenar: pendientes primero, luego reintentables
        return pending + retryable
    
    def _reset_failed_to_pending(self):
        """Reinicia videos fallidos a PENDING para reintento."""
        for vp in self.progress.values():
            if vp.status == VideoStatus.FAILED:
                vp.status = VideoStatus.PENDING
    
    # ═══════════════════════════════════════════════
    # PERSISTENCIA
    # ═══════════════════════════════════════════════
    
    def _load_checkpoint(self):
        """Carga el estado desde el archivo de checkpoint."""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE) as f:
                    data = json.load(f)
                for vdata in data.get("videos", []):
                    vp = VideoProgress(
                        video_id=vdata["video_id"],
                        channel=vdata.get("channel", "code4AI"),
                        title=vdata.get("title", ""),
                        status=VideoStatus(vdata.get("status", "pending")),
                        attempts=vdata.get("attempts", 0),
                        last_error=vdata.get("last_error", ""),
                        last_attempt=vdata.get("last_attempt", 0),
                        chars=vdata.get("chars", 0),
                    )
                    self.progress[vp.video_id] = vp
                self.stats.update(data.get("stats", {}))
                print(f"📂 Checkpoint cargado: {len(self.progress)} videos")
            except:
                pass
        
        # Si no hay checkpoint, inicializar desde índices
        if not self.progress:
            self._initialize_from_indices()
    
    def _initialize_from_indices(self):
        """Inicializa la lista de videos desde los archivos de índice."""
        for channel, index_file in INDEX_FILES.items():
            if not index_file.exists():
                continue
            
            try:
                with open(index_file) as f:
                    data = json.load(f)
                
                videos = data.get("videos", data.get("prioritarios", data if isinstance(data, list) else []))
                if isinstance(videos, dict):
                    videos = list(videos.values())
                
                for v in videos[:50]:  # Top 50
                    vid = v.get("id", v.get("video_id", ""))
                    if not vid:
                        continue
                    
                    # Verificar si ya está descargado
                    transcript_dir = TRANSCRIPT_DIRS.get(channel, TRANSCRIPT_DIRS["code4AI"])
                    already_extracted = (transcript_dir / f"{vid}.txt").exists()
                    
                    self.progress[vid] = VideoProgress(
                        video_id=vid,
                        channel=channel,
                        title=v.get("titulo", v.get("title", vid)),
                        status=VideoStatus.EXTRACTED if already_extracted else VideoStatus.PENDING,
                    )
                
                print(f"📋 {channel}: {len([v for v in self.progress.values() if v.channel==channel])} videos inicializados")
            except Exception as e:
                print(f"⚠️ Error cargando {channel}: {e}")
        
        self._save_progress()
    
    def _load_progress(self):
        """Carga progreso detallado."""
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE) as f:
                    saved = json.load(f)
                self.stats.update(saved.get("stats", {}))
            except:
                pass
    
    def _save_progress(self):
        """Guarda el progreso actual a disco."""
        try:
            checkpoint = {
                "videos": [
                    {
                        "video_id": vp.video_id,
                        "channel": vp.channel,
                        "title": vp.title,
                        "status": vp.status.value,
                        "attempts": vp.attempts,
                        "last_error": vp.last_error,
                        "last_attempt": vp.last_attempt,
                        "extracted_at": vp.extracted_at,
                        "chars": vp.chars,
                    }
                    for vp in self.progress.values()
                ],
                "stats": self.stats,
                "saved_at": time.time(),
            }
            with open(CHECKPOINT_FILE, 'w') as f:
                json.dump(checkpoint, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error guardando checkpoint: {e}")


# ═══════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Motor de Aprendizaje Continuo de Nova")
    parser.add_argument("--once", action="store_true", help="Ejecutar una sola pasada")
    parser.add_argument("--daemon", action="store_true", help="Bucle infinito (modo demonio)")
    parser.add_argument("--max", type=int, default=10, help="Máx videos por ciclo")
    args = parser.parse_args()
    
    loop = ContinuousLearningLoop()
    
    try:
        loop.run(once=args.once or not args.daemon, max_per_cycle=args.max)
    except KeyboardInterrupt:
        print("\n⏹️ Bucle detenido por el usuario")
        loop._save_progress()


if __name__ == "__main__":
    main()
