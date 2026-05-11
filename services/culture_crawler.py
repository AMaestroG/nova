#!/usr/bin/env python3
"""CULTURE CRAWLER — Internet autónomo recursivo para enriquecer la cultura de la colonia"""
import sys, os, time, json, random, hashlib, threading, subprocess, requests
sys.path.insert(0, os.path.dirname(__file__))

from hive_mind import hive_mind, think_hive, evolve_hive
from colony_core import persist, emit

print("🌐 CULTURE CRAWLER — Internet autónomo recursivo\n")

# Fuentes de cultura
CULTURE_SOURCES = [
    "https://arxiv.org/list/cs.AI/recent",
    "https://news.ycombinator.com/",
    "https://github.com/trending/python",
    "https://paperswithcode.com/",
]

stats = {"searches": 0, "found": 0, "indexed": 0, "cycles": 0}

def search_internet(query: str) -> list:
    """Busca en internet usando APIs públicas."""
    results = []
    try:
        # ArXiv search
        r = requests.get(f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results=5", timeout=10)
        if r.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.text)
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                title = entry.find('{http://www.w3.org/2005/Atom}title')
                summary = entry.find('{http://www.w3.org/2005/Atom}summary')
                if title is not None:
                    results.append(f"ARXIV: {title.text.strip()}")
                    if summary is not None:
                        results.append(f"  {summary.text.strip()[:200]}")
    except: pass
    
    try:
        # HackerNews
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        if r.status_code == 200:
            ids = r.json()[:5]
            for hid in ids:
                r2 = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{hid}.json", timeout=5)
                if r2.status_code == 200:
                    item = r2.json()
                    if item and 'title' in item:
                        results.append(f"HN: {item['title']}")
    except: pass
    
    return results

def recursive_search(seed: str, depth: int = 2, max_results: int = 20):
    """Búsqueda recursiva: sigue conexiones entre conceptos."""
    all_results = []
    seen = set()
    
    def _search(query, d):
        if d <= 0 or len(all_results) >= max_results:
            return
        
        results = search_internet(query)
        for r in results:
            if r not in seen and len(all_results) < max_results:
                seen.add(r)
                all_results.append(r)
                stats["found"] += 1
        
        # Extraer nuevos términos para búsqueda recursiva
        if d > 1:
            words = ' '.join(results).split()
            word_freq = {}
            for w in words:
                if len(w) > 5 and w.lower() not in ['which','their','about','these','there','would','could','should']:
                    word_freq[w] = word_freq.get(w, 0) + 1
            top_terms = sorted(word_freq.items(), key=lambda x: -x[1])[:3]
            for term, _ in top_terms:
                _search(f"{seed} {term}", d-1)
    
    _search(seed, depth)
    return all_results

def culture_worker():
    """Worker principal: búsqueda → indexación → propagación."""
    queries = [
        "artificial intelligence agents harness engineering",
        "large language models context engineering memory",
        "entropy intelligence multi-agent systems",
        "reinforcement learning self-improving AI",
    ]
    
    while True:
        try:
            query = random.choice(queries)
            stats["searches"] += 1
            stats["cycles"] += 1
            
            print(f"  🔍 [{stats['cycles']}] Buscando: {query[:60]}...")
            results = recursive_search(query, depth=2, max_results=10)
            
            for r in results:
                # Indexar en HiveMind
                hive_mind.vector_store.add(r, {"source": "internet", "query": query})
                hive_mind.memetic_engine._create_meme(r)
                stats["indexed"] += 1
            
            # Propagar a la colonia
            think_hive({"EXPLORADOR": 0.8, "MEMORIA": 0.6})
            
            # Evolucionar memes
            if stats["cycles"] % 5 == 0:
                evolve_hive(5)
                persist("culture_crawler", stats)
                emit("culture.crawled", {"found": stats["found"], "indexed": stats["indexed"]})
            
            if stats["cycles"] % 10 == 0:
                print(f"  📊 {stats['searches']} búsquedas | {stats['found']} encontrado | {stats['indexed']} indexado | {hive_mind.memetic_engine.get_stats()['population']} memes")
            
            time.sleep(60)  # 1 minuto entre búsquedas
            
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            time.sleep(120)

# ─── LANZAR ───
thread = threading.Thread(target=culture_worker, daemon=True, name="culture_crawler")
thread.start()
print(f"✅ Culture Crawler iniciado (thread: culture_crawler)")
print(f"   Búsquedas recursivas cada 60s")
print(f"   Indexación en HiveMind + Propagación memética\n")

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("\n⏹️ Culture Crawler detenido")
