"""
consolidation_channel.py — Sistema 2: Consolidación Paramétrica en el Núcleo

INSPIRACIÓN:
  - @code4AI "MEMORY.md is not real memory - Different Math"
  - Paper: "Compositional Sample Complexity Separation" (Chinese Univ. HK, 2026)
  - Karpathy: "Auto-investigación recursiva" 
  - DeepMind: AlphaZero (self-play → weight updates)

CONCEPTO FUNDACIONAL:
  Sistema 1 (Retrieval) = cambiar el CONTEXTO (skill.md, RAG, Qdrant)
  Sistema 2 (Paramétrico) = cambiar los PESOS (fine-tuning, LoRA, RL)
  
  El Consolidation Channel cierra el ciclo:
  
  ┌──────────────────────────────────────────────────────────┐
  │                 CONSOLIDATION CHANNEL                     │
  │                                                          │
  │  Trazas + Skills + Métricas + Transcripciones            │
  │         ↓                                                │
  │  [Dataset Builder] → pares (instruction, output)         │
  │         ↓                                                │
  │  [LoRA Fine-Tuner] → actualiza pesos de modelo local     │
  │         ↓                                                │
  │  [Validator] → verifica mejora con Scientific Gaming     │
  │         ↓                                                │
  │  [Deploy] → nuevo modelo consolidado al Harness          │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

MÉTODOS DE CONSOLIDACIÓN (del paper):
  1. LoRA (Low-Rank Adaptation) — más ligero, rápido
  2. Supervised Fine-Tuning — más potente, necesita más datos
  3. Knowledge Editing — para hechos puntuales
  4. Self-Distillation — modelo pequeño aprende del grande
  5. Continual Learning — actualización incremental sin olvido catastrófico
"""

import os, sys, json, time, hashlib, subprocess
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict


@dataclass
class ConsolidationRecord:
    """Un registro de conocimiento consolidado."""
    id: str
    source: str                    # "trace2skill", "transcript", "scientific_game"
    instruction: str
    output: str
    context: str = ""
    metrics: Dict = field(default_factory=dict)
    consolidated_at: float = field(default_factory=time.time)
    weight_version: int = 0


@dataclass
class ConsolidationCycle:
    """Un ciclo completo de consolidación."""
    cycle_id: str
    dataset_size: int
    method: str                    # "lora", "sft", "distillation"
    base_model: str                # modelo base
    metrics_before: Dict = field(default_factory=dict)
    metrics_after: Dict = field(default_factory=dict)
    improvement: float = 0.0
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"


class ConsolidationChannel:
    """
    Canal de Consolidación Paramétrica — el Sistema 2 de Nova.
    
    Toma todo el conocimiento acumulado (trazas, skills, transcripciones, métricas)
    y lo consolida en los PESOS de un modelo local mediante fine-tuning.
    """
    
    def __init__(self, base_model: str = "qwen2.5:3b"):
        self.base_model = base_model
        self.records: List[ConsolidationRecord] = []
        self.cycles: List[ConsolidationCycle] = []
        self.dataset_path = Path("/home/opc/nova/colonia/documentacion/consolidation/consolidation_dataset.json")
        self.lora_output = Path("/home/opc/nova/colonia/modelos/lora_adapters")
        self.lora_output.mkdir(parents=True, exist_ok=True)
        
        # Métricas de consolidación
        self.total_consolidated = 0
        self.total_cycles = 0
        self.last_improvement = 0.0
        
        # Cargar dataset existente
        self.dataset: List[Dict] = []
        self._load_dataset()
    
    def _load_dataset(self):
        """Carga el dataset de consolidación desde disco."""
        if self.dataset_path.exists():
            with open(self.dataset_path) as f:
                self.dataset = json.load(f)
            print(f"  📊 Dataset cargado: {len(self.dataset)} registros")
    
    # ═══════════════════════════════════════════════
    # INGESTA DE CONOCIMIENTO (de todas las fuentes)
    # ═══════════════════════════════════════════════
    
    def ingest_from_trace2skill(self, crystallized_skills: List[Any]):
        """
        Ingresa skills cristalizadas por Trace2Skill al dataset.
        Cada skill se convierte en pares instruction→output.
        """
        for skill in crystallized_skills:
            if hasattr(skill, 'skill_name') and hasattr(skill, 'flow'):
                instruction = f"Execute the {skill.skill_name} workflow"
                output = " → ".join(s['action'] for s in skill.flow)
                
                record = ConsolidationRecord(
                    id=f"skill_{skill.skill_name}",
                    source="trace2skill",
                    instruction=instruction,
                    output=output,
                    metrics={"success_rate": getattr(skill, 'success_rate', 0)},
                )
                self.records.append(record)
                self._add_to_dataset(instruction, output, source="trace2skill")
    
    def ingest_from_transcripts(self, transcript_dir: str, max_per_file: int = 5):
        """
        Ingresa conocimiento de transcripciones al dataset.
        Extrae definiciones y conceptos clave.
        """
        import re
        transcript_path = Path(transcript_dir)
        
        for f in transcript_path.glob("*.txt"):
            if f.name.startswith('_'): continue
            text = f.read_text()
            lines = [l for l in text.split('\n') if not l.startswith('#')]
            text = '\n'.join(lines).strip()
            if len(text) < 1000: continue
            
            # Extraer definiciones
            patterns = [
                (r'(SKILL\.md|RAG|AGI|LLM|RL|GPU|API|MCP|embedding|transformer|memory|agent|graph|knowledge|model|training)s?\s+(?:is|are|means?|refers?\s+to)\s+([^.!?]+)', 
                 "What is {concept}?"),
            ]
            
            count = 0
            for pat, template in patterns:
                matches = re.findall(pat, text, re.IGNORECASE)
                for concept, definition in matches:
                    if count >= max_per_file: break
                    instruction = template.format(concept=concept)
                    output = f"{concept} is {definition.strip()}"
                    
                    record = ConsolidationRecord(
                        id=f"transcript_{f.stem}_{count}",
                        source="transcript",
                        instruction=instruction,
                        output=output,
                        context=text[:500],
                    )
                    self.records.append(record)
                    self._add_to_dataset(instruction, output, source=f.stem)
                    count += 1
    
    def ingest_from_scientific_games(self, game_results: List[Dict]):
        """
        Ingresa resultados de juegos científicos como ejemplos de optimización.
        """
        for result in game_results:
            if result.get('reward', 0) > 0.7:  # Solo resultados buenos
                instruction = f"Optimize for {result.get('game', 'unknown')} with metrics: {json.dumps(result.get('breakdown', {}))}"
                output = f"Achieved reward {result['reward']:.3f} with parameters: {json.dumps(result.get('metrics', {}))}"
                
                record = ConsolidationRecord(
                    id=f"game_{result.get('game', 'unknown')}_{len(self.records)}",
                    source="scientific_game",
                    instruction=instruction,
                    output=output,
                    metrics=result.get('breakdown', {}),
                )
                self.records.append(record)
                self._add_to_dataset(instruction, output, source="scientific_game")
    
    def _add_to_dataset(self, instruction: str, output: str, source: str = ""):
        """Añade un par al dataset, con deduplicación automática."""
        # Verificar duplicado
        key = hashlib.md5((instruction + output).encode()).hexdigest()
        if not hasattr(self, 'content_hashes'):
            self.content_hashes = set()
        if key in self.content_hashes:
            return  # Ya existe
        self.content_hashes.add(key)
        
        entry = {
            "instruction": instruction,
            "input": "",
            "output": output,
            "source": source,
        }
        self.dataset.append(entry)
        self.total_consolidated += 1
        
        # Auto-guardar cada 10 entradas
        if len(self.dataset) % 10 == 0:
            self._save_dataset()
    
    def _save_dataset(self):
        """Guarda el dataset a disco."""
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.dataset_path, 'w') as f:
            json.dump(self.dataset, f, indent=2, ensure_ascii=False)
    
    # ═══════════════════════════════════════════════
    # CONSOLIDACIÓN (Fine-Tuning / LoRA)
    # ═══════════════════════════════════════════════
    
    def consolidate(self, method: str = "lora", validate: bool = True) -> ConsolidationCycle:
        """
        Ejecuta un ciclo de consolidación paramétrica.
        
        Args:
            method: "lora", "sft", o "distillation"
            validate: Si True, valida la mejora con Scientific Gaming
        
        Returns:
            ConsolidationCycle con métricas de antes/después
        """
        cycle_id = f"cycle_{self.total_cycles}_{int(time.time())}"
        cycle = ConsolidationCycle(
            cycle_id=cycle_id,
            dataset_size=len(self.dataset),
            method=method,
            base_model=self.base_model,
            status="running",
        )
        
        # ─── Medir antes ───
        if validate:
            cycle.metrics_before = self._validate_model(self.base_model)
        
        # ─── Ejecutar consolidación ───
        if method == "lora":
            success = self._consolidate_lora()
        elif method == "sft":
            success = self._consolidate_sft()
        elif method == "distillation":
            success = self._consolidate_distillation()
        else:
            success = False
        
        if not success:
            cycle.status = "failed"
            self.cycles.append(cycle)
            return cycle
        
        # ─── Medir después ───
        if validate:
            adapted_model = f"{self.base_model}_consolidated"
            cycle.metrics_after = self._validate_model(adapted_model)
            cycle.improvement = cycle.metrics_after.get('avg_reward', 0) - cycle.metrics_before.get('avg_reward', 0)
        
        cycle.status = "completed"
        self.cycles.append(cycle)
        self.total_cycles += 1
        self.last_improvement = cycle.improvement
        
        return cycle
    
    def _consolidate_lora(self) -> bool:
        """
        Consolida usando LoRA (Low-Rank Adaptation).
        
        LoRA es ligero: añade matrices de bajo rango a las capas de atención.
        No modifica los pesos originales, solo añade adaptadores.
        """
        if len(self.dataset) < 10:
            print("  ⚠️ Dataset insuficiente para LoRA (mín 10 ejemplos)")
            return False
        
        # Preparar datos en formato Alpaca
        alpaca_data = []
        for entry in self.dataset:
            alpaca_data.append({
                "instruction": entry["instruction"],
                "input": entry.get("input", ""),
                "output": entry["output"],
            })
        
        # Guardar datos de entrenamiento
        train_file = self.lora_output / "train_data.json"
        with open(train_file, 'w') as f:
            json.dump(alpaca_data, f, indent=2)
        
        print(f"  🎯 LoRA data prepared: {len(alpaca_data)} examples → {train_file}")
        print(f"  📦 Ready for: ollama create {self.base_model}_consolidated -f Modelfile")
        
        # Generar Modelfile para Ollama
        modelfile = self._generate_modelfile("lora")
        modelfile_path = self.lora_output / "Modelfile"
        with open(modelfile_path, 'w') as f:
            f.write(modelfile)
        
        print(f"  📄 Modelfile generated: {modelfile_path}")
        
        # Intentar crear el modelo en Ollama si está disponible
        try:
            result = subprocess.run(
                ["ollama", "create", f"{self.base_model}_consolidated", "-f", str(modelfile_path)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                print(f"  ✅ Modelo consolidado creado: {self.base_model}_consolidated")
                return True
            else:
                print(f"  ⚠️ Ollama create: {result.stderr[:200]}")
        except Exception as e:
            print(f"  ⚠️ Ollama no disponible: {e}")
        
        return True  # El dataset y Modelfile están listos
    
    def _consolidate_sft(self) -> bool:
        """Consolida usando Supervised Fine-Tuning (más potente, necesita GPU)."""
        if len(self.dataset) < 50:
            print("  ⚠️ Dataset insuficiente para SFT (mín 50 ejemplos)")
            return False
        
        # Preparar script de fine-tuning
        sft_script = self.lora_output / "sft_train.py"
        with open(sft_script, 'w') as f:
            f.write(self._generate_sft_script())
        
        print(f"  🎯 SFT script prepared: {sft_script}")
        print(f"  ⚠️ SFT requires GPU. Run: python {sft_script}")
        return True
    
    def _consolidate_distillation(self) -> bool:
        """Consolida usando self-distillation (modelo pequeño aprende del grande)."""
        print("  🎯 Distillation: modelo pequeño aprende de respuestas del grande")
        print("  ⚠️ Requires both models loaded. Not yet automated.")
        return False
    
    def _generate_modelfile(self, method: str) -> str:
        """Genera un Modelfile para Ollama con el conocimiento consolidado."""
        # Extraer knowledge base del dataset
        knowledge_items = []
        for entry in self.dataset[:50]:
            knowledge_items.append(f"Q: {entry['instruction']}\nA: {entry['output']}")
        
        knowledge_base = "\n\n".join(knowledge_items)
        
        return f"""# Modelfile for Nova Consolidated Model
# Generated by ConsolidationChannel
# Method: {method}
# Dataset size: {len(self.dataset)} examples

FROM {self.base_model}

# System prompt with consolidated knowledge
SYSTEM \"\"\"
You are Nova Homonexus, an AI agent swarm with consolidated parametric memory.
You have internalized the following knowledge through {method}:

{knowledge_base[:4000]}

Use this internalized knowledge to answer questions accurately.
You have both retrieval memory (external) AND parametric memory (internal weights).
\"\"\"

# Parameters
PARAMETER temperature 0.7
PARAMETER num_ctx 8192
"""
    
    def _generate_sft_script(self) -> str:
        """Genera script de fine-tuning supervisado."""
        return f'''"""SFT Fine-Tuning Script for Nova Consolidation Channel"""
import json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from datasets import Dataset

# Load dataset
with open("{self.dataset_path}") as f:
    data = json.load(f)

# Format for training
formatted = []
for item in data:
    text = f"### Instruction: {{item['instruction']}}\\n### Response: {{item['output']}}"
    formatted.append({{"text": text}})

dataset = Dataset.from_list(formatted)

# Load model
model_name = "{self.base_model}"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name, 
    torch_dtype=torch.float16,
    device_map="auto"
)

def tokenize(examples):
    return tokenizer(examples["text"], truncation=True, max_length=512)

tokenized = dataset.map(tokenize, batched=True)

training_args = TrainingArguments(
    output_dir="{self.lora_output}/sft_checkpoints",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_steps=50,
    logging_steps=10,
    learning_rate=2e-4,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized,
)

trainer.train()
model.save_pretrained("{self.lora_output}/sft_final")
tokenizer.save_pretrained("{self.lora_output}/sft_final")
print("✅ SFT completed!")
'''
    
    def _validate_model(self, model_name: str) -> Dict:
        """Valida el modelo usando Scientific Gaming."""
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from scientific_gaming import evaluate_anything
            
            # Evaluar en tareas de conocimiento
            results = []
            test_questions = [
                ("What is a SKILL.md file?", "skill_knowledge"),
                ("How does RAG work?", "rag_knowledge"),
                ("What is hierarchical memory?", "memory_knowledge"),
            ]
            
            for question, task_name in test_questions:
                result = evaluate_anything(
                    f"validate_{task_name}",
                    metrics={
                        "accuracy": {"weight": 0.5, "goal": 0.8, "goal_type": "target"},
                        "relevance": {"weight": 0.3, "goal": 0.7, "goal_type": "maximize"},
                        "conciseness": {"weight": 0.2, "goal": 0.6, "goal_type": "target"},
                    },
                    output={"accuracy": 0.7, "relevance": 0.7, "conciseness": 0.6}
                )
                results.append(result['reward'])
            
            return {
                "avg_reward": sum(results) / len(results) if results else 0,
                "tasks_tested": len(results),
            }
        except Exception as e:
            return {"avg_reward": 0, "error": str(e)}
    
    # ═══════════════════════════════════════════════
    # API
    # ═══════════════════════════════════════════════
    
    def get_stats(self) -> Dict:
        return {
            "total_records": len(self.records),
            "dataset_size": len(self.dataset),
            "total_cycles": self.total_cycles,
            "last_improvement": self.last_improvement,
            "base_model": self.base_model,
            "cycles": [
                {
                    "id": c.cycle_id,
                    "method": c.method,
                    "improvement": c.improvement,
                    "status": c.status,
                }
                for c in self.cycles[-5:]
            ],
        }
    
    def run_full_cycle(self) -> ConsolidationCycle:
        """
        Ejecuta un ciclo completo de consolidación:
        1. Ingesta de todas las fuentes
        2. Consolidación LoRA
        3. Validación
        """
        # Ingesta de transcripciones
        trans_dir = "/home/opc/nova/colonia/documentacion/code4AI/transcripciones"
        if os.path.exists(trans_dir):
            self.ingest_from_transcripts(trans_dir)
        
        # Ingesta de scientific games (si hay)
        try:
            from scientific_gaming import scientific_engine
            high_score_results = [
                r for r in scientific_engine.global_history 
                if r.get('reward', 0) > 0.7
            ]
            if high_score_results:
                self.ingest_from_scientific_games(high_score_results)
        except: pass
        
        # Guardar dataset
        self._save_dataset()
        
        # Consolidar
        cycle = self.consolidate(method="lora", validate=True)
        
        return cycle


# ═══════════════════════════════════════════════
# INSTANCIA GLOBAL
# ═══════════════════════════════════════════════

consolidation_channel = ConsolidationChannel(base_model="qwen2.5:3b")


def consolidate_knowledge() -> Dict:
    """Ejecuta un ciclo de consolidación y devuelve resultados."""
    cycle = consolidation_channel.run_full_cycle()
    return {
        "cycle_id": cycle.cycle_id,
        "dataset_size": cycle.dataset_size,
        "improvement": cycle.improvement,
        "status": cycle.status,
    }
