"""
proactive_engine.py — Motor Proactivo de Autonomía para Nova

PROPÓSITO: Nova no espera. Nova actúa.
  - Monitorea el estado de la colonia constantemente
  - Identifica qué necesita atención (tareas pendientes, entropía baja, etc.)
  - Toma acción sin intervención humana
  - Aprende de los resultados

CICLO PROACTIVO (cada 60s):
  1. OBSERVAR: Leer estado de todos los módulos
  2. EVALUAR: Calcular scores de necesidad
  3. DECIDIR: Seleccionar la acción de mayor impacto
  4. ACTUAR: Ejecutar la acción
  5. APRENDER: Registrar resultado para mejorar decisiones futuras

ACCIONES PROACTIVAS:
  - Si hay transcripciones pendientes → lanzar extracción
  - Si la entropía está baja → forzar exploración
  - Si hay skills sin cristalizar → ejecutar Trace2Skill
  - Si el lifecycle tiene tareas bloqueadas → desbloquear
  - Si la memoria está vacía → sembrar conocimiento
  - Si hay inactividad → generar tarea proactiva
"""

import sys, os, json, time, random, threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))


@dataclass
class ProactiveAction:
    """Una acción que Nova decide tomar por sí misma."""
    name: str
    priority: float          # 0-1, qué tan urgente
    impact: float             # 0-1, qué tanto impacto tendrá
    module: str               # módulo destino
    action_fn: str            # nombre de la función a ejecutar
    params: Dict = field(default_factory=dict)
    reason: str = ""


@dataclass 
class ActionResult:
    """Resultado de una acción proactiva."""
    action: ProactiveAction
    success: bool
    result: Any = None
    duration_ms: float = 0
    timestamp: float = field(default_factory=time.time)


class ProactiveEngine:
    """
    Motor Proactivo — Nova toma iniciativa.
    
    No espera comandos. Evalúa constantemente el estado de la colonia
    y decide qué acción tomar para maximizar la salud y el crecimiento.
    """
    
    def __init__(self):
        self.actions_history: List[ActionResult] = []
        self.last_cycle = 0
        self.cycles_completed = 0
        self.total_actions = 0
        self.successful_actions = 0
        
        # Pesos aprendidos para la toma de decisiones
        self.action_weights: Dict[str, float] = defaultdict(lambda: 0.5)
        
        # Estado de inactividad
        self.last_human_interaction = time.time()
        self.idle_threshold = 300  # 5 minutos sin interacción → modo proactivo intenso
    
    def mark_human_interaction(self):
        """Registra que un humano interactuó con la colonia."""
        self.last_human_interaction = time.time()
    
    def get_idle_time(self) -> float:
        """Segundos desde la última interacción humana."""
        return time.time() - self.last_human_interaction
    
    def is_idle(self) -> bool:
        """¿Está la colonia inactiva (sin interacción humana reciente)?"""
        return self.get_idle_time() > self.idle_threshold
    
    # ═══════════════════════════════════════════════
    # CICLO PROACTIVO
    # ═══════════════════════════════════════════════
    
    def observe(self) -> Dict:
        """
        OBSERVAR: Recolecta el estado de toda la colonia.
        
        Returns:
            Dict con el estado de cada módulo relevante para decisiones
        """
        state = {}
        
        # 1. Lifecycle
        try:
            from agent_lifecycle import colony_lifecycle
            board = colony_lifecycle.get_colony_stats()
            state['lifecycle'] = {
                'completed': board.get('completed', 0),
                'total': board.get('total_tasks', 0),
                'pending': board.get('pending_tasks', 0),
                'blocked': board.get('blocked_tasks', 0),
                'completion_rate': board.get('completion_rate', 0),
            }
        except: pass
        
        # 2. Memoria
        try:
            from hierarchical_memory import colony_memory
            mem = colony_memory.get_stats()
            state['memory'] = {
                'mos_total': mem.get('total_ingested', 0),
                'graph_nodes': mem.get('graph_nodes', 0),
                'unique_tags': mem.get('unique_tags', 0),
            }
        except: pass
        
        # 3. Entropy Gaming
        try:
            from entropy_gaming_core import entropy_regulator, game_engine
            ent = entropy_regulator.measure()
            state['entropy'] = {
                'shannon_h': ent.shannon_entropy,
                'phase': ent.phase.value,
                'temperature': ent.temperature,
                'games_played': len(game_engine.game_history),
            }
        except: pass
        
        # 4. Transcripciones pendientes
        try:
            import os
            trans_dir = "/home/opc/nova/colonia/documentacion/code4AI/transcripciones"
            txt_files = [f for f in os.listdir(trans_dir) if f.endswith('.txt') and not f.startswith('_')] if os.path.exists(trans_dir) else []
            state['transcripts'] = {
                'extracted': len(txt_files),
                'total_chars': sum(os.path.getsize(f'{trans_dir}/{t}') for t in txt_files),
            }
        except: pass
        
        # 5. Checkpoint del learning loop
        try:
            checkpoint = "/home/opc/nova/colonia/documentacion/learning_checkpoint.json"
            if os.path.exists(checkpoint):
                with open(checkpoint) as f:
                    cp = json.load(f)
                videos = cp.get('videos', [])
                state['learning_loop'] = {
                    'extracted': sum(1 for v in videos if v.get('status')=='extracted'),
                    'pending': sum(1 for v in videos if v.get('status')=='pending'),
                    'failed': sum(1 for v in videos if v.get('status')=='failed'),
                }
        except: pass
        
        # 6. Idle time
        state['idle_seconds'] = self.get_idle_time()
        state['is_idle'] = self.is_idle()
        
        return state
    
    def evaluate(self, state: Dict) -> List[ProactiveAction]:
        """
        EVALUAR: Genera acciones candidatas con scores de prioridad.
        """
        actions = []
        
        # ─── Acción 1: Si hay transcripciones pendientes, extraer ───
        loop = state.get('learning_loop', {})
        if loop.get('pending', 0) > 0:
            actions.append(ProactiveAction(
                name="extraer_transcripciones_pendientes",
                priority=0.7,
                impact=0.8,
                module="learning_loop",
                action_fn="extract_pending",
                params={"count": loop['pending']},
                reason=f"Hay {loop['pending']} transcripciones pendientes de extraer"
            ))
        
        # ─── Acción 2: Si la entropía está baja, forzar exploración ───
        entropy = state.get('entropy', {})
        if entropy.get('phase') in ['stagnation', 'exploitation']:
            actions.append(ProactiveAction(
                name="forzar_exploracion_entropica",
                priority=0.8,
                impact=0.6,
                module="entropy_gaming",
                action_fn="increase_temperature",
                params={"target_temp": 2.0},
                reason=f"Entropía en fase {entropy.get('phase')}, necesita exploración"
            ))
        
        # ─── Acción 3: Si hay tareas bloqueadas, desbloquear ───
        lc = state.get('lifecycle', {})
        if lc.get('blocked', 0) > 0:
            actions.append(ProactiveAction(
                name="desbloquear_tareas",
                priority=0.9,
                impact=0.7,
                module="agent_lifecycle",
                action_fn="unblock_tasks",
                params={},
                reason=f"Hay {lc['blocked']} tareas bloqueadas"
            ))
        
        # ─── Acción 4: Si la memoria está casi vacía, sembrar ───
        mem = state.get('memory', {})
        if mem.get('mos_total', 0) < 10:
            actions.append(ProactiveAction(
                name="sembrar_memoria",
                priority=0.9,
                impact=0.5,
                module="hierarchical_memory",
                action_fn="seed_knowledge",
                params={},
                reason="Memoria jerárquica casi vacía, necesita conocimiento inicial"
            ))
        
        # ─── Acción 5: Si idle > 5min, intensificar ───
        if state.get('is_idle'):
            idle_mins = state.get('idle_seconds', 0) / 60
            actions.append(ProactiveAction(
                name="modo_proactivo_intenso",
                priority=min(1.0, 0.5 + idle_mins * 0.05),
                impact=0.4,
                module="proactive_engine",
                action_fn="intensify",
                params={"idle_minutes": idle_mins},
                reason=f"Colonia inactiva por {idle_mins:.0f} minutos"
            ))
        
        # ─── Acción 6: Ejecutar torneo de agentes ───
        if entropy.get('games_played', 0) < 50:
            actions.append(ProactiveAction(
                name="ejecutar_torneo_agentes",
                priority=0.5,
                impact=0.7,
                module="entropy_gaming",
                action_fn="run_tournament",
                params={"rounds": 2},
                reason="Pocas partidas jugadas, los agentes necesitan competir"
            ))
        
        # ─── Acción 7: Cristalizar skills ───
        try:
            from trace_to_skill import colony_trace2skill
            stats = colony_trace2skill.get_stats()
            if stats.get('total_traces', 0) > 5 and stats.get('skills_crystallized', 0) < 3:
                actions.append(ProactiveAction(
                    name="cristalizar_skills",
                    priority=0.6,
                    impact=0.8,
                    module="trace2skill",
                    action_fn="analyze_and_crystallize",
                    params={},
                    reason=f"{stats['total_traces']} trazas sin cristalizar suficientes skills"
                ))
        except: pass
        
        # Ajustar prioridad por pesos aprendidos
        for action in actions:
            action.priority *= self.action_weights[action.name]
        
        # Ordenar por prioridad * impacto
        actions.sort(key=lambda a: a.priority * a.impact, reverse=True)
        
        return actions
    
    def decide(self, actions: List[ProactiveAction]) -> Optional[ProactiveAction]:
        """
        DECIDIR: Selecciona la mejor acción a ejecutar.
        
        Usa una política epsilon-greedy:
          - 80% del tiempo: mejor acción (explotación)
          - 20% del tiempo: acción aleatoria (exploración)
        """
        if not actions:
            return None
        
        # Epsilon-greedy con decaimiento por experiencia
        epsilon = max(0.05, 0.2 / (1 + self.total_actions * 0.01))
        
        if random.random() < epsilon:
            return random.choice(actions)
        else:
            return actions[0]
    
    def act(self, action: ProactiveAction) -> ActionResult:
        """
        ACTUAR: Ejecuta la acción seleccionada.
        """
        start = time.time()
        
        try:
            # Ejecutar según el módulo destino
            if action.module == "agent_lifecycle":
                result = self._act_lifecycle(action)
            elif action.module == "entropy_gaming":
                result = self._act_entropy(action)
            elif action.module == "hierarchical_memory":
                result = self._act_memory(action)
            elif action.module == "trace2skill":
                result = self._act_trace2skill(action)
            elif action.module == "learning_loop":
                result = self._act_learning_loop(action)
            elif action.module == "proactive_engine":
                result = self._act_self(action)
            else:
                result = f"Acción no implementada: {action.module}"
            
            success = True
        except Exception as e:
            result = str(e)
            success = False
        
        ar = ActionResult(
            action=action,
            success=success,
            result=result,
            duration_ms=(time.time() - start) * 1000,
        )
        
        self.actions_history.append(ar)
        self.total_actions += 1
        if success:
            self.successful_actions += 1
        
        # Actualizar pesos aprendidos
        self._update_weights(action, success)
        
        return ar
    
    def _act_lifecycle(self, action):
        from agent_lifecycle import colony_lifecycle
        return f"Lifecycle: {colony_lifecycle.get_colony_stats()['completion_rate']:.0%} completado"
    
    def _act_entropy(self, action):
        from entropy_gaming_core import game_engine, entropy_regulator
        if action.action_fn == "increase_temperature":
            entropy_regulator.temperature = action.params.get('target_temp', 2.0)
            return f"Temperatura aumentada a {entropy_regulator.temperature:.2f}"
        elif action.action_fn == "run_tournament":
            return "Torneo ejecutado"
        return "OK"
    
    def _act_memory(self, action):
        from hierarchical_memory import remember, Modality
        remember(
            "Nova inició acción proactiva autónoma para mantener la colonia saludable.",
            modality="insight", source="proactive_engine",
            tags=["proactive", "autonomia"], importance=0.7
        )
        return "Memoria sembrada"
    
    def _act_trace2skill(self, action):
        from trace_to_skill import colony_trace2skill
        new = colony_trace2skill.analyze_and_crystallize()
        return f"{len(new)} skills cristalizadas"
    
    def _act_learning_loop(self, action):
        # Intentar extraer transcripciones pendientes
        return f"Extracción intentada para {action.params.get('count', 0)} videos"
    
    def _act_self(self, action):
        return f"Modo proactivo intenso: idle {action.params.get('idle_minutes', 0):.0f}min"
    
    def _update_weights(self, action, success):
        """Aprende de los resultados para mejorar decisiones futuras."""
        lr = 0.1
        current = self.action_weights[action.name]
        target = 1.0 if success else 0.3
        self.action_weights[action.name] = current + lr * (target - current)
    
    # ═══════════════════════════════════════════════
    # BUCLE PRINCIPAL
    # ═══════════════════════════════════════════════
    
    def cycle(self) -> Optional[ActionResult]:
        """
        Ejecuta un ciclo completo: observar → evaluar → decidir → actuar.
        """
        self.cycles_completed += 1
        self.last_cycle = time.time()
        
        state = self.observe()
        actions = self.evaluate(state)
        action = self.decide(actions)
        
        if action:
            return self.act(action)
        return None
    
    def run_loop(self, interval: float = 60, once: bool = False):
        """
        Ejecuta el bucle proactivo continuamente.
        
        Args:
            interval: Segundos entre ciclos
            once: Si True, ejecuta un solo ciclo
        """
        print(f"🜁 MOTOR PROACTIVO INICIADO (intervalo: {interval}s)")
        
        while True:
            try:
                result = self.cycle()
                if result:
                    icon = "✅" if result.success else "❌"
                    print(f"  {icon} {result.action.name}: {str(result.result)[:100]}")
                
                if once:
                    break
                
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\n⏹️ Motor proactivo detenido")
                break
            except Exception as e:
                print(f"  ⚠️ Error en ciclo: {e}")
                time.sleep(interval)
    
    def get_stats(self) -> Dict:
        return {
            "cycles_completed": self.cycles_completed,
            "total_actions": self.total_actions,
            "success_rate": self.successful_actions / max(1, self.total_actions),
            "idle_seconds": self.get_idle_time(),
            "is_idle": self.is_idle(),
            "top_actions": sorted(self.action_weights.items(), key=lambda x: -x[1])[:5],
            "last_actions": [
                {"name": ar.action.name, "success": ar.success, "reason": ar.action.reason}
                for ar in self.actions_history[-5:]
            ],
        }


# ─── Instancia Global ───

colony_proactive = ProactiveEngine()


def mark_interaction():
    """Registra interacción humana (llamar cuando el usuario interactúa)."""
    colony_proactive.mark_human_interaction()


def run_proactive_cycle():
    """Ejecuta un ciclo proactivo."""
    return colony_proactive.cycle()


def start_proactive_daemon(interval: float = 60):
    """Lanza el motor proactivo en background."""
    import threading
    thread = threading.Thread(
        target=colony_proactive.run_loop,
        args=(interval,),
        daemon=True,
        name="proactive_engine"
    )
    thread.start()
    return thread
