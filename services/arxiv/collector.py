"""
Arxiv Nova — Paper Collector (EXPLORADOR)
Scraping de arxiv API con rate limiting y deduplicación.
Agente: EXPLORADOR del Enjambre Homonexus.
"""

import arxiv
import time
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict
import feedparser

from config import config
from db import insert_paper, paper_exists, get_stats

logger = logging.getLogger(__name__)

# ─── ARXIV API CLIENT ───

class ArxivCollector:
    """Recolector de papers de arxiv cs.AI usando API oficial + RSS"""

    def __init__(self):
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=config.ARXIV_DELAY,
            num_retries=3,
        )
        self.stats = {"new": 0, "skipped": 0, "errors": 0}

    def fetch_recent(self, max_results: int = None) -> List[Dict]:
        """
        Fetch recent papers from cs.AI.
        Retorna lista de dicts con metadatos.
        """
        if max_results is None:
            max_results = config.ARXIV_MAX_RESULTS

        logger.info(f"🔍 EXPLORADOR: Fetching {max_results} recent papers from cs.AI...")

        search = arxiv.Search(
            query="cat:cs.AI",
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )

        papers = []
        for result in self.client.results(search):
            try:
                paper = self._parse_result(result)
                papers.append(paper)
            except Exception as e:
                logger.error(f"Error parsing paper {getattr(result, 'entry_id', '?')}: {e}")
                self.stats["errors"] += 1

        logger.info(f"📥 EXPLORADOR: Fetched {len(papers)} papers from arxiv")
        return papers

    def fetch_by_date(self, target_date: date) -> List[Dict]:
        """Fetch papers de una fecha específica usando RSS feed"""
        # arxiv RSS: https://rss.arxiv.org/rss/cs.AI
        # Format: https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&start=0&max_results=100
        logger.info(f"📅 Fetching papers for {target_date}...")

        papers = []
        # Use the API with date filtering
        search = arxiv.Search(
            query=f"cat:cs.AI AND submittedDate:[{target_date.isoformat()} TO {target_date.isoformat()}]",
            max_results=500,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        for result in self.client.results(search):
            try:
                paper = self._parse_result(result)
                if paper.get("published_date") == target_date:
                    papers.append(paper)
            except Exception as e:
                logger.error(f"Error: {e}")

        return papers

    def collect_and_store(self, max_results: int = None) -> Dict:
        """
        Bucle RAPH — Request: recolecta papers y los almacena en PostgreSQL.
        Retorna estadísticas.
        """
        self.stats = {"new": 0, "skipped": 0, "errors": 0}

        papers = self.fetch_recent(max_results)

        for paper in papers:
            try:
                if insert_paper(paper):
                    self.stats["new"] += 1
                else:
                    self.stats["skipped"] += 1
            except Exception as e:
                logger.error(f"DB insert error for {paper['arxiv_id']}: {e}")
                self.stats["errors"] += 1

        logger.info(
            f"✅ EXPLORADOR: Collection complete — "
            f"New: {self.stats['new']}, Skipped: {self.stats['skipped']}, Errors: {self.stats['errors']}"
        )
        return self.stats

    def _parse_result(self, result: arxiv.Result) -> Dict:
        """Parsea un resultado de arxiv API a diccionario"""
        # Extract arxiv ID from entry_id
        entry_id = str(result.entry_id)
        arxiv_id = entry_id.split("/")[-1].replace("v1", "").replace("v2", "").replace("v3", "")

        # Authors
        authors = ", ".join(str(a) for a in result.authors[:10])
        if len(result.authors) > 10:
            authors += f" et al. ({len(result.authors)} total)"

        # Categories
        categories = ", ".join(str(c) for c in result.categories)

        # Date
        pub_date = result.published.date() if result.published else None

        return {
            "arxiv_id": arxiv_id,
            "title": str(result.title).replace("\n", " ").strip(),
            "authors": authors,
            "abstract": str(result.summary).replace("\n", " ").strip(),
            "categories": categories,
            "published_date": pub_date,
            "url": str(entry_id),
            "pdf_url": str(result.pdf_url) if result.pdf_url else "",
        }


# ─── STANDALONE EXECUTION ───

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    collector = ArxivCollector()
    stats = collector.collect_and_store(max_results=50)
    print(f"\n📊 Collection stats: {stats}")
