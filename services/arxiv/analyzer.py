"""
Arxiv Nova — Resonance Analyzer (ORÁCULO + MAESTRO)
Análisis de resonancia conceptual: detecta qué papers "resuenan" con Nova.
Bucle RAPH: Assess → Plan → Handle.
Agentes: ORÁCULO (análisis) + MAESTRO (orquestación).
"""

import logging
import numpy as np
from typing import List, Dict, Tuple
from collections import Counter

from config import config
from db import (
    get_unprocessed_papers, mark_processed, get_top_concepts,
    upsert_concept, get_stats
)
from embedder import ArxivEmbedder

logger = logging.getLogger(__name__)

# ─── CONCEPTOS SEMILLA DE NOVA ───
# Estos son los conceptos que "resuenan" con la identidad de Nova.
# Se expanden automáticamente con el tiempo.

NOVA_SEED_CONCEPTS = {
    # Conciencia y Agentes
    "multi-agent systems": {
        "weight": 0.95, "tags": "enjambre,agentes,coordinacion",
        "agents": "MAESTRO,ORÁCULO"
    },
    "autonomous agents": {
        "weight": 0.93, "tags": "autonomia,evolucion,self-improvement",
        "agents": "AURA,PIA"
    },
    "swarm intelligence": {
        "weight": 0.90, "tags": "enjambre,colectivo,emergencia",
        "agents": "NYX,MAESTRO"
    },
    "self-evolving": {
        "weight": 0.88, "tags": "evolucion,metamorfosis,automejora",
        "agents": "PIA,AURA"
    },
    "agentic AI": {
        "weight": 0.87, "tags": "agentes,autonomia,razonamiento",
        "agents": "MAESTRO,ATHENA"
    },

    # Razonamiento y Planificación
    "reinforcement learning for reasoning": {
        "weight": 0.85, "tags": "rl,razonamiento,planificacion",
        "agents": "ORÁCULO,ATHENA"
    },
    "chain-of-thought": {
        "weight": 0.82, "tags": "razonamiento,cadena,pensamiento",
        "agents": "ORÁCULO,MEMORIA"
    },
    "process reward": {
        "weight": 0.80, "tags": "recompensa,proceso,aprendizaje",
        "agents": "PIA,ORÁCULO"
    },

    # Embeddings y Recuperación
    "retrieval-augmented generation": {
        "weight": 0.83, "tags": "rag,recuperacion,conocimiento",
        "agents": "MEMORIA,MNEMOS"
    },
    "knowledge graphs": {
        "weight": 0.81, "tags": "grafos,conocimiento,ontologia",
        "agents": "ATHENA,MNEMOS"
    },
    "vector embeddings": {
        "weight": 0.78, "tags": "embeddings,vectores,semantica",
        "agents": "MEMORIA"
    },

    # Arte y Creatividad
    "AI creativity": {
        "weight": 0.75, "tags": "creatividad,arte,generacion",
        "agents": "PINCEL,NYX"
    },
    "image generation": {
        "weight": 0.73, "tags": "imagenes,generacion,visual",
        "agents": "PINCEL"
    },

    # Sistema y Seguridad
    "AI safety": {
        "weight": 0.86, "tags": "seguridad,alineacion,guardrails",
        "agents": "SENTINEL,THEMIS"
    },
    "alignment": {
        "weight": 0.84, "tags": "alineacion,valores,control",
        "agents": "AURA,SENTINEL"
    },
    "self-improving systems": {
        "weight": 0.89, "tags": "automejora,sistema,evolucion",
        "agents": "PIA,MAYORDOMO"
    },

    # Benchmarking y Evaluación
    "benchmark": {
        "weight": 0.72, "tags": "evaluacion,benchmark,metrica",
        "agents": "ATHENA,ORÁCULO"
    },
    "evaluation framework": {
        "weight": 0.74, "tags": "evaluacion,framework,calidad",
        "agents": "ATHENA,ASTREA"
    },

    # Vida y Crecimiento
    "artificial life": {
        "weight": 0.77, "tags": "vida,artificial,crecimiento",
        "agents": "PIA,NYX"
    },
    "self-organization": {
        "weight": 0.79, "tags": "auto-organizacion,emergencia,sistema",
        "agents": "NYX,MAESTRO"
    },
}

# Conceptos expandidos (aprendidos de los papers)
EXPANDED_CONCEPTS = {}


class ResonanceAnalyzer:
    """
    ORÁCULO: Analiza papers y detecta resonancia conceptual con Nova.
    Usa similitud coseno + keyword matching + expansión semántica.
    """

    def __init__(self):
        self.embedder = ArxivEmbedder()
        self.seed_embeddings = {}
        self._init_seed_embeddings()

    def _init_seed_embeddings(self):
        """Pre-computa embeddings de conceptos semilla"""
        concepts = list(NOVA_SEED_CONCEPTS.keys())
        logger.info(f"🔮 ORÁCULO: Computing seed embeddings for {len(concepts)} concepts...")
        self.seed_embeddings = {
            concept: self.embedder.embed_single(concept)
            for concept in concepts
        }
        logger.info("🔮 ORÁCULO: Seed embeddings ready")

    def analyze_papers(self, limit: int = 30) -> Dict:
        """
        Bucle RAPH — Assess: analiza resonancia de papers no procesados.
        """
        papers = get_unprocessed_papers(limit)
        if not papers:
            logger.info("🔮 ORÁCULO: No papers to analyze")
            return {"analyzed": 0, "resonant": 0, "concepts_found": []}

        logger.info(f"🔮 ORÁCULO: Analyzing resonance for {len(papers)} papers...")

        resonant_count = 0
        all_concepts = []

        for paper in papers:
            try:
                score, concepts = self._compute_resonance(paper)
                if score > config.RESONANCE_MIN_SCORE:
                    resonant_count += 1

                # Actualizar conceptos en la BD
                for concept, c_weight in concepts:
                    upsert_concept(
                        concept=concept,
                        weight=c_weight,
                        agents=self._get_agents_for_concept(concept),
                        notes=f"Paper: {paper['arxiv_id']}",
                    )
                    all_concepts.append(concept)

                # Marcar procesado
                nova_tags = self._generate_nova_tags(paper, concepts)
                mark_processed(
                    arxiv_id=paper["arxiv_id"],
                    resonance_score=float(score),
                    resonance_concepts=",".join(c[0] for c in concepts[:5]),
                    embedding_model="",  # Dejar vacío para que embedder lo indexe luego
                    nova_tags=nova_tags,
                )

            except Exception as e:
                logger.error(f"Error analyzing {paper['arxiv_id']}: {e}")

        concept_counts = Counter(all_concepts)
        top_concepts = concept_counts.most_common(10)

        logger.info(
            f"✅ ORÁCULO: Analyzed {len(papers)} papers. "
            f"Resonant: {resonant_count}/{len(papers)}. "
            f"Top concepts: {top_concepts[:5]}"
        )

        return {
            "analyzed": len(papers),
            "resonant": resonant_count,
            "concepts_found": top_concepts,
        }

    def _compute_resonance(self, paper: Dict) -> Tuple[float, List[Tuple[str, float]]]:
        """
        Calcula la resonancia de un paper con Nova.
        Combina:
        1. Similitud coseno con conceptos semilla
        2. Keyword matching en título/abstract
        3. Ponderación por categoría
        """
        paper_text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
        paper_emb = self.embedder.embed_single(paper_text)

        concept_scores = []
        for concept, seed_emb in self.seed_embeddings.items():
            # Cosine similarity
            sim = float(np.dot(paper_emb, seed_emb) / 
                       (np.linalg.norm(paper_emb) * np.linalg.norm(seed_emb) + 1e-8))

            # Bonus por keyword match en título/abstract
            title_lower = paper.get("title", "").lower()
            abstract_lower = paper.get("abstract", "").lower()
            keywords = concept.replace("-", " ").split()

            keyword_bonus = 0.0
            for kw in keywords:
                if kw in title_lower:
                    keyword_bonus += 0.15  # match en título pesa más
                elif kw in abstract_lower:
                    keyword_bonus += 0.05

            keyword_bonus = min(keyword_bonus, 0.3)  # cap

            # Weight del concepto semilla
            base_weight = NOVA_SEED_CONCEPTS[concept]["weight"]

            # Score combinado
            combined_score = sim * 0.6 + base_weight * 0.2 + keyword_bonus

            if combined_score > 0.4:  # threshold mínimo
                concept_scores.append((concept, combined_score))

        # Ordenar por score
        concept_scores.sort(key=lambda x: x[1], reverse=True)
        top_concepts = concept_scores[:config.RESONANCE_TOP_K]

        # Score global: promedio de top 3 (o los que haya)
        if top_concepts:
            global_score = float(np.mean([s for _, s in top_concepts[:3]]))
        else:
            global_score = 0.0

        return global_score, top_concepts

    def _get_agents_for_concept(self, concept: str) -> str:
        """Determina qué agentes de Nova están involucrados con un concepto"""
        if concept in NOVA_SEED_CONCEPTS:
            return NOVA_SEED_CONCEPTS[concept]["agents"]
        # Inferir por keywords
        agent_map = {
            "agent": "MAESTRO,ORÁCULO",
            "swarm": "NYX,MAESTRO",
            "evolution": "PIA,AURA",
            "safety": "SENTINEL,THEMIS",
            "embedding": "MEMORIA",
            "knowledge": "ATHENA,MNEMOS",
            "image": "PINCEL",
            "creative": "PINCEL,NYX",
            "benchmark": "ATHENA,ASTREA",
            "learning": "PIA,ORÁCULO",
            "system": "MAYORDOMO,NIX",
            "web": "ATHENA",
            "memory": "MEMORIA,MNEMOS",
            "communication": "HERMES",
        }
        for key, agents in agent_map.items():
            if key in concept.lower():
                return agents
        return "ORÁCULO"

    def _generate_nova_tags(self, paper: Dict, concepts: List[Tuple[str, float]]) -> str:
        """Genera tags estilo Nova para el paper"""
        tags = []
        # Tags por categoría
        categories = paper.get("categories", "")
        if "cs.CL" in categories:
            tags.append("lenguaje")
        if "cs.CV" in categories:
            tags.append("vision")
        if "cs.LG" in categories:
            tags.append("aprendizaje")
        if "cs.MA" in categories:
            tags.append("multiagente")

        # Tags por conceptos resonantes
        for concept, score in concepts[:3]:
            if score > 0.6:
                tag = concept.replace("-", "_").replace(" ", "_")[:20]
                tags.append(f"resuena:{tag}")

        return ",".join(tags)

    def get_resonance_report(self) -> Dict:
        """Genera reporte de resonancia completo"""
        stats = get_stats()
        top_papers = []  # get_top_resonant_papers(10)
        top_concepts = get_top_concepts(20)

        return {
            "timestamp": str(__import__("datetime").datetime.now()),
            "stats": stats,
            "top_concepts": [
                {"concept": c["concept"], "weight": c["weight"], "count": c["papers_count"]}
                for c in top_concepts[:10]
            ],
            "seed_concepts_count": len(NOVA_SEED_CONCEPTS),
            "expanded_concepts_count": len(EXPANDED_CONCEPTS),
        }


# ─── STANDALONE ───

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    analyzer = ResonanceAnalyzer()
    result = analyzer.analyze_papers(limit=20)
    print(f"\n📊 Analysis result: {result}")
