"""
scientific_gaming.py — Gamificación como Herramienta de Evaluación Científica Universal

CONCEPTO FUNDACIONAL: Cualquier tarea, sistema o proceso puede ser formulado como 
un JUEGO CIENTÍFICO con reglas claras, métricas ponderadas, y función de recompensa.
Esto transforma la gamificación de un mecanismo de competencia entre agentes a un 
MARCO UNIVERSAL de evaluación y optimización.

INSPIRACIÓN:
  - DeepMind: AlphaGo/AlphaFold como juegos científicos
  - Karpathy: "Si no puedes evaluarlo, no puedes automatizarlo"
  - @code4AI: MEMORY.md paper — necesidad de RL con métricas objetivas
  - Teoría de Juegos + Reinforcement Learning

ARQUITECTURA:
  
  CUALQUIER COSA → [Scientific Game] → Métricas → RL → Optimización
  
  ┌─────────────────────────────────────────────────────┐
  │              SCIENTIFIC GAME ENGINE                 │
  │                                                     │
  │  Game = {                                           │
  │    task: "lo que sea",                              │
  │    metrics: {                                       │
  │      "precision":   {weight: 0.4, goal: 0.95},     │
  │      "velocidad":   {weight: 0.3, goal: "<100ms"}, │
  │      "eficiencia":  {weight: 0.2, goal: 0.8},      │
  │      "novedad":     {weight: 0.1, goal: "max"},    │
  │    },                                              │
  │    reward_fn: weighted_sum(metrics),               │
  │    rules: [...],                                    │
  │  }                                                  │
  │                                                     │
  │  Play → Measure → Reward → Learn → Repeat          │
  └─────────────────────────────────────────────────────┘
"""

import json, time, math, random
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import os, sys


# ═══════════════════════════════════════════════
# DEFINICIÓN DE JUEGO CIENTÍFICO
# ═══════════════════════════════════════════════

class GoalType(Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"
    TARGET = "target"        # Alcanzar un valor exacto
    THRESHOLD = "threshold"  # Superar un umbral
    RANGE = "range"          # Mantenerse en un rango


@dataclass
class MetricConfig:
    """Configuración de una métrica científica."""
    name: str
    weight: float = 1.0              # Peso en la función de recompensa
    goal: Union[float, str] = 0.0    # Objetivo (número o "max"/"min")
    goal_type: GoalType = GoalType.MAXIMIZE
    unit: str = ""                   # Unidad (ms, %, count, etc.)
    baseline: float = 0.0            # Valor base para normalizar
    description: str = ""
    
    def score(self, value: float) -> float:
        """
        Calcula el score normalizado (0-1) para un valor de métrica.
        """
        if self.goal_type == GoalType.MAXIMIZE:
            if isinstance(self.goal, str) and self.goal == "max":
                return min(1.0, max(0.0, value / max(1.0, self.baseline)))
            goal_val = float(self.goal) if not isinstance(self.goal, str) else 1.0
            return min(1.0, value / max(0.001, goal_val))
        
        elif self.goal_type == GoalType.MINIMIZE:
            if isinstance(self.goal, str) and self.goal == "min":
                return max(0.0, 1.0 - value / max(1.0, self.baseline))
            goal_val = float(self.goal) if not isinstance(self.goal, str) else 0.0
            if goal_val == 0:
                return max(0.0, 1.0 - value / max(0.001, self.baseline))
            return max(0.0, min(1.0, goal_val / max(0.001, value)))
        
        elif self.goal_type == GoalType.TARGET:
            target = float(self.goal) if not isinstance(self.goal, str) else 0.5
            distance = abs(value - target)
            return max(0.0, 1.0 - distance / max(0.001, target))
        
        elif self.goal_type == GoalType.THRESHOLD:
            threshold = float(self.goal) if not isinstance(self.goal, str) else 0.5
            return 1.0 if value >= threshold else value / max(0.001, threshold)
        
        elif self.goal_type == GoalType.RANGE:
            if isinstance(self.goal, str):
                return 0.5
            low, high = (0.3, 0.7)  # default range
            if isinstance(self.goal, (list, tuple)) and len(self.goal) == 2:
                low, high = self.goal
            if low <= value <= high:
                return 1.0
            distance = min(abs(value - low), abs(value - high))
            return max(0.0, 1.0 - distance / max(0.001, (high - low) / 2))
        
        return 0.5


@dataclass
class ScientificGame:
    """
    Un juego científico que evalúa cualquier tarea.
    
    Ejemplos de juegos:
      - "Extraer transcripción de YouTube" 
      - "Indexar documento en Qdrant"
      - "Responder consulta RAG"
      - "Optimizar memoria del enjambre"
      - "Cristalizar una skill"
      - CUALQUIER tarea de la colonia
    """
    name: str
    description: str = ""
    
    # Métricas
    metrics: Dict[str, MetricConfig] = field(default_factory=dict)
    
    # La tarea a ejecutar
    task_fn: Optional[Callable] = None
    task_params: Dict = field(default_factory=dict)
    
    # Reglas
    max_attempts: int = 1
    timeout_seconds: float = 60.0
    validators: List[Callable] = field(default_factory=list)
    
    # Resultados acumulados
    history: List[Dict] = field(default_factory=list)
    best_score: float = 0.0
    best_params: Dict = field(default_factory=dict)
    
    def add_metric(self, name: str, weight: float = 1.0, goal=0.0, 
                   goal_type: GoalType = GoalType.MAXIMIZE, unit: str = "",
                   description: str = ""):
        """Añade una métrica al juego."""
        baseline = goal if isinstance(goal, (int, float)) else 1.0
        self.metrics[name] = MetricConfig(
            name=name, weight=weight, goal=goal,
            goal_type=goal_type, unit=unit, baseline=baseline,
            description=description,
        )
        return self
    
    def calculate_reward(self, measured: Dict[str, float]) -> Tuple[float, Dict]:
        """
        Calcula la recompensa total como suma ponderada de métricas.
        
        Args:
            measured: Dict con valores medidos {metric_name: value}
        
        Returns:
            (reward_total, breakdown) donde breakdown tiene cada métrica con su score
        """
        if not self.metrics:
            return 0.0, {}
        
        total_weight = sum(m.weight for m in self.metrics.values())
        if total_weight == 0:
            return 0.0, {}
        
        reward = 0.0
        breakdown = {}
        
        for name, metric in self.metrics.items():
            value = measured.get(name, 0.0)
            score = metric.score(value)
            weighted = score * metric.weight / total_weight
            reward += weighted
            breakdown[name] = {
                "value": value,
                "score": score,
                "weighted": weighted,
                "goal": str(metric.goal),
            }
        
        return reward, breakdown
    
    def play(self, **kwargs) -> Dict:
        """
        Ejecuta una partida del juego científico.
        
        Returns:
            Dict con resultado completo: reward, metrics, breakdown, etc.
        """
        start = time.time()
        result = {
            "game": self.name,
            "timestamp": time.time(),
            "attempt": len(self.history) + 1,
            "success": False,
            "reward": 0.0,
            "metrics": {},
            "breakdown": {},
            "duration_ms": 0,
        }
        
        try:
            # Ejecutar la tarea
            if self.task_fn:
                output = self.task_fn(**{**self.task_params, **kwargs})
            else:
                output = kwargs.get("output", {})
            
            # Medir métricas
            measured = {}
            for name in self.metrics:
                # Intentar obtener del output o medir directamente
                if isinstance(output, dict) and name in output:
                    measured[name] = float(output[name])
                elif name in kwargs:
                    measured[name] = float(kwargs[name])
                else:
                    measured[name] = 0.0
            
            # Validar
            valid = all(v(output) for v in self.validators) if self.validators else True
            
            # Calcular recompensa
            reward, breakdown = self.calculate_reward(measured)
            
            result["success"] = valid and reward > 0
            result["reward"] = reward
            result["metrics"] = measured
            result["breakdown"] = breakdown
            result["output"] = output if isinstance(output, (str, int, float, bool)) else str(output)[:200]
            
            # Actualizar mejor puntuación
            if reward > self.best_score:
                self.best_score = reward
                self.best_params = kwargs
            
        except Exception as e:
            result["error"] = str(e)
        
        result["duration_ms"] = (time.time() - start) * 1000
        self.history.append(result)
        
        return result
    
    def get_stats(self) -> Dict:
        """Estadísticas del juego."""
        if not self.history:
            return {"games_played": 0}
        
        rewards = [h["reward"] for h in self.history]
        return {
            "games_played": len(self.history),
            "best_reward": max(rewards),
            "avg_reward": sum(rewards) / len(rewards),
            "trend": rewards[-5:] if len(rewards) >= 5 else rewards,
            "improvement": (rewards[-1] - rewards[0]) if len(rewards) >= 2 else 0,
            "best_params": self.best_params,
        }


# ═══════════════════════════════════════════════
# SCIENTIFIC GAME ENGINE — Catálogo de Juegos
# ═══════════════════════════════════════════════

class ScientificGameEngine:
    """
    Motor que gestiona múltiples juegos científicos para evaluar
    cualquier aspecto de la colonia.
    """
    
    def __init__(self):
        self.games: Dict[str, ScientificGame] = {}
        self.global_history: List[Dict] = []
        
        # Registrar juegos predefinidos
        self._register_default_games()
    
    def register_game(self, game: ScientificGame):
        """Registra un juego científico."""
        self.games[game.name] = game
        return game
    
    def create_game(self, name: str, description: str = "") -> ScientificGame:
        """Crea y registra un nuevo juego."""
        game = ScientificGame(name=name, description=description)
        self.games[name] = game
        return game
    
    def play(self, game_name: str, **kwargs) -> Dict:
        """Juega una partida de un juego registrado."""
        game = self.games.get(game_name)
        if not game:
            return {"error": f"Juego '{game_name}' no encontrado"}
        
        result = game.play(**kwargs)
        self.global_history.append(result)
        return result
    
    def evaluate_anything(self, task_name: str, metrics: Dict[str, Dict], 
                          output: Dict[str, float]) -> Dict:
        """
        EVALÚA CUALQUIER COSA como un juego científico.
        
        Esta es la función clave: conviertes cualquier tarea en un juego
        definiendo métricas y midiendo el output.
        
        Args:
            task_name: Nombre de la tarea
            metrics: Dict de métricas {name: {value, weight, goal, goal_type}}
            output: Dict con los valores medidos {metric_name: actual_value}
        
        Returns:
            Resultado completo con reward, scores, breakdown
        """
        # Crear juego on-the-fly
        game = ScientificGame(name=task_name)
        
        for mname, mconfig in metrics.items():
            game.add_metric(
                name=mname,
                weight=mconfig.get("weight", 1.0),
                goal=mconfig.get("goal", 1.0),
                goal_type=GoalType(mconfig.get("goal_type", "maximize")),
                unit=mconfig.get("unit", ""),
                description=mconfig.get("description", ""),
            )
        
        # Jugar con el output medido
        result = game.play(output=output, **output)
        
        # Guardar
        self.games[task_name] = game
        self.global_history.append(result)
        
        return result
    
    def get_leaderboard(self) -> List[Dict]:
        """Ranking de juegos por mejor recompensa."""
        rankings = []
        for name, game in self.games.items():
            if game.history:
                rankings.append({
                    "game": name,
                    "best_reward": game.best_score,
                    "games_played": len(game.history),
                    "trend": "↑" if len(game.history) >= 2 and game.history[-1]["reward"] > game.history[0]["reward"] else "→",
                })
        return sorted(rankings, key=lambda r: -r["best_reward"])
    
    def _register_default_games(self):
        """Registra juegos científicos predefinidos para la colonia."""
        
        # Juego 1: Extracción de Transcripción
        game = ScientificGame(
            name="transcript_extraction",
            description="Evaluar la calidad de extracción de transcripciones de YouTube"
        )
        game.add_metric("chars_extracted", weight=0.3, goal=10000, goal_type=GoalType.MAXIMIZE, unit="chars")
        game.add_metric("extraction_time_ms", weight=0.2, goal=30000, goal_type=GoalType.MINIMIZE, unit="ms")
        game.add_metric("success_rate", weight=0.4, goal=0.8, goal_type=GoalType.TARGET, unit="%")
        game.add_metric("novelty", weight=0.1, goal="max", goal_type=GoalType.MAXIMIZE)
        self.games[game.name] = game
        
        # Juego 2: Indexación Qdrant
        game = ScientificGame(name="qdrant_indexing", description="Evaluar indexación en Qdrant")
        game.add_metric("chunks_created", weight=0.3, goal=20, goal_type=GoalType.MAXIMIZE)
        game.add_metric("index_time_ms", weight=0.2, goal=5000, goal_type=GoalType.MINIMIZE, unit="ms")
        game.add_metric("dedup_saved", weight=0.3, goal=0.1, goal_type=GoalType.MAXIMIZE, unit="%")
        game.add_metric("retrieval_precision", weight=0.2, goal=0.9, goal_type=GoalType.TARGET)
        self.games[game.name] = game
        
        # Juego 3: RAG Query
        game = ScientificGame(name="rag_query", description="Evaluar calidad de consultas RAG")
        game.add_metric("relevance_score", weight=0.4, goal=0.8, goal_type=GoalType.TARGET)
        game.add_metric("response_time_ms", weight=0.2, goal=1000, goal_type=GoalType.MINIMIZE, unit="ms")
        game.add_metric("coverage", weight=0.2, goal=0.7, goal_type=GoalType.MAXIMIZE)
        game.add_metric("diversity", weight=0.2, goal=0.5, goal_type=GoalType.TARGET)
        self.games[game.name] = game
        
        # Juego 4: Skill Crystallization
        game = ScientificGame(name="skill_crystallization", description="Evaluar cristalización de skills")
        game.add_metric("skills_created", weight=0.3, goal=3, goal_type=GoalType.MAXIMIZE)
        game.add_metric("success_rate", weight=0.3, goal=0.8, goal_type=GoalType.THRESHOLD)
        game.add_metric("complexity_reduction", weight=0.2, goal=0.3, goal_type=GoalType.MAXIMIZE)
        game.add_metric("reusability", weight=0.2, goal=0.7, goal_type=GoalType.TARGET)
        self.games[game.name] = game
        
        # Juego 5: Memoria Jerárquica
        game = ScientificGame(name="hierarchical_memory", description="Evaluar eficiencia de memoria")
        game.add_metric("mos_created", weight=0.2, goal=50, goal_type=GoalType.MAXIMIZE)
        game.add_metric("dedup_ratio", weight=0.3, goal=0.3, goal_type=GoalType.TARGET)
        game.add_metric("retrieval_speed_ms", weight=0.2, goal=100, goal_type=GoalType.MINIMIZE, unit="ms")
        game.add_metric("graph_connectivity", weight=0.3, goal=0.5, goal_type=GoalType.MAXIMIZE)
        self.games[game.name] = game
    
    def get_stats(self) -> Dict:
        return {
            "total_games": len(self.games),
            "total_plays": len(self.global_history),
            "leaderboard": self.get_leaderboard()[:10],
        }


# ═══════════════════════════════════════════════
# RL INTEGRATION — De métricas a aprendizaje
# ═══════════════════════════════════════════════

class RLBridge:
    """
    Puente entre gamificación científica y Reinforcement Learning.
    
    Convierte los resultados de cualquier ScientificGame en:
      - Estado (state): métricas actuales
      - Acción (action): parámetros a ajustar
      - Recompensa (reward): score del juego
      - Política (policy): qué acción tomar para maximizar recompensa
    """
    
    def __init__(self):
        self.q_table: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.exploration_rate = 0.2
    
    def state_from_metrics(self, metrics: Dict[str, float]) -> str:
        """Convierte métricas en un estado discreto para Q-learning."""
        # Discretizar métricas en buckets
        parts = []
        for name, value in sorted(metrics.items()):
            if value < 0.3: bucket = "L"
            elif value < 0.7: bucket = "M"
            else: bucket = "H"
            parts.append(f"{name[:3]}={bucket}")
        return "|".join(parts) if parts else "default"
    
    def get_best_action(self, state: str, available_actions: List[str]) -> str:
        """Obtiene la mejor acción para un estado (epsilon-greedy)."""
        if not available_actions:
            return "none"
        
        # Exploración
        if random.random() < self.exploration_rate:
            return random.choice(available_actions)
        
        # Explotación
        q_values = {a: self.q_table[state].get(a, 0.0) for a in available_actions}
        return max(q_values, key=q_values.get)
    
    def update(self, state: str, action: str, reward: float, next_state: str, available_actions: List[str]):
        """Actualiza Q-table con Q-learning."""
        current_q = self.q_table[state].get(action, 0.0)
        
        # Max Q del siguiente estado
        next_qs = [self.q_table[next_state].get(a, 0.0) for a in available_actions]
        max_next_q = max(next_qs) if next_qs else 0.0
        
        # Q-learning update
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        self.q_table[state][action] = new_q
    
    def get_stats(self) -> Dict:
        return {
            "states_learned": len(self.q_table),
            "total_q_entries": sum(len(actions) for actions in self.q_table.values()),
            "exploration_rate": self.exploration_rate,
        }


# ═══════════════════════════════════════════════
# INSTANCIAS GLOBALES
# ═══════════════════════════════════════════════

scientific_engine = ScientificGameEngine()
rl_bridge = RLBridge()


def evaluate_anything(task_name: str, metrics: Dict, output: Dict) -> Dict:
    """
    Evalúa CUALQUIER COSA como un juego científico.
    
    Uso:
        result = evaluate_anything(
            "mi_tarea",
            metrics={
                "precision": {"weight": 0.5, "goal": 0.95, "goal_type": "maximize"},
                "velocidad": {"weight": 0.3, "goal": 100, "goal_type": "minimize", "unit": "ms"},
                "cobertura": {"weight": 0.2, "goal": 0.8, "goal_type": "target"},
            },
            output={"precision": 0.92, "velocidad": 150, "cobertura": 0.75}
        )
        print(f"Reward: {result['reward']:.2f}")
    """
    return scientific_engine.evaluate_anything(task_name, metrics, output)


def learn_from_game(game_name: str, action_space: List[str], num_episodes: int = 10) -> Dict:
    """
    Aplica RL sobre un juego científico para optimizar sus parámetros.
    
    Args:
        game_name: Nombre del juego registrado
        action_space: Lista de acciones posibles (ej: ["increase_temp", "decrease_temp"])
        num_episodes: Número de episodios de entrenamiento
    
    Returns:
        Estadísticas de aprendizaje
    """
    game = scientific_engine.games.get(game_name)
    if not game:
        return {"error": f"Juego no encontrado: {game_name}"}
    
    history = []
    for ep in range(num_episodes):
        # Elegir acción
        current_metrics = {m.name: m.baseline for m in game.metrics.values()} if game.history else {}
        if game.history:
            current_metrics = game.history[-1].get("metrics", current_metrics)
        
        state = rl_bridge.state_from_metrics(current_metrics)
        action = rl_bridge.get_best_action(state, action_space)
        
        # Ejecutar juego con parámetros modificados por la acción
        params = {"action": action, "episode": ep}
        result = game.play(**params)
        
        # Actualizar Q-table
        next_metrics = result.get("metrics", {})
        next_state = rl_bridge.state_from_metrics(next_metrics)
        rl_bridge.update(state, action, result["reward"], next_state, action_space)
        
        history.append({"episode": ep, "action": action, "reward": result["reward"]})
    
    return {
        "game": game_name,
        "episodes": num_episodes,
        "final_reward": history[-1]["reward"] if history else 0,
        "best_reward": max(h["reward"] for h in history) if history else 0,
        "history": history,
    }
