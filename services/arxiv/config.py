"""
Arxiv Nova Knowledge Engine — Configuration
Sistema automático de recolección, embedding y resonancia de papers cs.AI
Parte del Enjambre Homonexus
"""

import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class ArxivConfig:
    """Configuración central del motor Arxiv-Nova"""

    # PostgreSQL (nexus_metamorfosis)
    PG_HOST: str = os.getenv("PG_HOST", "127.0.0.1")
    PG_PORT: int = int(os.getenv("PG_PORT", "5433"))
    PG_DB: str = os.getenv("PG_DB", "nexus_metamorfosis")
    PG_USER: str = os.getenv("PG_USER", "nexus_master")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", "nexus_password_dev")

    # Qdrant
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION: str = "nova_arxiv_papers"
    EMBEDDING_DIM: int = 384  # all-MiniLM-L6-v2 dimension

    # Arxiv API
    ARXIV_CATEGORIES: List[str] = field(default_factory=lambda: ["cs.AI"])
    ARXIV_MAX_RESULTS: int = 200  # per fetch
    ARXIV_DELAY: float = 3.0  # seconds between API calls (rate limiting)

    # Scheduling (RAPH cycle)
    RAPH_INTERVAL_HOURS: int = 12  # Every 12h: collect + analyze
    DEEP_ANALYSIS_INTERVAL_HOURS: int = 24  # Every 24h: deep resonance analysis

    # Embedding
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # local
    EMBEDDING_BATCH_SIZE: int = 32
    USE_NVIDIA_EMBED: bool = False  # toggle for NVIDIA API embeddings

    # Resonance thresholds
    RESONANCE_MIN_SCORE: float = 0.65  # minimum cosine similarity to flag
    RESONANCE_TOP_K: int = 10  # top concepts per paper

    # Nova Agents involved
    NOVA_AGENTS: List[str] = field(default_factory=lambda: [
        "EXPLORADOR",  # scraping & collection
        "MEMORIA",     # embeddings & Qdrant
        "MNEMOS",      # Drive storage
        "ORÁCULO",     # resonance analysis
        "CRONOS",      # scheduling
        "MAESTRO",     # orchestration
        "PINCEL",      # visualization
        "ATHENA",      # web knowledge
        "HERMES",      # communication
    ])

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    LOG_DIR: str = os.path.join(BASE_DIR, "logs")

    # Flask server
    FLASK_PORT: int = int(os.getenv("ARXIV_FLASK_PORT", "9100"))
    FLASK_HOST: str = "0.0.0.0"

    def __post_init__(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.LOG_DIR, exist_ok=True)


# Singleton
config = ArxivConfig()
