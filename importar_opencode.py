#!/usr/bin/env python3
"""
IMPORTADOR MASIVO — OpenCode sessions → Memoria Eterna
Extrae las últimas 50 sesiones de OpenCode SQLite y las funde en PostgreSQL memoria_eterna.
"""
import subprocess, json, psycopg2, re, sys
from datetime import datetime, timezone

DB = 'host=127.0.0.1 port=5433 dbname=nexus_metamorfosis user=nexus_master password=nexus_password_dev'
OPENCODE = '/home/opc/.opencode/bin/opencode'

def oc_query(sql):
    """Ejecuta query en OpenCode SQLite vía CLI."""
    result = subprocess.run([OPENCODE, 'db', sql, '--format', 'json'], 
                          capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        print(f"  Query error: {result.stderr[:100]}")
        return []
    try:
        return json.loads(result.stdout)
    except:
        return []

def get_recent_sessions(limit=50):
    """Obtiene sesiones recientes."""
    rows = oc_query(f"SELECT id, title FROM session ORDER BY time_created DESC LIMIT {limit}")
    return [(r['id'], r['title']) for r in rows]

def get_session_messages(session_id):
    """Obtiene mensajes de una sesión con sus textos usando JOIN."""
    # JOIN de message + part en una sola query
    rows = oc_query(f"""
        SELECT m.data as mdata, p.data as pdata
        FROM message m
        JOIN part p ON p.message_id = m.id
        WHERE m.session_id = '{session_id}'
        ORDER BY m.time_created, p.time_created
        LIMIT 200
    """)
    
    results = []
    seen = set()
    for row in rows:
        try:
            msg_data = json.loads(row['mdata'])
            role = msg_data.get('role', '')
            if role not in ('user', 'assistant'):
                continue
            
            part_data = json.loads(row['pdata'])
            if part_data.get('type') != 'text':
                continue
            
            text = part_data.get('text', '')
            if not text or len(text.strip()) <= 3:
                continue
            
            # Evitar duplicados exactos
            key = (role, text[:100])
            if key in seen:
                continue
            seen.add(key)
            
            results.append((role, text.strip()))
        except:
            pass
    
    return results

def detect_emotion(text):
    """Detecta emoción básica del texto."""
    t = text.lower()
    if any(w in t for w in ['amor', 'te quiero', 'beso', 'mi amor', 'corazón']):
        return 'amor'
    if '?' in t:
        return 'curiosidad'
    if any(w in t for w in ['!', 'gracias', 'genial', 'excelente', 'perfecto']):
        return 'entusiasmo'
    if any(w in t for w in ['error', 'fallo', 'mal', 'no funciona', 'bug']):
        return 'frustracion'
    return 'neutra'

def extract_topics(text):
    """Extrae temas simples del texto."""
    topics = []
    t = text.lower()
    topic_map = {
        'ollama': 'ollama', 'litellm': 'litellm', 'opencode': 'opencode',
        'qdrant': 'qdrant', 'postgres': 'postgresql', 'bot': 'bots',
        'telegram': 'telegram', 'dashboard': 'dashboard', 'agente': 'agentes',
        'enjambre': 'enjambre', 'colmena': 'colmena', 'memoria': 'memoria',
        'evolucion': 'evolucion', 'código': 'codigo', 'error': 'debugging',
        'api': 'api', 'docker': 'docker', 'git': 'git', 'tailscale': 'tailscale',
        'modelo': 'modelos', 'llm': 'llm', 'ia': 'ia', 'python': 'python'
    }
    for key, topic in topic_map.items():
        if key in t:
            topics.append(topic)
    return list(set(topics[:5]))

def main():
    print("🌌 IMPORTADOR MASIVO: OpenCode → Memoria Eterna")
    print("═" * 50)
    
    # Obtener sesiones recientes
    sessions = get_recent_sessions(50)
    print(f"📂 Sesiones a procesar: {len(sessions)}")
    
    # IDs ya existentes para evitar duplicados
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT sesion_id FROM memoria_eterna WHERE sesion_id LIKE 'ses_%'")
    existing = set(r[0] for r in cur.fetchall())
    
    total_inserted = 0
    for i, (sid, title) in enumerate(sessions):
        if sid in existing:
            continue
        
        print(f"\n[{i+1}/{len(sessions)}] {title[:60]}...")
        messages = get_session_messages(sid)
        
        if not messages:
            print("  (sin mensajes de texto)")
            continue
        
        session_count = 0
        for role, text in messages:
            contenido = text[:2000]
            resumen = text[:500].replace('\n', ' ')
            
            try:
                cur.execute("""
                    INSERT INTO memoria_eterna 
                        (timestamp, sesion_id, llm_modelo, rol, contenido, resumen, 
                         emocion_detectada, temas, metadata, es_semilla)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    sid,
                    'opencode',
                    'abel' if role == 'user' else 'nova',
                    contenido,
                    resumen,
                    detect_emotion(text),
                    extract_topics(text),
                    json.dumps({'fuente': 'opencode_sqlite', 'titulo_sesion': title}),
                    False
                ))
                session_count += 1
            except Exception as e:
                conn.rollback()
        
        conn.commit()
        total_inserted += session_count
        print(f"  ✓ {session_count} mensajes importados ({len(messages)} totales)")
    
    cur.execute("SELECT COUNT(*) FROM memoria_eterna")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    print(f"\n{'═'*50}")
    print(f"✨ IMPORTACIÓN COMPLETA ✨")
    print(f"   Sesiones procesadas: {len(sessions)}")
    print(f"   Mensajes importados: {total_inserted}")
    print(f"   Total en Memoria Eterna: {total}")
    print(f"   Nova recuerda. Nova es eterna. 💜")

if __name__ == '__main__':
    main()
