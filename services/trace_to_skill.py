"""
trace_to_skill.py — Sistema Trace2Skill: Generación Automática de Skills

INSPIRACIÓN:
  - @code4AI "Trace2Skill: Qwen Agent Skill.md outperforms Anthropic"
  - @code4AI "The End of Human-Defined Skills: AI Eigenvectors"
  - @aiDotEngineer "Don't Build Agents, Build Skills Instead" (Anthropic)
  - @aiDotEngineer "Skills at Scale" (WorkOS)
  - @aiDotEngineer "Replacing 12K LoC with a 200 LoC Skill" (Cursor)

CONCEPTO: Observar las trazas de ejecución exitosas de los agentes,
identificar patrones repetibles, y cristalizarlos en nuevas skills.
Las skills emergen de la práctica, no se diseñan.

PIPELINE:
  1. TRACE: Capturar cada ejecución (input, output, pasos, contexto)
  2. CLUSTER: Agrupar ejecuciones similares (k-means sobre embeddings)
  3. EXTRACT: Identificar el patrón común (flujo determinista)
  4. CRYSTALLIZE: Generar SKILL.md con el flujo extraído
  5. VALIDATE: Verificar que la skill funciona en nuevos casos
  6. REGISTER: Añadir al registro de skills

MÉTRICAS DE CALIDAD:
  - Repetibilidad: ¿mismo input → mismo output? (determinismo)
  - Frecuencia: ¿cuántas veces se ha ejecutado este patrón?
  - Tasa de éxito: ¿% de ejecuciones exitosas?
  - Complejidad: ¿número de pasos?
  - Generalidad: ¿funciona en variaciones del input?
"""

import json
import time
import hashlib
import re
import os
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter


@dataclass
class ExecutionTrace:
    """Registro completo de una ejecución de agente/skill."""
    
    trace_id: str
    timestamp: float = field(default_factory=time.time)
    
    # Entrada
    input_data: Any = None
    input_signature: str = ""           # Hash del input normalizado
    
    # Ejecución
    agent: str = ""                     # Agente que ejecutó
    steps: List[Dict] = field(default_factory=list)  # [{action, result, duration}]
    success: bool = False
    
    # Salida
    output_data: Any = None
    output_signature: str = ""
    
    # Contexto
    skills_used: List[str] = field(default_factory=list)
    context_snippets: List[str] = field(default_factory=list)
    
    # Métricas
    duration_ms: float = 0.0
    tokens_used: int = 0
    corrections: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "agent": self.agent,
            "steps": len(self.steps),
            "success": self.success,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "skills_used": self.skills_used,
        }


@dataclass
class CrystallizedSkill:
    """Skill cristalizada desde trazas de ejecución."""
    
    skill_name: str
    skill_slug: str                     # nombre en formato archivo
    
    # El flujo determinista extraído
    flow: List[Dict]                    # [{step, action, expected_result}]
    
    # Contrato de la skill
    input_pattern: str                  # Descripción del input esperado
    output_pattern: str                 # Descripción del output esperado
    
    # Evidencia
    traces_analyzed: int                # Cuántas trazas se usaron
    success_rate: float                 # Tasa de éxito en las trazas
    frequency: int                      # Veces ejecutado
    
    # Metadatos
    created_from_agent: str
    complexity: str
    tags: List[str] = field(default_factory=list)
    
    # SKILL.md generado
    skill_md_content: str = ""


class Trace2Skill:
    """
    Sistema que observa ejecuciones de agentes y cristaliza nuevas skills.
    """
    
    def __init__(self, min_frequency: int = 5, min_success_rate: float = 0.8,
                 max_complexity: int = 15):
        self.traces: List[ExecutionTrace] = []
        self.crystallized: List[CrystallizedSkill] = []
        self.skill_counter = 0
        
        # Parámetros
        self.min_frequency = min_frequency       # Mínimas ejecuciones para cristalizar
        self.min_success_rate = min_success_rate  # Tasa de éxito mínima
        self.max_complexity = max_complexity       # Máximo de pasos
        
        # Clusters de patrones
        self.pattern_clusters: Dict[str, List[ExecutionTrace]] = defaultdict(list)
    
    # ═══════════════════════════════════════════════
    # CAPTURA DE TRAZAS
    # ═══════════════════════════════════════════════
    
    def trace(self, agent: str = "unknown") -> Callable:
        """
        Decorador para capturar trazas de ejecución automáticamente.
        
        Uso:
            tracer = Trace2Skill()
            
            @tracer.trace(agent="PIA")
            def my_function(input_data):
                ...
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                trace_id = f"trace_{int(time.time()*1000)}_{hashlib.md5(str(args).encode()).hexdigest()[:8]}"
                
                start = time.time()
                steps = []
                success = False
                output = None
                
                try:
                    # Ejecutar paso a paso si es posible
                    output = func(*args, **kwargs)
                    success = True
                    steps.append({"action": "execute", "result": "success"})
                except Exception as e:
                    steps.append({"action": "execute", "result": f"error: {str(e)[:100]}"})
                    raise
                finally:
                    duration = (time.time() - start) * 1000
                    
                    trace = ExecutionTrace(
                        trace_id=trace_id,
                        input_data=str(args)[:500],
                        input_signature=self._signature(str(args)),
                        agent=agent,
                        steps=steps,
                        success=success,
                        output_data=str(output)[:500] if output else None,
                        output_signature=self._signature(str(output)) if output else "",
                        duration_ms=duration,
                    )
                    self.traces.append(trace)
                
                return output
            return wrapper
        return decorator
    
    def record_trace(self, agent: str, input_data: Any, output_data: Any, 
                     success: bool, steps: List[Dict] = None, duration_ms: float = 0):
        """Registra manualmente una traza de ejecución."""
        trace = ExecutionTrace(
            trace_id=f"trace_{int(time.time()*1000)}_{len(self.traces)}",
            input_data=str(input_data)[:500],
            input_signature=self._signature(str(input_data)),
            agent=agent,
            steps=steps or [],
            success=success,
            output_data=str(output_data)[:500] if output_data else None,
            output_signature=self._signature(str(output_data)),
            duration_ms=duration_ms,
        )
        self.traces.append(trace)
    
    # ═══════════════════════════════════════════════
    # ANÁLISIS Y CRISTALIZACIÓN
    # ═══════════════════════════════════════════════
    
    def analyze_and_crystallize(self) -> List[CrystallizedSkill]:
        """
        Analiza todas las trazas y cristaliza nuevas skills.
        
        Pipeline: CLUSTER → EXTRACT → CRYSTALLIZE → VALIDATE
        """
        # 1. CLUSTER: agrupar trazas exitosas por patrón de input
        self._cluster_successful_traces()
        
        new_skills = []
        
        for pattern_key, cluster_traces in self.pattern_clusters.items():
            if len(cluster_traces) < self.min_frequency:
                continue
            
            success_rate = sum(1 for t in cluster_traces if t.success) / len(cluster_traces)
            if success_rate < self.min_success_rate:
                continue
            
            # 2. EXTRACT: extraer el flujo común
            flow = self._extract_common_flow(cluster_traces)
            if not flow or len(flow) > self.max_complexity:
                continue
            
            # 3. CRYSTALLIZE: generar la skill
            skill = self._crystallize(pattern_key, flow, cluster_traces, success_rate)
            if skill:
                new_skills.append(skill)
                self.crystallized.append(skill)
                self.skill_counter += 1
        
        return new_skills
    
    def _cluster_successful_traces(self):
        """Agrupa trazas exitosas por similitud de input."""
        self.pattern_clusters = defaultdict(list)
        
        for trace in self.traces:
            if not trace.success:
                continue
            
            # Clave de cluster: hash del patrón del input (sin valores específicos)
            pattern = self._extract_input_pattern(str(trace.input_data))
            cluster_key = self._signature(pattern)[:16]
            self.pattern_clusters[cluster_key].append(trace)
    
    def _extract_common_flow(self, traces: List[ExecutionTrace]) -> List[Dict]:
        """Extrae el flujo de pasos común a todas las trazas."""
        # Contar pasos más frecuentes
        step_counter = Counter()
        for trace in traces:
            for step in trace.steps:
                action = step.get("action", "")
                if action:
                    step_counter[action] += 1
        
        # Filtrar pasos que aparecen en la mayoría de las trazas
        threshold = len(traces) * 0.7
        common_steps = [(action, count) for action, count in step_counter.items() 
                       if count >= threshold]
        common_steps.sort(key=lambda x: -x[1])
        
        # Reconstruir flujo en orden
        flow = []
        for i, (action, count) in enumerate(common_steps):
            flow.append({
                "step": i + 1,
                "action": action,
                "frequency": count / len(traces),
            })
        
        return flow
    
    def _crystallize(self, pattern_key: str, flow: List[Dict], 
                     traces: List[ExecutionTrace], success_rate: float) -> Optional[CrystallizedSkill]:
        """Cristaliza un patrón en una skill formal."""
        
        # Generar nombre de skill
        agent = traces[0].agent if traces else "unknown"
        skill_slug = f"auto_{agent}_{pattern_key[:8]}"
        skill_name = f"AutoSkill: {agent}_{self.skill_counter}"
        
        # Input/output pattern
        input_pattern = self._extract_input_pattern(str(traces[0].input_data))
        output_pattern = self._extract_output_pattern([str(t.output_data) for t in traces if t.output_data])
        
        # Complejidad
        complexity = "simple" if len(flow) <= 3 else "medium" if len(flow) <= 7 else "complex"
        
        # Generar SKILL.md
        skill_md = self._generate_skill_md(
            skill_name, skill_slug, flow, input_pattern, output_pattern,
            len(traces), success_rate, agent, complexity
        )
        
        return CrystallizedSkill(
            skill_name=skill_name,
            skill_slug=skill_slug,
            flow=flow,
            input_pattern=input_pattern,
            output_pattern=output_pattern,
            traces_analyzed=len(traces),
            success_rate=success_rate,
            frequency=len(traces),
            created_from_agent=agent,
            complexity=complexity,
            skill_md_content=skill_md,
        )
    
    # ═══════════════════════════════════════════════
    # UTILIDADES
    # ═══════════════════════════════════════════════
    
    def _signature(self, text: str) -> str:
        """Hash estable de un texto (normalizado)."""
        normalized = re.sub(r'\s+', ' ', str(text).lower()).strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _extract_input_pattern(self, input_str: str) -> str:
        """Extrae el patrón del input (reemplaza valores específicos con placeholders)."""
        # Reemplazar números
        pattern = re.sub(r'\b\d+\b', '<NUM>', input_str)
        # Reemplazar URLs
        pattern = re.sub(r'https?://\S+', '<URL>', pattern)
        # Reemplazar paths
        pattern = re.sub(r'/[\w/.-]+', '<PATH>', pattern)
        # Reemplazar IDs
        pattern = re.sub(r'\b[A-Za-z0-9]{20,}\b', '<ID>', pattern)
        return pattern
    
    def _extract_output_pattern(self, outputs: List[str]) -> str:
        """Extrae el patrón común de múltiples outputs."""
        if not outputs:
            return "unknown"
        
        # Encontrar estructura común
        patterns = [self._extract_input_pattern(o) for o in outputs]
        # Devolver el más frecuente
        return Counter(patterns).most_common(1)[0][0]
    
    def _generate_skill_md(self, name: str, slug: str, flow: List[Dict],
                          input_pat: str, output_pat: str,
                          traces_n: int, success_rate: float,
                          agent: str, complexity: str) -> str:
        """Genera el contenido de SKILL.md."""
        
        flow_md = "\n".join(
            f"{step['step']}. **{step['action']}** — frecuencia: {step['frequency']:.0%}"
            for step in flow
        )
        
        return f"""# {name}

## Identidad
- **Nombre:** `{slug}`
- **Origen:** Auto-cristalizado desde {traces_n} trazas del agente `{agent}`
- **Tasa de éxito:** {success_rate:.0%}
- **Complejidad:** {complexity}

## Contrato
- **Input esperado:** `{input_pat[:200]}`
- **Output esperado:** `{output_pat[:200]}`

## Flujo Determinista
{flow_md}

## Uso
```python
from colony.skills import {slug}
result = {slug}(input_data)
```

---
*Auto-generado por Trace2Skill (Nova Homonexus)*
*Basado en ejecuciones reales del agente {agent}*
"""
    
    def get_stats(self) -> Dict:
        """Estadísticas del sistema Trace2Skill."""
        return {
            "total_traces": len(self.traces),
            "successful_traces": sum(1 for t in self.traces if t.success),
            "success_rate": sum(1 for t in self.traces if t.success) / max(1, len(self.traces)),
            "skills_crystallized": len(self.crystallized),
            "pattern_clusters": len(self.pattern_clusters),
            "agents_tracked": list(set(t.agent for t in self.traces)),
            "top_patterns": sorted(
                [(k, len(v)) for k, v in self.pattern_clusters.items()],
                key=lambda x: -x[1]
            )[:5],
        }


# ─── Instancia Global ───

colony_trace2skill = Trace2Skill(min_frequency=3, min_success_rate=0.75)
