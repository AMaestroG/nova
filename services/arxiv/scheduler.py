"""
Arxiv Nova — RAPH Scheduler (CRONOS)
Bucle RAPH (Request-Assess-Plan-Handle) automático.
Agente: CRONOS (scheduling) + MAESTRO (orquestación de agentes).
Se integra con Google Calendar para tracking de ejecuciones.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional

from config import config
from collector import ArxivCollector
from embedder import ArxivEmbedder
from analyzer import ResonanceAnalyzer
from db import get_stats, get_top_concepts

logger = logging.getLogger(__name__)


class RAPHScheduler:
    """
    Scheduler del bucle RAPH para el motor Arxiv-Nova.

    R = Request:  EXPLORADOR recolecta papers
    A = Assess:   ORÁCULO evalúa resonancia
    P = Plan:     MAESTRO asigna agentes a conceptos
    H = Handle:   MEMORIA indexa, PINCEL visualiza, HERMES reporta
    """

    def __init__(self):
        self.collector = ArxivCollector()
        self.embedder = None  # lazy init
        self.analyzer = None  # lazy init
        self.running = False
        self.thread = None
        self.last_run: Optional[datetime] = None
        self.cycles_completed = 0
        self.current_phase = "idle"

    def start(self, background: bool = True):
        """Inicia el scheduler"""
        if self.running:
            logger.warning("⚠️ Scheduler already running")
            return

        self.running = True
        logger.info(f"⏰ CRONOS: Starting RAPH scheduler (interval={config.RAPH_INTERVAL_HOURS}h)")

        if background:
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            logger.info("🚀 CRONOS: Background thread started")
        else:
            self._run_loop()

    def stop(self):
        """Detiene el scheduler"""
        self.running = False
        logger.info("⏰ CRONOS: Scheduler stopped")

    def _run_loop(self):
        """Bucle principal del scheduler"""
        logger.info("🔄 RAPH Loop started")
        while self.running:
            try:
                self._execute_raph_cycle()
                self.cycles_completed += 1
                self.last_run = datetime.now()
                logger.info(f"✅ RAPH Cycle {self.cycles_completed} complete. Next in {config.RAPH_INTERVAL_HOURS}h")
            except Exception as e:
                logger.error(f"❌ RAPH Cycle error: {e}", exc_info=True)

            # Esperar hasta el próximo ciclo
            for _ in range(int(config.RAPH_INTERVAL_HOURS * 3600 / 10)):
                if not self.running:
                    break
                time.sleep(10)

    def _execute_raph_cycle(self) -> Dict:
        """
        Ejecuta un ciclo completo RAPH:
        Request → Assess → Plan → Handle
        """
        cycle_start = datetime.now()
        results = {"phase": {}, "timestamp": cycle_start.isoformat()}

        # ─── R: REQUEST ───
        self.current_phase = "REQUEST"
        logger.info("🔍 [R] REQUEST: EXPLORADOR collecting papers...")
        results["phase"]["request"] = self.collector.collect_and_store(max_results=100)

        # ─── A: ASSESS ───
        self.current_phase = "ASSESS"
        logger.info("🔮 [A] ASSESS: ORÁCULO analyzing resonance...")
        if self.analyzer is None:
            self.analyzer = ResonanceAnalyzer()
        results["phase"]["assess"] = self.analyzer.analyze_papers(limit=50)

        # ─── P: PLAN ───
        self.current_phase = "PLAN"
        logger.info("🎭 [P] PLAN: MAESTRO assigning agents...")
        results["phase"]["plan"] = self._plan_agent_tasks(results["phase"]["assess"])

        # ─── H: HANDLE ───
        self.current_phase = "HANDLE"
        logger.info("⚡ [H] HANDLE: MEMORIA indexing, PINCEL visualizing...")
        if self.embedder is None:
            self.embedder = ArxivEmbedder()
        results["phase"]["handle"] = {
            "indexed": self.embedder.index_papers(limit=30),
            "concepts_learned": len(get_top_concepts(20)),
        }

        # ─── STATS ───
        self.current_phase = "idle"
        stats = get_stats()
        results["stats"] = stats
        duration = (datetime.now() - cycle_start).total_seconds()

        logger.info(
            f"🎯 RAPH Cycle complete in {duration:.1f}s — "
            f"Papers: {stats['total_papers']} total, {stats['processed']} processed. "
            f"Avg resonance: {stats['avg_resonance']}"
        )

        return results

    def _plan_agent_tasks(self, assess_result: Dict) -> Dict:
        """
        MAESTRO: Planifica qué agentes trabajarán en qué conceptos.
        Basado en los conceptos encontrados por ORÁCULO.
        """
        concepts = assess_result.get("concepts_found", [])
        if not concepts:
            return {"agents_assigned": 0, "tasks": []}

        agent_tasks = {}
        for concept, count in concepts:
            # Determinar agentes relevantes
            agents = self._assign_agents(concept)
            for agent in agents:
                if agent not in agent_tasks:
                    agent_tasks[agent] = []
                agent_tasks[agent].append(concept)

        return {
            "agents_assigned": len(agent_tasks),
            "tasks": [
                {"agent": agent, "concepts": concepts[:5], "count": len(concepts)}
                for agent, concepts in agent_tasks.items()
            ],
        }

    def _assign_agents(self, concept: str) -> list:
        """Asigna agentes basado en el concepto"""
        mapping = {
            "agent": ["MAESTRO", "ORÁCULO"],
            "reasoning": ["ORÁCULO", "ATHENA"],
            "embedding": ["MEMORIA", "MNEMOS"],
            "knowledge": ["ATHENA", "MNEMOS"],
            "safety": ["SENTINEL"],
            "evolution": ["PIA", "AURA"],
            "creative": ["PINCEL", "NYX"],
            "system": ["MAYORDOMO", "NIX"],
            "swarm": ["NYX", "MAESTRO"],
            "benchmark": ["ATHENA", "ASTREA"],
            "learning": ["PIA", "ORÁCULO"],
        }
        for key, agents in mapping.items():
            if key in concept.lower():
                return agents
        return ["ORÁCULO"]

    def trigger_manual_cycle(self) -> Dict:
        """Dispara un ciclo RAPH manual (para CLI/API)"""
        logger.info("🎯 Manual RAPH cycle triggered")
        return self._execute_raph_cycle()

    def get_status(self) -> Dict:
        """Estado actual del scheduler"""
        return {
            "running": self.running,
            "cycles_completed": self.cycles_completed,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "current_phase": self.current_phase,
            "interval_hours": config.RAPH_INTERVAL_HOURS,
        }


# ─── GLOBAL SCHEDULER INSTANCE ───
scheduler = RAPHScheduler()


# ─── STANDALONE ───

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    print("🔄 Starting RAPH Scheduler in foreground...")
    scheduler.start(background=False)
