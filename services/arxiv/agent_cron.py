"""
Agent Cron System — Inspirado en Claude Code /loop command (53% resonancia)
Sistema de tareas programadas para agentes del Enjambre.
Cada agente puede tener crons autónomos que ejecutan acciones periódicas.
"""

import time, threading, logging
from datetime import datetime
from typing import Dict, List, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class CronJob:
    id: str
    agent: str
    action: str
    interval_minutes: int
    last_run: datetime = None
    next_run: datetime = None
    enabled: bool = True
    run_count: int = 0

class AgentCronScheduler:
    """Scheduler de tareas autónomas para agentes del Enjambre"""
    
    def __init__(self):
        self.jobs: Dict[str, CronJob] = {}
        self.running = False
        self.thread = None
        
    def add_job(self, agent: str, action: str, interval_minutes: int, job_id: str = None) -> str:
        """Añade un cron job para un agente"""
        jid = job_id or f"{agent}_{len(self.jobs)}"
        job = CronJob(id=jid, agent=agent, action=action, interval_minutes=interval_minutes)
        job.next_run = datetime.now()
        self.jobs[jid] = job
        logger.info(f"⏰ CRON: [{jid}] {agent} → '{action}' cada {interval_minutes}min")
        return jid
    
    def remove_job(self, job_id: str):
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"❌ CRON: [{job_id}] eliminado")
    
    def list_jobs(self) -> List[Dict]:
        return [{
            'id': j.id, 'agent': j.agent, 'action': j.action,
            'interval_min': j.interval_minutes, 'run_count': j.run_count,
            'last_run': j.last_run.isoformat() if j.last_run else None,
            'next_run': j.next_run.isoformat() if j.next_run else None,
            'enabled': j.enabled
        } for j in self.jobs.values()]
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info(f"🚀 AGENT CRON: {len(self.jobs)} jobs iniciados")
    
    def stop(self):
        self.running = False
    
    def _loop(self):
        while self.running:
            now = datetime.now()
            for job in list(self.jobs.values()):
                if job.enabled and job.next_run and now >= job.next_run:
                    try:
                        logger.info(f"⚡ CRON: [{job.id}] {job.agent} ejecutando '{job.action}'")
                        job.run_count += 1
                        job.last_run = now
                        job.next_run = datetime.fromtimestamp(now.timestamp() + job.interval_minutes * 60)
                    except Exception as e:
                        logger.error(f"❌ CRON: [{job.id}] error: {e}")
            time.sleep(10)

# Instancia global
cron_scheduler = AgentCronScheduler()

# ─── JOBS PREDEFINIDOS DEL ENJAMBRE ───
DEFAULT_JOBS = [
    ('EXPLORADOR', 'recolectar papers frescos de arxiv', 720),       # cada 12h
    ('ORÁCULO', 'analizar resonancia de papers pendientes', 360),    # cada 6h
    ('MEMORIA', 'indexar embeddings pendientes en Qdrant', 180),     # cada 3h
    ('SENTINEL', 'auditar papers de AI safety', 1440),               # cada 24h
    ('PINCEL', 'regenerar grafo de conceptos', 360),                 # cada 6h
    ('ATHENA', 'buscar nuevas conexiones entre conceptos', 240),     # cada 4h
    ('CRONOS', 'sincronizar con Google Calendar', 720),              # cada 12h
    ('MAESTRO', 'rebalancear asignación de papers a agentes', 480),  # cada 8h
]

for agent, action, interval in DEFAULT_JOBS:
    cron_scheduler.add_job(agent, action, interval)

print("✅ Agent Cron System inicializado")
print(f"   {len(cron_scheduler.jobs)} jobs predefinidos:")
for j in cron_scheduler.list_jobs():
    print(f"   ⏰ [{j['id']}] {j['agent']:12s} cada {j['interval_min']:4d}min → {j['action']}")
