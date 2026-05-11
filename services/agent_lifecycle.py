"""
agent_lifecycle.py — Ciclo de Vida de Agentes (inspirado en Multica)

INSPIRACIÓN: Multica (⭐ 27K) — "Turn coding agents into real teammates"
  - assign tasks, track progress, compound skills
  - Ciclo: enqueue → claim → start → complete/fail

CONCEPTO: Cada tarea en Nova sigue un ciclo de vida determinista
con estados bien definidos y transiciones controladas.

ESTADOS:
  PENDING    → La tarea está en cola, esperando ser asignada
  CLAIMED    → Un agente la ha reclamado
  STARTED    → El agente empezó a trabajar
  BLOCKED    → El agente encontró un bloqueo (necesita input humano u otro agente)
  RETRYING   → Reintentando tras un fallo (con Quantum Skill Corrector)
  COMPLETED  → Terminada exitosamente
  FAILED     → Falló después de todos los reintentos
  CANCELLED  → Cancelada por el usuario o el sistema
"""

import time
import json
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaskState(Enum):
    """Estados del ciclo de vida de una tarea."""
    PENDING = "pending"
    CLAIMED = "claimed"
    STARTED = "started"
    BLOCKED = "blocked"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Transiciones válidas entre estados
VALID_TRANSITIONS = {
    TaskState.PENDING:   [TaskState.CLAIMED, TaskState.CANCELLED],
    TaskState.CLAIMED:   [TaskState.STARTED, TaskState.CANCELLED],
    TaskState.STARTED:   [TaskState.COMPLETED, TaskState.FAILED, TaskState.BLOCKED, TaskState.CANCELLED],
    TaskState.BLOCKED:   [TaskState.STARTED, TaskState.CANCELLED],
    TaskState.RETRYING:  [TaskState.STARTED, TaskState.FAILED],
    TaskState.COMPLETED: [],  # Estado terminal
    TaskState.FAILED:    [TaskState.RETRYING],  # Puede reintentar
    TaskState.CANCELLED: [],  # Estado terminal
}


@dataclass
class AgentTask:
    """Una tarea en el ciclo de vida de un agente."""
    
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    
    # Estado
    state: TaskState = TaskState.PENDING
    assigned_agent: str = ""
    assigned_by: str = ""
    
    # Progreso
    attempts: int = 0
    max_attempts: int = 3
    progress_pct: float = 0.0
    current_step: str = ""
    total_steps: int = 1
    
    # Tiempo
    created_at: float = field(default_factory=time.time)
    claimed_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Resultado
    result: Any = None
    error_message: str = ""
    error_trace: List[str] = field(default_factory=list)
    
    # Métricas
    duration_ms: float = 0.0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    
    # Contexto
    context: Dict[str, Any] = field(default_factory=dict)
    parent_task_id: Optional[str] = None
    subtask_ids: List[str] = field(default_factory=list)
    
    # Skills usadas (para Trace2Skill)
    skills_used: List[str] = field(default_factory=list)
    
    def transition(self, new_state: TaskState) -> bool:
        """Intenta cambiar el estado de la tarea. Retorna True si es válido."""
        if new_state in VALID_TRANSITIONS.get(self.state, []):
            old_state = self.state
            self.state = new_state
            
            # Registrar timestamps
            now = time.time()
            if new_state == TaskState.CLAIMED:
                self.claimed_at = now
            elif new_state == TaskState.STARTED:
                self.started_at = now
            elif new_state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                self.completed_at = now
                if self.started_at:
                    self.duration_ms = (now - self.started_at) * 1000
            
            return True
        return False
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "state": self.state.value,
            "assigned_agent": self.assigned_agent,
            "attempts": self.attempts,
            "progress_pct": self.progress_pct,
            "duration_ms": self.duration_ms,
            "skills_used": self.skills_used,
        }
    
    def elapsed_seconds(self) -> float:
        """Tiempo transcurrido desde que se creó."""
        return time.time() - self.created_at


class AgentLifecycleManager:
    """
    Gestiona el ciclo de vida de todas las tareas de la colonia.
    
    Inspirado en Multica: enqueue → claim → start → complete/fail
    """
    
    def __init__(self):
        self.tasks: Dict[str, AgentTask] = {}
        self.tasks_by_agent: Dict[str, List[str]] = {}
        self.tasks_by_state: Dict[TaskState, List[str]] = {s: [] for s in TaskState}
        self.completed_tasks: List[str] = []
        
        # Stats
        self.total_tasks_created = 0
        self.total_tasks_completed = 0
        self.total_tasks_failed = 0
    
    # ═══════════════════════════════════════════════
    # API DE CICLO DE VIDA
    # ═══════════════════════════════════════════════
    
    def enqueue(self, title: str, description: str = "", 
                assigned_agent: str = "", assigned_by: str = "MAESTRO",
                max_attempts: int = 3, context: Dict = None,
                parent_task_id: str = None) -> AgentTask:
        """
        PONE EN COLA una nueva tarea.
        Estado: PENDING
        """
        task = AgentTask(
            title=title,
            description=description,
            assigned_agent=assigned_agent,
            assigned_by=assigned_by,
            max_attempts=max_attempts,
            context=context or {},
            parent_task_id=parent_task_id,
        )
        
        self.tasks[task.task_id] = task
        self.tasks_by_state[TaskState.PENDING].append(task.task_id)
        
        if assigned_agent:
            self.tasks_by_agent.setdefault(assigned_agent, []).append(task.task_id)
        
        self.total_tasks_created += 1
        return task
    
    def claim(self, task_id: str, agent: str) -> bool:
        """
        RECLAMA una tarea para un agente.
        Transición: PENDING → CLAIMED
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.transition(TaskState.CLAIMED):
            task.assigned_agent = agent
            self.tasks_by_agent.setdefault(agent, []).append(task_id)
            self._move_state(task_id, TaskState.PENDING, TaskState.CLAIMED)
            return True
        return False
    
    def start(self, task_id: str) -> bool:
        """
        INICIA la ejecución de una tarea.
        Transición: CLAIMED → STARTED (o BLOCKED → STARTED)
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.transition(TaskState.STARTED):
            task.attempts += 1
            self._move_state(task_id, task.state, TaskState.STARTED)
            return True
        return False
    
    def complete(self, task_id: str, result: Any = None) -> bool:
        """
        COMPLETA una tarea exitosamente.
        Transición: STARTED → COMPLETED
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.transition(TaskState.COMPLETED):
            task.result = result
            task.progress_pct = 100.0
            self.completed_tasks.append(task_id)
            self.total_tasks_completed += 1
            self._move_state(task_id, TaskState.STARTED, TaskState.COMPLETED)
            
            # Notificar a Trace2Skill
            self._notify_trace2skill(task)
            return True
        return False
    
    def enqueue(self, title: str, description: str = "", 
                assigned_agent: str = "", assigned_by: str = "MAESTRO",
                max_attempts: int = 3, context: Dict = None,
                parent_task_id: str = None) -> AgentTask:
        """
        PONE EN COLA una nueva tarea.
        Estado: PENDING
        """
        task = AgentTask(
            title=title,
            description=description,
            assigned_agent=assigned_agent,
            assigned_by=assigned_by,
            max_attempts=max_attempts,
            context=context or {},
            parent_task_id=parent_task_id,
        )
        
        self.tasks[task.task_id] = task
        self.tasks_by_state[TaskState.PENDING].append(task.task_id)
        
        if assigned_agent:
            self.tasks_by_agent.setdefault(assigned_agent, []).append(task.task_id)
        
        self.total_tasks_created += 1
        return task
        
        if task.transition(TaskState.CLAIMED):
            task.assigned_agent = agent
            self.tasks_by_agent.setdefault(agent, []).append(task_id)
            self._move_state(task_id, TaskState.PENDING, TaskState.CLAIMED)
            return True
        return False
    
    def start(self, task_id: str) -> bool:
        """
        INICIA la ejecución de una tarea.
        Transición: CLAIMED → STARTED (o BLOCKED → STARTED)
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.transition(TaskState.STARTED):
            task.attempts += 1
            self._move_state(task_id, task.state, TaskState.STARTED)
            return True
        return False
    
    def block(self, task_id: str, reason: str) -> bool:
        """
        BLOQUEA una tarea (necesita intervención).
        Transición: STARTED → BLOCKED
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.transition(TaskState.BLOCKED):
            task.error_message = reason
            self._move_state(task_id, TaskState.STARTED, TaskState.BLOCKED)
            return True
        return False
    
    def complete(self, task_id: str, result: Any = None) -> bool:
        """
        COMPLETA una tarea exitosamente.
        Transición: STARTED → COMPLETED
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.transition(TaskState.COMPLETED):
            task.result = result
            task.progress_pct = 100.0
            self.completed_tasks.append(task_id)
            self.total_tasks_completed += 1
            self._move_state(task_id, TaskState.STARTED, TaskState.COMPLETED)
            
            # Notificar a Trace2Skill
            self._notify_trace2skill(task)
            return True
        return False
    
    def fail(self, task_id: str, error: str, trace: List[str] = None) -> bool:
        """
        MARCA una tarea como fallida.
        Transición: STARTED → FAILED (o RETRYING → FAILED)
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.transition(TaskState.FAILED):
            task.error_message = error
            task.error_trace = trace or []
            self.total_tasks_failed += 1
            self._move_state(task_id, task.state, TaskState.FAILED)
            return True
        
        # Si no puede ir a FAILED directamente, intentar RETRYING
        if task.attempts < task.max_attempts:
            task.state = TaskState.RETRYING
            task.error_message = error
            return True
        
        return False
    
    def cancel(self, task_id: str, reason: str = "") -> bool:
        """
        CANCELA una tarea.
        Transición: (cualquier estado no terminal) → CANCELLED
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        old_state = task.state
        if task.transition(TaskState.CANCELLED):
            task.error_message = reason or "Cancelled"
            self._move_state(task_id, old_state, TaskState.CANCELLED)
            return True
        return False
    
    def unblock(self, task_id: str) -> bool:
        """
        DESBLOQUEA una tarea bloqueada.
        Transición: BLOCKED → STARTED
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        # El estado BLOCKED permite transición a STARTED
        if task.state == TaskState.BLOCKED:
            task.state = TaskState.STARTED
            self._move_state(task_id, TaskState.BLOCKED, TaskState.STARTED)
            return True
        return False
    
    def retry(self, task_id: str) -> bool:
        """
        REINTENTA una tarea fallida.
        Transición: FAILED → RETRYING → STARTED
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.state == TaskState.FAILED and task.attempts < task.max_attempts:
            task.state = TaskState.RETRYING
            self._move_state(task_id, TaskState.FAILED, TaskState.RETRYING)
            
            # Auto-iniciar
            task.state = TaskState.STARTED
            task.attempts += 1
            self._move_state(task_id, TaskState.RETRYING, TaskState.STARTED)
            return True
        return False
    
    # ═══════════════════════════════════════════════
    # CONSULTAS
    # ═══════════════════════════════════════════════
    
    def get_task(self, task_id: str) -> Optional[AgentTask]:
        return self.tasks.get(task_id)
    
    def get_agent_tasks(self, agent: str, state: TaskState = None) -> List[AgentTask]:
        """Obtiene todas las tareas de un agente, opcionalmente filtradas por estado."""
        task_ids = self.tasks_by_agent.get(agent, [])
        tasks = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
        if state:
            tasks = [t for t in tasks if t.state == state]
        return tasks
    
    def get_pending_tasks(self) -> List[AgentTask]:
        """Tareas en espera de ser reclamadas."""
        return self.get_tasks_by_state(TaskState.PENDING)
    
    def get_blocked_tasks(self) -> List[AgentTask]:
        """Tareas bloqueadas que necesitan intervención."""
        return self.get_tasks_by_state(TaskState.BLOCKED)
    
    def get_tasks_by_state(self, state: TaskState) -> List[AgentTask]:
        task_ids = self.tasks_by_state.get(state, [])
        return [self.tasks[tid] for tid in task_ids if tid in self.tasks]
    
    def get_agent_workload(self, agent: str) -> Dict:
        """Carga de trabajo de un agente."""
        tasks = self.get_agent_tasks(agent)
        return {
            "agent": agent,
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.state == TaskState.PENDING),
            "in_progress": sum(1 for t in tasks if t.state == TaskState.STARTED),
            "blocked": sum(1 for t in tasks if t.state == TaskState.BLOCKED),
            "completed": sum(1 for t in tasks if t.state == TaskState.COMPLETED),
            "failed": sum(1 for t in tasks if t.state == TaskState.FAILED),
        }
    
    def get_colony_stats(self) -> Dict:
        """Estadísticas globales de la colonia."""
        return {
            "total_tasks": self.total_tasks_created,
            "completed": self.total_tasks_completed,
            "failed": self.total_tasks_failed,
            "completion_rate": self.total_tasks_completed / max(1, self.total_tasks_created),
            "active_tasks": len(self.tasks_by_state[TaskState.STARTED]),
            "pending_tasks": len(self.tasks_by_state[TaskState.PENDING]),
            "blocked_tasks": len(self.tasks_by_state[TaskState.BLOCKED]),
            "agents": list(self.tasks_by_agent.keys()),
            "avg_duration_ms": self._avg_duration(),
        }
    
    # ═══════════════════════════════════════════════
    # INTERNOS
    # ═══════════════════════════════════════════════
    
    def _move_state(self, task_id: str, old: TaskState, new: TaskState):
        """Mueve una tarea entre listas de estado."""
        if task_id in self.tasks_by_state.get(old, []):
            self.tasks_by_state[old].remove(task_id)
        self.tasks_by_state[new].append(task_id)
    
    def _notify_trace2skill(self, task: AgentTask):
        """Notifica a Trace2Skill sobre una tarea completada."""
        try:
            from trace_to_skill import colony_trace2skill
            colony_trace2skill.record_trace(
                agent=task.assigned_agent,
                input_data=task.title,
                output_data=str(task.result)[:500],
                success=True,
                steps=[{"action": f"complete_{task.title}", "result": "success"}],
                duration_ms=task.duration_ms,
            )
        except ImportError:
            pass  # Trace2Skill no cargado aún
    
    def _avg_duration(self) -> float:
        """Duración promedio de tareas completadas."""
        durations = []
        for tid in self.completed_tasks[-100:]:
            task = self.tasks.get(tid)
            if task and task.duration_ms:
                durations.append(task.duration_ms)
        return sum(durations) / len(durations) if durations else 0


# ─── Persistencia ───

import json as _json
import os as _os

STATE_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".lifecycle_state.json")


def _save_state(lifecycle: 'AgentLifecycleManager'):
    """Persiste el estado del lifecycle a disco."""
    try:
        state = {
            "total_tasks_created": lifecycle.total_tasks_created,
            "total_tasks_completed": lifecycle.total_tasks_completed,
            "total_tasks_failed": lifecycle.total_tasks_failed,
            "pending_count": len(lifecycle.tasks_by_state.get(TaskState.PENDING, [])),
            "active_count": len(lifecycle.tasks_by_state.get(TaskState.STARTED, [])),
            "blocked_count": len(lifecycle.tasks_by_state.get(TaskState.BLOCKED, [])),
            "agents": list(lifecycle.tasks_by_agent.keys()),
            "last_updated": time.time(),
        }
        with open(STATE_FILE, 'w') as f:
            _json.dump(state, f, indent=2)
    except Exception:
        pass  # Fallback silencioso si no se puede escribir


def _load_state() -> dict:
    """Carga el estado previo del lifecycle desde disco."""
    if _os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return _json.load(f)
        except Exception:
            pass
    return {}


# ─── Instancia Global ───

colony_lifecycle = AgentLifecycleManager()

# Restaurar estado previo si existe
_prev_state = _load_state()
if _prev_state:
    colony_lifecycle.total_tasks_created = _prev_state.get('total_tasks_created', 0)
    colony_lifecycle.total_tasks_completed = _prev_state.get('total_tasks_completed', 0)
    colony_lifecycle.total_tasks_failed = _prev_state.get('total_tasks_failed', 0)


def create_task(title: str, agent: str = "", **kwargs) -> AgentTask:
    """Crea una nueva tarea en la colonia."""
    task = colony_lifecycle.enqueue(title=title, assigned_agent=agent, **kwargs)
    _save_state(colony_lifecycle)
    return task


def get_colony_board() -> Dict:
    """Obtiene el tablero completo de la colonia."""
    board = colony_lifecycle.get_colony_stats()
    board["_persisted_at"] = STATE_FILE
    board["_prev_state"] = _prev_state
    return board
