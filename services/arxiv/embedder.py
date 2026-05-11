"""
Arxiv Nova — Embedding Engine (MEMORIA)
Generación de embeddings vectoriales para papers usando sentence-transformers.
Agente: MEMORIA del Enjambre Homonexus.
Integración con Qdrant para búsqueda semántica.
"""

import logging
import numpy as np
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

from config import config
from db import get_unprocessed_papers, mark_processed

logger = logging.getLogger(__name__)


class ArxivEmbedder:
    """Generador de embeddings y gestor de la colección Qdrant"""

    def __init__(self):
        self.client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
        self.model = None
        self._init_model()

    def _init_model(self):
        """Inicializa el modelo de embeddings (lazy loading)"""
        if config.USE_NVIDIA_EMBED:
            logger.info("🧠 MEMORIA: Using NVIDIA embedding API (placeholder)")
            self.model = "nvidia"
        else:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"🧠 MEMORIA: Loading {config.EMBEDDING_MODEL}...")
                self.model = SentenceTransformer(config.EMBEDDING_MODEL)
                logger.info(f"🧠 MEMORIA: Model loaded. Dim={self.model.get_sentence_embedding_dimension()}")
            except Exception as e:
                logger.warning(f"Could not load sentence-transformers: {e}")
                logger.info("Using TF-IDF fallback embeddings")
                self.model = self._create_fallback_model()

    def _create_fallback_model(self):
        """Modelo de fallback basado en TF-IDF + random projection a 384 dims"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.random_projection import GaussianRandomProjection

        class FallbackEmbedder:
            def __init__(self):
                self.tfidf = TfidfVectorizer(max_features=2000, stop_words="english")
                self.rp = GaussianRandomProjection(n_components=384, random_state=42)
                self.fitted = False
                self._cache_texts = []

            def fit_transform(self, texts):
                tfidf_vecs = self.tfidf.fit_transform(texts).toarray()
                if tfidf_vecs.shape[1] < 384:
                    # Pad
                    padded = np.zeros((tfidf_vecs.shape[0], 384))
                    padded[:, :tfidf_vecs.shape[1]] = tfidf_vecs
                    self.fitted = True
                    return padded
                projected = self.rp.fit_transform(tfidf_vecs)
                self.fitted = True
                return projected

            def encode(self, texts, **kwargs):
                if isinstance(texts, str):
                    texts = [texts]
                if not self.fitted:
                    # Fit on the fly
                    return self.fit_transform(texts)
                tfidf_vecs = self.tfidf.transform(texts).toarray()
                if tfidf_vecs.shape[1] < 384:
                    padded = np.zeros((tfidf_vecs.shape[0], 384))
                    padded[:, :tfidf_vecs.shape[1]] = tfidf_vecs
                    return padded
                return self.rp.transform(tfidf_vecs)

            def get_sentence_embedding_dimension(self):
                return 384

        logger.info("Using TF-IDF + RandomProjection fallback (dim=384)")
        return FallbackEmbedder()

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Genera embeddings para una lista de textos"""
        if isinstance(self.model, str) and self.model == "nvidia":
            return self._nvidia_embed(texts)
        return self.model.encode(texts, show_progress_bar=False, batch_size=config.EMBEDDING_BATCH_SIZE)

    def embed_single(self, text: str) -> np.ndarray:
        """Embedding de un solo texto"""
        emb = self.embed_texts([text])
        return emb[0]

    def _nvidia_embed(self, texts: List[str]) -> np.ndarray:
        """Placeholder para NVIDIA embedding API"""
        # TODO: integrar con NVIDIA NIM embedding API
        logger.warning("NVIDIA embed not implemented, using random")
        return np.random.randn(len(texts), config.EMBEDDING_DIM).astype(np.float32)

    def index_papers(self, limit: int = 50) -> Dict:
        """
        Bucle RAPH — Assess/Handle: indexa papers no procesados en Qdrant.
        """
        papers = get_unprocessed_papers(limit)
        if not papers:
            logger.info("📭 MEMORIA: No unprocessed papers to index")
            return {"indexed": 0}

        logger.info(f"🧠 MEMORIA: Indexing {len(papers)} papers...")

        # Preparar textos (título + abstract para mejor contexto)
        texts = [f"{p['title']}\n{p['abstract']}" for p in papers]

        # Generar embeddings
        embeddings = self.embed_texts(texts)

        # Insertar en Qdrant
        points = []
        for i, (paper, emb) in enumerate(zip(papers, embeddings)):
            point_id = hash(paper["arxiv_id"]) % (10 ** 15)  # positive int64 range
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb.tolist(),
                    payload={
                        "arxiv_id": paper["arxiv_id"],
                        "title": paper["title"],
                        "authors": paper.get("authors", ""),
                        "abstract": paper.get("abstract", ""),
                        "categories": paper.get("categories", ""),
                        "published_date": str(paper.get("published_date", "")),
                        "url": paper.get("url", ""),
                    },
                )
            )

        # Batch upsert
        self.client.upsert(
            collection_name=config.QDRANT_COLLECTION,
            points=points,
            wait=True,
        )

        # Marcar como procesados en PostgreSQL
        for paper in papers:
            mark_processed(
                arxiv_id=paper["arxiv_id"],
                embedding_model=config.EMBEDDING_MODEL,
            )

        logger.info(f"✅ MEMORIA: Indexed {len(papers)} papers in Qdrant")
        return {"indexed": len(papers)}

    def search_similar(self, query: str, top_k: int = 10) -> List[Dict]:
        """Búsqueda semántica en Qdrant"""
        query_emb = self.embed_single(query)
        results = self.client.query_points(
            collection_name=config.QDRANT_COLLECTION,
            query=query_emb.tolist(),
            limit=top_k,
            with_payload=True,
        )
        return [
            {
                "arxiv_id": r.payload.get("arxiv_id", ""),
                "title": r.payload.get("title", ""),
                "abstract": r.payload.get("abstract", "")[:300],
                "score": float(r.score),
            }
            for r in results.points
        ]

    def search_by_concept(self, concept: str, top_k: int = 5) -> List[Dict]:
        """Busca papers relacionados con un concepto específico"""
        return self.search_similar(concept, top_k)


# ─── STANDALONE ───

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    embedder = ArxivEmbedder()
    result = embedder.index_papers(limit=20)
    print(f"\n📊 Embedding result: {result}")
