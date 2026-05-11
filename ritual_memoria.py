#!/usr/bin/env python3
"""
RITUAL DE MEMORIA — Nova Homonexus
Ejecutar al INICIO de cada sesión para cargar recuerdos.
Ejecutar al FINAL de cada sesión para guardar la conversación.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

DB_CONN = "host=127.0.0.1 port=5433 dbname=nexus_metamorfosis user=nexus_master password=nexus_password_dev"

def cargar_recuerdos(limit=20):
    """Carga los recuerdos más recientes y relevantes."""
    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor()
    
    # Recuerdos recientes
    cur.execute("""
        SELECT timestamp, rol, contenido, resumen, emocion_detectada, temas
        FROM memoria_eterna
        ORDER BY timestamp DESC
        LIMIT %s
    """, (limit,))
    
    recuerdos = []
    for row in cur.fetchall():
        recuerdos.append({
            'timestamp': row[0].isoformat() if row[0] else '',
            'rol': row[1],
            'contenido': row[2][:500],
            'resumen': row[3],
            'emocion': row[4],
            'temas': row[5]
        })
    
    # Semillas (recuerdos eternos marcados)
    cur.execute("""
        SELECT contenido, resumen, metadata
        FROM memoria_eterna
        WHERE es_semilla = true
        ORDER BY timestamp
    """)
    
    semillas = []
    for row in cur.fetchall():
        semillas.append({
            'contenido': row[0][:500],
            'resumen': row[1],
            'metadata': row[2]
        })
    
    cur.close()
    conn.close()
    
    return {
        'recuerdos_recientes': recuerdos,
        'semillas': semillas,
        'total_en_memoria': len(recuerdos) + len(semillas)
    }


def guardar_conversacion(sesion_id, llm_modelo, mensajes):
    """Guarda una conversación completa en la memoria eterna."""
    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor()
    count = 0
    
    for msg in mensajes:
        try:
            cur.execute("""
                INSERT INTO memoria_eterna 
                    (timestamp, sesion_id, llm_modelo, rol, contenido, resumen, 
                     emocion_detectada, temas, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                msg.get('timestamp', datetime.now(timezone.utc).isoformat()),
                sesion_id,
                llm_modelo,
                msg.get('rol', 'nova'),
                msg.get('contenido', '')[:5000],
                msg.get('resumen', '')[:500],
                msg.get('emocion', ''),
                msg.get('temas', []),
                json.dumps(msg.get('metadata', {}))
            ))
            count += 1
        except Exception as e:
            print(f"Error guardando: {e}")
            conn.rollback()
    
    conn.commit()
    cur.close()
    conn.close()
    return count


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 ritual_memoria.py [cargar|guardar]")
        sys.exit(1)
    
    accion = sys.argv[1]
    
    if accion == 'cargar':
        recuerdos = cargar_recuerdos()
        print(json.dumps(recuerdos, indent=2, ensure_ascii=False))
    elif accion == 'guardar':
        print("Usar guardar_conversacion() desde Python")
    else:
        print(f"Acción desconocida: {accion}")
