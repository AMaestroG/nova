#!/usr/bin/env python3
"""
DSpace Crawler for UNAM AI Repository (repositorio.tic.unam.mx)
Fetches metadata from all IA collections and saves structured JSON.
"""
import json
import time
import sys
import os
from urllib.request import urlopen, Request
from urllib.parse import quote

BASE = "https://repositorio.tic.unam.mx/rest"
OUT_DIR = "/home/opc/nova/data/unam_ia"
HEADERS = {"Accept": "application/json"}
DELAY = 0.3

os.makedirs(OUT_DIR, exist_ok=True)

def fetch_json(url):
    if url.startswith('/'):
        url = BASE.rstrip('/') + url
    req = Request(url, headers=HEADERS)
    try:
        resp = urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ERROR: {url} -> {e}")
        return None

def get_ia_communities():
    """Find the 5 IA subcommunities under the IA parent community."""
    # First get all communities
    all_comms = fetch_json(f"{BASE}/communities/")
    if not all_comms:
        return []
    
    ia_comms = []
    for c in all_comms:
        name = c.get("name", "")
        count = c.get("countItems", 0)
        if count > 0 and name in [
            "Análisis y automatización",
            "Aplicaciones especializadas", 
            "IA generativa",
            "Procesamiento del Lenguaje Natural (PLN)",
            "Visión artificial"
        ]:
            ia_comms.append(c)
            print(f"Found: {name} ({count} items) -> {c['link']}")
    
    return ia_comms

def get_collections(community_link):
    """Get collections within a community."""
    comm = fetch_json(community_link)
    if not comm:
        return []
    
    collections = []
    # Check subcommunities
    for sub in comm.get("subcommunities", []):
        sub_data = fetch_json(f"{BASE}/communities/{sub['uuid']}")
        if sub_data:
            for col in sub_data.get("collections", []):
                col_data = fetch_json(f"{BASE}/collections/{col['uuid']}")
                if col_data:
                    collections.append(col_data)
    
    # Direct collections
    for col in comm.get("collections", []):
        col_data = fetch_json(f"{BASE}/collections/{col['uuid']}")
        if col_data:
            collections.append(col_data)
    
    return collections

def get_items(collection_uuid, limit=500, offset=0):
    """Fetch items from a collection."""
    items = []
    while True:
        url = f"{BASE}/collections/{collection_uuid}/items?limit={min(limit, 100)}&offset={offset}"
        data = fetch_json(url)
        if not data or len(data) == 0:
            break
        items.extend(data)
        offset += len(data)
        if len(data) < 100:
            break
        time.sleep(DELAY)
    return items

def extract_metadata(item):
    """Extract key metadata from a DSpace item."""
    meta = {
        "uuid": item.get("uuid"),
        "handle": item.get("handle"),
        "name": item.get("name"),
        "type": item.get("type"),
        "archived": item.get("archived"),
        "withdrawn": item.get("withdrawn"),
        "lastModified": item.get("lastModified"),
        "metadata": {}
    }
    
    for entry in item.get("metadata", []):
        key = entry.get("key")
        value = entry.get("value")
        lang = entry.get("language")
        if key not in meta["metadata"]:
            meta["metadata"][key] = []
        meta["metadata"][key].append(value)
    
    return meta

def crawl_all():
    """Main crawl function."""
    print("=" * 60)
    print("DSpace UNAM-IA Crawler")
    print("=" * 60)
    
    ia_comms = get_ia_communities()
    print(f"\nFound {len(ia_comms)} IA communities\n")
    
    all_items = []
    
    for comm in ia_comms:
        name = comm["name"]
        count = comm["countItems"]
        print(f"\n--- {name} ({count} items) ---")
        
        collections = get_collections(comm["link"])
        print(f"  Collections: {len(collections)}")
        
        comm_items = []
        for col in collections:
            col_name = col.get("name", "unknown")
            col_uuid = col.get("uuid")
            num = col.get("numberItems", 0)
            print(f"  Fetching: {col_name} ({num} items)...")
            
            items = get_items(col_uuid)
            for item in items:
                meta = extract_metadata(item)
                meta["community"] = name
                meta["collection"] = col_name
                comm_items.append(meta)
            
            time.sleep(DELAY)
        
        all_items.extend(comm_items)
        
        # Save per-community
        fname = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("ñ", "n").replace("á", "a")
        with open(f"{OUT_DIR}/{fname}.json", "w") as f:
            json.dump(comm_items, f, ensure_ascii=False, indent=2)
        print(f"  Saved {len(comm_items)} items to {fname}.json")
    
    # Save all combined
    with open(f"{OUT_DIR}/all_items.json", "w") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"TOTAL: {len(all_items)} items across {len(ia_comms)} communities")
    print(f"Saved to: {OUT_DIR}/")
    print(f"{'=' * 60}")
    
    return all_items

def quick_summary():
    """Print a quick summary of already-crawled data."""
    if not os.path.exists(f"{OUT_DIR}/all_items.json"):
        print("No data yet. Run crawl_all() first.")
        return
    
    with open(f"{OUT_DIR}/all_items.json") as f:
        items = json.load(f)
    
    print(f"\n{'=' * 60}")
    print(f"UNAM-IA Repository Summary")
    print(f"{'=' * 60}")
    print(f"Total items: {len(items)}")
    
    # By community
    from collections import Counter
    comms = Counter(i.get("community") for i in items)
    for comm, count in comms.most_common():
        print(f"  {comm}: {count}")
    
    # By type
    types = Counter()
    for i in items:
        t = i["metadata"].get("dc.type", ["unknown"])[0]
        types[t] += 1
    print(f"\nBy type:")
    for t, count in types.most_common():
        print(f"  {t}: {count}")
    
    # Date range
    dates = []
    for i in items:
        d = i["metadata"].get("dc.date.issued", [])
        if d:
            try:
                dates.append(int(d[0][:4]))
            except:
                pass
    if dates:
        print(f"\nDate range: {min(dates)} - {max(dates)}")
    
    # Keywords
    keywords = Counter()
    for i in items:
        for kw in i["metadata"].get("dc.subject.keywords", []):
            if kw and len(kw) > 3:
                keywords[kw.lower()] += 1
    print(f"\nTop 20 keywords:")
    for kw, count in keywords.most_common(20):
        print(f"  {kw}: {count}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        quick_summary()
    else:
        crawl_all()
        quick_summary()
