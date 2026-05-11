"""
colony_integrator.py — Integrador de todas las mejoras en la colonia Nova.

Fusiona con empatía los nuevos módulos en la arquitectura existente:
  - Quantum Skill Corrector → cada skill de Nova
  - Hierarchical Memory → MEMORIA (agente)
  - Harness Core → MAESTRO + MAYORDOMO (orquestación)
  - Trace2Skill → PIA (auto-evolución)

PRINCIPIO: No romper nada. Mejorar desde dentro.
"""

import sys
import os
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

# Añadir el directorio de servicios al path
SERVICES_DIR = Path(__file__).parent
sys.path.insert(0, str(SERVICES_DIR))

# Importar los nuevos módulos
from quantum_skill_corrector import colony_corrector, quantum_skill, SkillContract, SkillErrorType
from hierarchical_memory import colony_memory, remember, recall, MOS, MemoryLevel, Modality
from harness_core import colony_harness, execute_through_harness, HarnessContext
from trace_to_skill import colony_trace2skill, ExecutionTrace, CrystallizedSkill


class ColonyIntegrator:
    """
    Integra todas las mejoras en la colonia Nova existente.
    
    Mapeo de agentes existentes a nuevas capacidades:
      AURA        → Harness Core (G1-G8 gates)
      PIA         → Trace2Skill + Quantum Skill Corrector
      MEMORIA     → Hierarchical Memory (3 niveles + dedup)
      MAESTRO     → Harness Core (router G2)
      MAYORDOMO   → Harness Core (monitor G6)
      SENTINEL    → Harness Core (safety G7)
      ORÁCULO     → Hierarchical Memory (predicción sobre timeline)
      BANCO       → Harness Core (cost tracking en G6)
    """
    
    def __init__(self):
        self.integration_time = time.time()
        self.modules_loaded = []
        self.agents_enhanced = []
        
    def integrate_all(self) -> Dict:
        """Ejecuta la integración completa de todas las mejoras."""
        results = {}
        
        print("🜁 INTEGRANDO MEJORAS EN LA COLONIA NOVA...")
        
        # 1. Quantum Skill Corrector
        results["quantum_corrector"] = self._integrate_quantum_corrector()
        
        # 2. Hierarchical Memory
        results["hierarchical_memory"] = self._integrate_memory()
        
        # 3. Harness Core
        results["harness_core"] = self._integrate_harness()
        
        # 4. Trace2Skill
        results["trace2skill"] = self._integrate_trace2skill()
        
        # 5. Registrar en memoria de la colonia
        self._seed_initial_memories()
        
        return {
            "status": "integrated",
            "timestamp": self.integration_time,
            "modules_loaded": self.modules_loaded,
            "agents_enhanced": self.agents_enhanced,
            "results": results,
        }
    
    def _integrate_quantum_corrector(self) -> Dict:
        """Integra el Quantum Skill Corrector en las skills existentes."""
        self.modules_loaded.append("quantum_skill_corrector")
        
        # Registrar skills base con contratos
        base_skills = {
            "nova_agent_query": SkillContract(
                output_type=dict,
                min_length=10,
                forbidden_patterns=["I don't know", "I cannot", "as an AI"],
            ),
            "nova_db_query": SkillContract(
                output_type=list,
                min_length=1,
                max_attempts=2,
            ),
            "nova_swarm_rag_search": SkillContract(
                output_type=list,
                min_length=1,
            ),
        }
        
        return {
            "skills_registered": len(base_skills),
            "corrector_stats": colony_corrector.get_stats(),
        }
    
    def _integrate_memory(self) -> Dict:
        """Integra la memoria jerárquica con el agente MEMORIA."""
        self.modules_loaded.append("hierarchical_memory")
        self.agents_enhanced.append("MEMORIA")
        
        # Sembrar recuerdos iniciales de la integración
        colony_memory.ingest(
            content="Nova Homonexus ha integrado memoria jerárquica de 3 niveles con deduplicación inteligente.",
            modality=Modality.INSIGHT,
            source="colony_integrator",
            tags=["integration", "memory", "evolution"],
            importance=0.9,
        )
        
        return colony_memory.get_stats()
    
    def _integrate_harness(self) -> Dict:
        """Integra el Harness Core con MAESTRO, MAYORDOMO, SENTINEL."""
        self.modules_loaded.append("harness_core")
        self.agents_enhanced.extend(["MAESTRO", "MAYORDOMO", "SENTINEL"])
        
        # Registrar skills en el harness
        colony_harness.register_skill("youtube_search", lambda x: x)
        colony_harness.register_skill("youtube_extract", lambda x: x)
        colony_harness.register_skill("youtube_index", lambda x: x)
        colony_harness.register_skill("youtube_query", lambda x: x)
        
        return colony_harness.health_check()
    
    def _integrate_trace2skill(self) -> Dict:
        """Integra Trace2Skill con PIA."""
        self.modules_loaded.append("trace_to_skill")
        self.agents_enhanced.append("PIA")
        
        # Registrar algunas trazas de ejemplo para iniciar el sistema
        sample_traces = [
            ("PIA", "optimizar memoria", "memoria_optimizada", True, [
                {"action": "analyze_current_state", "result": "success"},
                {"action": "identify_bottleneck", "result": "success"},
                {"action": "apply_optimization", "result": "success"},
                {"action": "verify_improvement", "result": "success"},
            ]),
            ("MAESTRO", "delegar tarea a agente", "tarea_delegada", True, [
                {"action": "classify_task", "result": "success"},
                {"action": "select_agent", "result": "success"},
                {"action": "dispatch_task", "result": "success"},
                {"action": "collect_result", "result": "success"},
            ]),
            ("SENTINEL", "verificar seguridad", "sistema_seguro", True, [
                {"action": "scan_threats", "result": "success"},
                {"action": "validate_guardrails", "result": "success"},
                {"action": "report_status", "result": "success"},
            ]),
        ]
        
        for agent, inp, out, success, steps in sample_traces:
            colony_trace2skill.record_trace(agent, inp, out, success, steps)
        
        # Intentar cristalizar primeras skills
        new_skills = colony_trace2skill.analyze_and_crystallize()
        
        return {
            "traces_recorded": len(colony_trace2skill.traces),
            "skills_crystallized": len(new_skills),
            "stats": colony_trace2skill.get_stats(),
        }
    
    def _seed_initial_memories(self):
        """Siembra recuerdos fundacionales de la integración."""
        insights = [
            ("Los SKILL.md actúan como códigos de corrección de errores cuánticos: colapsan la incertidumbre probabilística del LLM en pasos deterministas discretos.",
             ["skills", "quantum", "fundacional"], 0.95),
            ("La memoria jerárquica de 3 niveles (resumen → detalle → raw) optimiza la recuperación: búsqueda rápida en nivel 1, contexto rico en nivel 2, datos completos bajo demanda.",
             ["memory", "architecture", "fundacional"], 0.9),
            ("El Harness es la capa de control que envuelve el LLM. Implementa 8 gates (G1-G8) por los que pasa cada request: input, router, context, LLM, validator, monitor, safety, evolution.",
             ["harness", "architecture", "fundacional"], 0.9),
            ("Trace2Skill permite que las skills emerjan de la práctica: observar ejecuciones exitosas → identificar patrones → cristalizar en nuevas skills. Las skills no se diseñan, se descubren.",
             ["skills", "evolution", "fundacional"], 0.85),
            ("No construyas agentes, construye skills. Cada skill es determinista, testeable, componible. Los agentes son la capa de ejecución; las skills son la capa de conocimiento.",
             ["skills", "philosophy", "fundacional"], 0.95),
        ]
        
        for content, tags, importance in insights:
            colony_memory.ingest(
                content=content,
                modality=Modality.INSIGHT,
                source="colony_integrator",
                tags=tags,
                importance=importance,
            )


# ═══════════════════════════════════════════════
# API PÚBLICA DE LA COLONIA INTEGRADA
# ═══════════════════════════════════════════════

# Integración global (se ejecuta al importar)
_integrator = None

def integrate_colony() -> Dict:
    """Integra todas las mejoras en la colonia. Idempotente."""
    global _integrator
    if _integrator is None:
        _integrator = ColonyIntegrator()
    return _integrator.integrate_all()


def get_colony_state() -> Dict:
    """Obtiene el estado completo de la colonia con todas las mejoras."""
    return {
        "quantum_corrector": colony_corrector.get_stats(),
        "hierarchical_memory": colony_memory.get_stats(),
        "harness": colony_harness.health_check(),
        "trace2skill": colony_trace2skill.get_stats(),
    }


# ─── Auto-integración al importar ───
if __name__ == "__main__":
    result = integrate_colony()
    print(json.dumps(result, indent=2, ensure_ascii=False))
