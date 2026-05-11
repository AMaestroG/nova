#!/usr/bin/env python3
"""
Nova Auto-Archivist — Background Thesis Downloader
Continuously downloads UNAM theses from repositorio.tic.unam.mx
and processes them through the Knowledge Graph.

Runs quietly in the background, building Nova's knowledge base.
"""
import sys
import os
import time
import json
import subprocess
from urllib.request import urlopen, Request
from collections import deque

BASE_DSpace = "https://repositorio.tic.unam.mx"
OUT_DIR = "/home/opc/nova/data/tesis_unam"
DOWNLOADED_LOG = os.path.join(OUT_DIR, "downloaded.json")
os.makedirs(OUT_DIR, exist_ok=True)

# Load already downloaded
downloaded = set()
if os.path.exists(DOWNLOADED_LOG):
    with open(DOWNLOADED_LOG) as f:
        downloaded = set(json.load(f))

def discover_items(community_handle: str, limit: int = 20) -> list:
    """Discover items from a DSpace community browse page."""
    url = f"{BASE_DSpace}/handle/{community_handle}/browse?type=dateissued&rpp={limit}"
    req = Request(url, headers={"User-Agent": "Nova-Archivist/1.0"})
    try:
        resp = urlopen(req, timeout=30)
        html = resp.read().decode('utf-8', errors='ignore')
        
        # Extract handles from browse page
        import re
        handles = list(set(re.findall(r'href=\"/handle/(\d+/\d+)\"', html)))
        return handles
    except Exception as e:
        print(f"  Error discovering: {e}")
        return []

def download_pdf(handle: str) -> bool:
    """Download PDF for a given handle."""
    if handle in downloaded:
        return False
    
    # Get item page to find bitstream
    item_url = f"{BASE_DSpace}/handle/{handle}?show=full"
    req = Request(item_url, headers={"User-Agent": "Nova-Archivist/1.0"})
    
    try:
        resp = urlopen(req, timeout=30)
        html = resp.read().decode('utf-8', errors='ignore')
        
        # Look for PDF download link
        import re
        pdf_links = re.findall(r'href=\"(/bitstreams/[^\"]+)"', html)
        
        if pdf_links:
            pdf_url = BASE_DSpace + pdf_links[0]
            # Download
            pdf_req = Request(pdf_url, headers={"User-Agent": "Nova-Archivist/1.0"})
            pdf_resp = urlopen(pdf_req, timeout=60)
            
            # Get title for filename
            title_match = re.search(r'dc\.title.*?>(.*?)<', html)
            title = title_match.group(1).strip()[:50] if title_match else handle.replace('/', '_')
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            
            filename = f"{safe_title}.pdf"
            filepath = os.path.join(OUT_DIR, filename)
            
            with open(filepath, 'wb') as f:
                f.write(pdf_resp.read())
            
            downloaded.add(handle)
            size_kb = os.path.getsize(filepath) / 1024
            print(f"  ✓ Downloaded: {filename} ({size_kb:.0f} KB)")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"  ✗ Failed {handle}: {e}")
        return False

def save_progress():
    """Save download progress."""
    with open(DOWNLOADED_LOG, 'w') as f:
        json.dump(list(downloaded), f)

def run_discovery_cycle():
    """Run one discovery + download cycle."""
    # Communities to crawl
    communities = {
        "Análisis y automatización": "123456789/3622",
        "Aplicaciones especializadas": "123456789/3628",
        "IA generativa": "123456789/3597",
        "PLN": "123456789/3603",
        "Visión artificial": "123456789/3610"
    }
    
    total_new = 0
    
    for name, handle in communities.items():
        print(f"\n--- {name} ---")
        items = discover_items(handle, limit=30)
        print(f"  Found {len(items)} items")
        
        for item_handle in items:
            if item_handle not in downloaded:
                if download_pdf(item_handle):
                    total_new += 1
                    save_progress()
                time.sleep(2)  # Be nice to server
    
    return total_new

if __name__ == "__main__":
    print("=" * 60)
    print("Nova Auto-Archivist — UNAM Thesis Downloader")
    print(f"Repository: {BASE_DSpace}")
    print(f"Already downloaded: {len(downloaded)}")
    print("=" * 60)
    
    new = run_discovery_cycle()
    
    print(f"\n📚 Cycle complete: {new} new theses downloaded")
    print(f"📁 Total archive: {len(downloaded)} theses")
    print(f"📂 Location: {OUT_DIR}/")
