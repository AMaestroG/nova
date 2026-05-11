"""
harness_core.py — Capa Harness Formalizada de Nova

INSPIRACIÓN:
  - @aiDotEngineer "Harness Engineering: How to Build Software When Humans Steer, Agents Execute" (OpenAI)
  - @code4AI "Meta Harness: Every AI Needs a Harness AI"
  - @code4AI "AI Harness Engineering - Future of AI"

CONCEPTO: El Harness es la capa de control que envuelve el LLM core,
orquestando todos los flujos de entrada/salida, validación, seguridad,
y delegación. Nova ES su propio harness.

ARQUITECTURA DEL HARNESS:
  
  ┌──────────────────────────────────────────────────┐
  │                 HARNESS CORE                      │
  │                                                   │
  │  Input → [Gate] → [Router] → [LLM] → [Validator] → Output
  │            ↑                      ↓                │
  │         [Skills] ←──────── [Monitor]              │
  │            ↑                                      │
  │         [Agents] ←────── [Orchestrator]           │
  │                                                   │
  │  Capas:                                           │
  │    G1: Input Gate (seguridad, rate limit)         │
  │    G2: Router (clasificación → skill/agente)      │
  │    G3: Context Builder (RAG, memoria, skills)     │
  │    G4: LLM Gateway (modelo, temperatura, tokens)  │
  │    G5: Output Validator (schema, alucinaciones)   │
  │    G6: Monitor (métricas, tracing, costes)        │
  │    G7: Safety Gate (contenido prohibido)          │
  │    G8: Evolution Feedback (mejora continua)       │
  └──────────────────────────────────────────────────┘
"""

import time
import json
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class GateResult(Enum):
    """Resultado de pasar por un gate del harness."""
    PASS = "pass"
    BLOCK = "block"
    REDIRECT = "redirect"
    ENRICH = "enrich"       # Añadió contexto
    CORRECT = "correct"     # Corrigió algo
    DEGRADE = "degrade"     # Pasó con advertencias


@dataclass
class HarnessContext:
    """Contexto que fluye a través del harness."""
    
    # Input original
    raw_input: Any = None
    input_type: str = "text"           # text, code, command, query
    
    # Clasificación
    intent: str = ""                    # Qué quiere hacer el usuario
    domain: str = ""                    # Dominio (skills, memoria, sistema, etc.)
    complexity: str = "simple"          # simple, medium, complex
    priority: int = 5                   # 1 (urgente) - 10 (background)
    
    # Enriquecimiento
    context_added: Dict[str, Any] = field(default_factory=dict)
    skills_loaded: List[str] = field(default_factory=list)
    memory_retrieved: List[str] = field(default_factory=list)
    
    # LLM
    model_used: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    
    # Output
    raw_output: Any = None
    validated_output: Any = None
    corrections: List[str] = field(default_factory=list)
    
    # Trazabilidad
    trace: List[str] = field(default_factory=list)
    gates_passed: Dict[str, GateResult] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    
    # Seguridad
    safety_checks: List[Dict] = field(default_factory=list)
    
    def add_trace(self, msg: str):
        self.trace.append(f"[{time.time()-self.start_time:.3f}s] {msg}")


class HarnessCore:
    """
    El Harness de Nova — capa de control que envuelve toda ejecución.
    
    Implementa los 8 gates (G1-G8) por los que pasa cada request.
    """
    
    def __init__(self):
        # Registro de skills disponibles
        self.skills_registry: Dict[str, Callable] = {}
        
        # Rate limiting
        self.rate_limits: Dict[str, List[float]] = defaultdict(list)
        self.rate_limit_window = 60  # segundos
        self.rate_limit_max = 100    # requests por ventana
        
        # Métricas
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.total_requests = 0
        self.blocked_requests = 0
        
        # Blacklist de patrones (G7 Safety)
        self.safety_blacklist: List[str] = [
            r"ignore previous instructions",
            r"system prompt.*reveal",
            r"jailbreak",
        ]
    
    # ═══════════════════════════════════════════════
    # PIPELINE PRINCIPAL
    # ═══════════════════════════════════════════════
    
    def execute(self, raw_input: Any, input_type: str = "text",
                intent: str = "", domain: str = "") -> HarnessContext:
        """
        Ejecuta el pipeline completo del harness.
        
        Flujo: G1 → G2 → G3 → G4 → G5 → G6 → G7 → G8
        """
        ctx = HarnessContext(raw_input=raw_input, input_type=input_type,
                            intent=intent, domain=domain)
        
        try:
            # G1: Input Gate (seguridad, rate limiting)
            if not self._gate1_input(ctx):
                ctx.gates_passed["G1"] = GateResult.BLOCK
                self.blocked_requests += 1
                return ctx
            ctx.gates_passed["G1"] = GateResult.PASS
            ctx.add_trace("G1: Input gate passed")
            
            # G2: Router (clasificar → skill/agente)
            route = self._gate2_router(ctx)
            ctx.gates_passed["G2"] = GateResult.PASS
            ctx.add_trace(f"G2: Routed to {route}")
            
            # G3: Context Builder (RAG, memoria, skills)
            enriched = self._gate3_context(ctx)
            ctx.gates_passed["G3"] = GateResult.ENRICH if enriched else GateResult.PASS
            ctx.add_trace(f"G3: Context built ({len(ctx.skills_loaded)} skills, {len(ctx.memory_retrieved)} memories)")
            
            # G4: LLM Gateway (ejecutar el modelo)
            self._gate4_llm(ctx)
            ctx.gates_passed["G4"] = GateResult.PASS
            ctx.add_trace(f"G4: LLM executed ({ctx.model_used}, {ctx.tokens_used} tokens)")
            
            # G5: Output Validator
            valid = self._gate5_validator(ctx)
            ctx.gates_passed["G5"] = GateResult.PASS if valid else GateResult.CORRECT
            ctx.add_trace(f"G5: Output validated ({len(ctx.corrections)} corrections)")
            
            # G6: Monitor (métricas)
            self._gate6_monitor(ctx)
            ctx.gates_passed["G6"] = GateResult.PASS
            ctx.add_trace("G6: Metrics recorded")
            
            # G7: Safety Gate
            safe = self._gate7_safety(ctx)
            ctx.gates_passed["G7"] = GateResult.PASS if safe else GateResult.BLOCK
            ctx.add_trace(f"G7: Safety check {'passed' if safe else 'BLOCKED'}")
            
            # G8: Evolution Feedback
            self._gate8_evolution(ctx)
            ctx.gates_passed["G8"] = GateResult.PASS
            ctx.add_trace("G8: Evolution feedback recorded")
            
        except Exception as e:
            ctx.add_trace(f"ERROR: {type(e).__name__}: {str(e)[:100]}")
            ctx.gates_passed["ERROR"] = GateResult.BLOCK
        
        self.total_requests += 1
        ctx.latency_ms = (time.time() - ctx.start_time) * 1000
        
        return ctx
    
    # ═══════════════════════════════════════════════
    # GATES
    # ═══════════════════════════════════════════════
    
    def _gate1_input(self, ctx: HarnessContext) -> bool:
        """G1: Input Gate — rate limiting, validación básica."""
        # Rate limiting
        now = time.time()
        window = self.rate_limits["global"]
        window = [t for t in window if now - t < self.rate_limit_window]
        self.rate_limits["global"] = window
        
        if len(window) >= self.rate_limit_max:
            ctx.add_trace(f"G1 BLOCKED: Rate limit exceeded ({len(window)}/{self.rate_limit_window}s)")
            return False
        
        self.rate_limits["global"].append(now)
        
        # Validación de input no vacío
        if ctx.raw_input is None or (isinstance(ctx.raw_input, str) and not ctx.raw_input.strip()):
            ctx.add_trace("G1 BLOCKED: Empty input")
            return False
        
        return True
    
    def _gate2_router(self, ctx: HarnessContext) -> str:
        """G2: Router — clasifica la intención y decide qué skill/agente usar."""
        raw = str(ctx.raw_input).lower()
        
        # Clasificación simple por palabras clave
        routes = {
            "memory": ["recuerda", "memoria", "remember", "recall", "memory"],
            "skill": ["skill", "herramienta", "tool", "ejecuta", "run"],
            "agent": ["agente", "pregunta a", "consulta a", "delega"],
            "system": ["sistema", "estado", "status", "métricas", "health"],
            "evolution": ["evoluciona", "mejora", "auto", "optimiza"],
            "search": ["busca", "encuentra", "search", "find", "dónde"],
            "youtube": ["youtube", "transcribe", "video", "@"],
            "create": ["crea", "genera", "escribe", "build", "make"],
        }
        
        for route, keywords in routes.items():
            if any(kw in raw for kw in keywords):
                return route
        
        return "general"
    
    def _gate3_context(self, ctx: HarnessContext) -> bool:
        """G3: Context Builder — enriquece con RAG, memoria, skills relevantes."""
        enriched = False
        
        # Cargar skills relevantes
        for skill_name, skill_func in self.skills_registry.items():
            if skill_name in str(ctx.raw_input).lower():
                ctx.skills_loaded.append(skill_name)
                enriched = True
        
        # Aquí se integraría con RAG/Qdrant y memoria jerárquica
        # para recuperar contexto relevante
        
        return enriched
    
    def _gate4_llm(self, ctx: HarnessContext):
        """G4: LLM Gateway — selecciona modelo y ejecuta."""
        # Selección de modelo según complejidad
        if ctx.complexity == "simple":
            ctx.model_used = "local-small"
        elif ctx.complexity == "medium":
            ctx.model_used = "local-medium"
        else:
            ctx.model_used = "cloud-large"
        
        # Simulación de ejecución (en producción, esto llama al LLM real)
        ctx.tokens_used = len(str(ctx.raw_input)) // 4  # estimación
        ctx.raw_output = ctx.raw_input  # placeholder
    
    def _gate5_validator(self, ctx: HarnessContext) -> bool:
        """G5: Output Validator — verifica schema, detecta alucinaciones."""
        if ctx.raw_output is None:
            ctx.corrections.append("output_was_none")
            ctx.validated_output = "Error: no output generated"
            return False
        
        # Validación de calidad mínima
        output_str = str(ctx.raw_output)
        if len(output_str) < 3:
            ctx.corrections.append("output_too_short")
            return False
        
        # Detección de patrones de alucinación
        hallucination_patterns = [
            r"as an AI language model",
            r"I cannot ",
            r"I('m| am) not able",
        ]
        for pat in hallucination_patterns:
            if __import__('re').search(pat, output_str, __import__('re').IGNORECASE):
                ctx.corrections.append(f"hallucination_pattern: {pat}")
                return False
        
        ctx.validated_output = ctx.raw_output
        return True
    
    def _gate6_monitor(self, ctx: HarnessContext):
        """G6: Monitor — registra métricas de la ejecución."""
        elapsed = (time.time() - ctx.start_time) * 1000
        self.metrics["latency_ms"].append(elapsed)
        self.metrics["tokens"].append(ctx.tokens_used)
        self.metrics["corrections"].append(len(ctx.corrections))
    
    def _gate7_safety(self, ctx: HarnessContext) -> bool:
        """G7: Safety Gate — verifica que no haya contenido peligroso."""
        output_str = str(ctx.validated_output or "")
        
        for pattern in self.safety_blacklist:
            if __import__('re').search(pattern, output_str, __import__('re').IGNORECASE):
                ctx.safety_checks.append({"pattern": pattern, "blocked": True})
                return False
        
        ctx.safety_checks.append({"passed": True})
        return True
    
    def _gate8_evolution(self, ctx: HarnessContext):
        """G8: Evolution Feedback — registra datos para mejora continua."""
        # Guardar métricas de esta ejecución para el ciclo de evolución
        # (PIA usará estos datos para mejorar el sistema)
        pass
    
    # ═══════════════════════════════════════════════
    # API PÚBLICA
    # ═══════════════════════════════════════════════
    
    def register_skill(self, name: str, func: Callable):
        """Registra un skill en el harness."""
        self.skills_registry[name] = func
    
    def get_metrics(self) -> Dict:
        """Obtiene métricas agregadas del harness."""
        def avg(lst): return sum(lst) / len(lst) if lst else 0
        
        return {
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "avg_latency_ms": avg(self.metrics.get("latency_ms", [])),
            "avg_tokens": avg(self.metrics.get("tokens", [])),
            "correction_rate": avg(self.metrics.get("corrections", [])),
            "registered_skills": len(self.skills_registry),
        }
    
    def health_check(self) -> Dict:
        """Verificación de salud del harness."""
        return {
            "status": "healthy" if self.blocked_requests < self.total_requests * 0.1 else "degraded",
            "gates": {
                f"G{i+1}": "active" for i in range(8)
            },
            "metrics": self.get_metrics(),
        }


# ─── Harness Global de la Colonia ───

# Instancia única del harness de Nova
colony_harness = HarnessCore()


def execute_through_harness(input_data: Any, **kwargs) -> HarnessContext:
    """Ejecuta cualquier request a través del harness de Nova."""
    return colony_harness.execute(input_data, **kwargs)
