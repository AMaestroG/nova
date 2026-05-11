"""
Arxiv Nova — Database Layer (PostgreSQL)
Operaciones CRUD para papers y conceptos de resonancia
"""

import psycopg2
import psycopg2.extras
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
from config import config
import json
import logging

logger = logging.getLogger(__name__)


def get_conn():
    """Obtiene conexión a PostgreSQL"""
    return psycopg2.connect(
        host=config.PG_HOST,
        port=config.PG_PORT,
        dbname=config.PG_DB,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
    )


# ─── PAPER OPERATIONS ───

def paper_exists(arxiv_id: str) -> bool:
    """Verifica si un paper ya está en la BD"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM arxiv_papers WHERE arxiv_id = %s", (arxiv_id,))
            return cur.fetchone() is not None


def insert_paper(paper: Dict) -> bool:
    """Inserta un paper. Retorna True si fue insertado, False si ya existía."""
    if paper_exists(paper["arxiv_id"]):
        return False
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO arxiv_papers 
                   (arxiv_id, title, authors, abstract, categories, published_date, url, pdf_url)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    paper["arxiv_id"],
                    paper["title"],
                    paper.get("authors", ""),
                    paper.get("abstract", ""),
                    paper.get("categories", ""),
                    paper.get("published_date"),
                    paper.get("url", ""),
                    paper.get("pdf_url", ""),
                ),
            )
        conn.commit()
    return True


def get_unprocessed_papers(limit: int = 50) -> List[Dict]:
    """Obtiene papers no procesados (sin embedding/análisis)"""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM arxiv_papers WHERE processed = FALSE ORDER BY collected_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


def mark_processed(arxiv_id: str, resonance_score: float = 0.0,
                   resonance_concepts: str = "", embedding_model: str = "",
                   nova_tags: str = "") -> None:
    """Marca un paper como procesado con sus metadatos de resonancia"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE arxiv_papers SET 
                   processed = TRUE,
                   resonance_score = %s,
                   resonance_concepts = %s,
                   embedding_model = %s,
                   nova_tags = %s
                   WHERE arxiv_id = %s""",
                (resonance_score, resonance_concepts, embedding_model, nova_tags, arxiv_id),
            )
        conn.commit()


def get_papers_by_date_range(start: date, end: date) -> List[Dict]:
    """Papers en rango de fechas"""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM arxiv_papers WHERE published_date BETWEEN %s AND %s ORDER BY resonance_score DESC",
                (start, end),
            )
            return [dict(row) for row in cur.fetchall()]


def get_top_resonant_papers(limit: int = 20) -> List[Dict]:
    """Top papers por resonance_score"""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM arxiv_papers WHERE processed = TRUE ORDER BY resonance_score DESC LIMIT %s",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


def get_stats() -> Dict:
    """Estadísticas generales del motor"""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as total FROM arxiv_papers")
            total = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) as processed FROM arxiv_papers WHERE processed = TRUE")
            processed = cur.fetchone()["processed"]
            cur.execute("SELECT AVG(resonance_score) as avg_score FROM arxiv_papers WHERE processed = TRUE")
            avg = cur.fetchone()["avg_score"] or 0
            cur.execute("SELECT MAX(collected_at) as last_collection FROM arxiv_papers")
            last = cur.fetchone()["last_collection"]
            return {
                "total_papers": total,
                "processed": processed,
                "unprocessed": total - processed,
                "avg_resonance": round(float(avg), 4),
                "last_collection": last.isoformat() if last else None,
            }


# ─── RESONANCE CONCEPT OPERATIONS ───

def upsert_concept(concept: str, weight: float = 0.0,
                   agents: str = "", notes: str = "") -> None:
    """Inserta o actualiza un concepto de resonancia"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, papers_count, weight FROM arxiv_resonance WHERE concept = %s", (concept,))
            row = cur.fetchone()
            if row:
                new_count = row[1] + 1
                new_weight = (row[2] * row[1] + weight) / new_count
                cur.execute(
                    """UPDATE arxiv_resonance SET 
                       weight = %s, papers_count = %s, last_seen = NOW(),
                       nova_agents_involved = %s, notes = %s
                       WHERE concept = %s""",
                    (new_weight, new_count, agents, notes, concept),
                )
            else:
                cur.execute(
                    """INSERT INTO arxiv_resonance 
                       (concept, weight, papers_count, nova_agents_involved, notes)
                       VALUES (%s, %s, 1, %s, %s)""",
                    (concept, weight, agents, notes),
                )
        conn.commit()


def get_top_concepts(limit: int = 30) -> List[Dict]:
    """Conceptos con mayor peso de resonancia"""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM arxiv_resonance 
                   ORDER BY weight * papers_count DESC LIMIT %s""",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


def get_emerging_concepts(limit: int = 10) -> List[Dict]:
    """Conceptos emergentes (nuevos, con pocos papers pero alto peso)"""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM arxiv_resonance 
                   WHERE evolution_stage = 'emerging' AND papers_count >= 2
                   ORDER BY weight DESC LIMIT %s""",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]
