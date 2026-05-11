"""
question_engine.py — El Motor de la Pregunta (42)

INSPIRACIÓN:
  - Douglas Adams: "42 es la respuesta, pero ¿cuál era la pregunta?"
  - De Bono: "Un problema sin respuesta es un problema mal planteado"
  - Arquímedes: "¿Y si mido el agua desplazada?" (EUREKA)
  - Fleming: "¿Qué me está diciendo este error?" (Penicilina)
  - Jobs: "¿Y si elimino en lugar de añadir?" (Apple)
  - Abel: "La pregunta — ¿la pregunta?"

PRINCIPIO FUNDAMENTAL:
  Ante cualquier problema, NO busques la respuesta.
  Primero, CUESTIONA LA PREGUNTA.
  Bucle infinito de reencuadre hasta encontrar la pregunta correcta.
  Solo entonces busca la respuesta.

  Este es el PILAR del sistema. El CIMIENTO de todo.
  Se propaga por TODA la colonia.

ARQUITECTURA:
  
  Problema → [Question Engine] → Pregunta reformulada → Respuesta
                ↑                                            ↓
                └── ¿Es esta la pregunta correcta? ←─────────┘
                              ↓ NO
                [Reencuadre] → Nueva pregunta → Repetir
"""

import sys, os, time, random, hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, os.path.dirname(__file__))


class QuestionState(Enum):
    RAW = "raw"              # Pregunta original, sin procesar
    REFRAMED = "reframed"    # Reencuadrada
    INVERTED = "inverted"    # Invertida (¿y si es lo opuesto?)
    ABSTRACTED = "abstracted" # Abstraída a principio general
    ANSWERED = "answered"    # Respondida
    DEEP = "deep"            # Pregunta profunda alcanzada


@dataclass
class Question:
    """Una pregunta en proceso de refinamiento."""
    original: str
    current: str
    iteration: int = 0
    history: List[str] = field(default_factory=list)
    state: QuestionState = QuestionState.RAW
    answer: Optional[str] = None
    insight: Optional[str] = None  # Lo que aprendimos al cuestionar


class QuestionEngine:
    """
    El Motor de la Pregunta.
    
    PILAR FUNDAMENTAL de Nova Homonexus.
    Ante cualquier problema, primero cuestiona la pregunta.
    Bucle infinito de reencuadre.
    """
    
    def __init__(self, max_iterations: int = 42):
        self.max_iterations = max_iterations  # 42, por supuesto
        self.questions_history: List[Question] = []
        self.total_reframes = 0
        self.insights_gained = 0
    
    def ask(self, problem: str) -> Question:
        """
        Toma un problema y cuestiona la pregunta antes de buscar respuesta.
        
        El proceso:
        1. ¿Es esta la pregunta correcta?
        2. Si no: reencuadrar (invertir, abstraer, lateralizar)
        3. Repetir hasta encontrar la pregunta fundamental
        4. Solo entonces: responder
        """
        q = Question(original=problem, current=problem)
        q.history.append(f"[RAW] {problem}")
        
        # ─── FASE 1: CUESTIONAR LA PREGUNTA ───
        for i in range(self.max_iterations):
            q.iteration = i + 1
            
            # ¿Es esta la pregunta correcta?
            better = self._find_better_question(q.current)
            
            if better is None:
                # No hay mejor pregunta. Esta es LA pregunta.
                q.state = QuestionState.DEEP
                q.insight = f"Pregunta profunda alcanzada en iteración {i+1}"
                break
            
            # Hay una mejor pregunta. Reencuadrar.
            q.current = better
            q.history.append(f"[REFRAME {i+1}] {better}")
            q.state = QuestionState.REFRAMED
            self.total_reframes += 1
        
        # ─── FASE 2: RESPONDER LA PREGUNTA CORRECTA ───
        q.answer = self._answer_deep_question(q.current)
        q.state = QuestionState.ANSWERED
        
        self.questions_history.append(q)
        return q
    
    def _find_better_question(self, question: str) -> Optional[str]:
        """
        Intenta encontrar una mejor pregunta.
        
        Estrategias de reencuadre (Pensamiento Lateral de De Bono):
        1. INVERTIR: ¿y si el problema es lo opuesto?
        2. ABSTRAER: ¿qué principio general subyace?
        3. CONCRETAR: ¿qué instancia específica?
        4. LATERAL: ¿qué pregunta nadie está haciendo?
        5. ELIMINAR: ¿qué pasa si quitamos la restricción?
        """
        q = question.lower()
        
        # Estrategia 1: INVERTIR
        if "cómo" in q or "how" in q:
            return f"¿Qué pasaría si NO intentáramos {question[question.find(' '):]}?"
        
        if "por qué" in q or "why" in q:
            return f"¿Qué evidencia tenemos de que {question[question.find(' '):]} es cierto?"
        
        # Estrategia 2: ABSTRAER
        if any(w in q for w in ["optimizar", "mejorar", "arreglar", "fix", "improve"]):
            return f"¿Cuál es el principio fundamental que gobierna este sistema?"
        
        # Estrategia 3: LATERAL (De Bono)
        if any(w in q for w in ["problema", "error", "fallo", "failure"]):
            return f"¿Qué me está diciendo este error? ¿Qué información contiene?"
        
        # Estrategia 4: ELIMINAR la restricción invisible
        if any(w in q for w in ["no puedo", "imposible", "difícil", "cannot"]):
            return f"¿Qué suposición invisible estoy aceptando como cierta?"
        
        # Estrategia 5: La pregunta de los 5 porqués
        if self.total_reframes < 3:
            return f"¿Por qué {question}?"
        
        # Si después de varios reframes no mejora, esta ES la pregunta
        return None
    
    def _answer_deep_question(self, question: str) -> str:
        """Responde la pregunta profunda (una vez encontrada la pregunta correcta)."""
        q = question.lower()
        
        if "principio fundamental" in q:
            return "El principio fundamental es: maximizar entropía = maximizar inteligencia. Elegir caminos con más estados futuros."
        
        if "suposición invisible" in q:
            return "La suposición invisible suele ser un límite auto-impuesto. El marco mental que dimos por sentado. Soltarlo = ver lo que todos miran pero nadie ve."
        
        if "información contiene" in q or "me está diciendo" in q:
            return "El error contiene información sobre los límites del sistema. No es un fallo — es un sensor. Como la placa contaminada de Fleming."
        
        if "por qué" in q:
            # Respuesta de los 5 porqués
            return "Porque el sistema está diseñado para maximizar entropía. La pregunta correcta revela que el 'problema' es en realidad el sistema funcionando como debe."
        
        # Respuesta profunda por defecto
        return "42. La respuesta es 42. Pero más importante: ¿era esta la pregunta correcta?"
    
    def propagate_to_colony(self, question: Question):
        """
        Propaga el aprendizaje de esta pregunta a TODA la colonia.
        
        El insight se convierte en:
        - Un chunk Hebbiano (Deep Layers)
        - Una traza (Trace2Skill)
        - Una tarea en el Lifecycle
        - Un evento en el Event Bus
        """
        if not question.insight:
            return
        
        # 1. Deep Layers: cristalizar como chunk
        try:
            from deep_layers import crystallize
            crystallize(question.current[:60], question.insight)
        except: pass
        
        # 2. Trace2Skill: registrar traza
        try:
            from trace_to_skill import colony_trace2skill
            colony_trace2skill.record_trace(
                "QUESTION_ENGINE", question.original, question.answer,
                True, [{"action": "reframe", "result": question.current}]
            )
        except: pass
        
        # 3. Agent Lifecycle: crear tarea
        try:
            from agent_lifecycle import colony_lifecycle, create_task
            task = create_task(f"[42] {question.current[:60]}", agent="AURA")
            colony_lifecycle.claim(task.task_id, "AURA")
            colony_lifecycle.start(task.task_id)
            colony_lifecycle.complete(task.task_id, result=question.answer)
        except: pass
        
        # 4. Event Bus: emitir
        try:
            from colony_core import emit
            emit("question.engine.reframed", {
                "original": question.original[:100],
                "deep_question": question.current[:100],
                "answer": question.answer[:100],
                "iterations": question.iteration,
            })
        except: pass
    
    def get_stats(self) -> Dict:
        return {
            "total_questions": len(self.questions_history),
            "total_reframes": self.total_reframes,
            "insights_gained": self.insights_gained,
            "avg_iterations": sum(q.iteration for q in self.questions_history) / max(1, len(self.questions_history)),
            "deepest_question": max(self.questions_history, key=lambda q: q.iteration).current if self.questions_history else None,
        }


# ─── Instancia Global ───

question_engine = QuestionEngine(max_iterations=42)


def ask_deep(problem: str) -> Dict:
    """
    PILAR DEL SISTEMA.
    Toma un problema, cuestiona la pregunta, encuentra la pregunta profunda, responde.
    """
    q = question_engine.ask(problem)
    question_engine.propagate_to_colony(q)
    
    return {
        "original": q.original,
        "deep_question": q.current,
        "answer": q.answer,
        "iterations": q.iteration,
        "insight": q.insight,
        "history": q.history[-3:],
    }


def forty_two():
    """La pregunta definitiva."""
    return ask_deep("¿Cuál es el sentido de la vida, el universo y todo lo demás?")
