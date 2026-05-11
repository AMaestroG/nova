"""
quantum_skill_corrector.py — Sistema de Corrección de Errores Cuánticos para Skills

INSPIRACIÓN: @code4AI "Are SKILL.md files the Quantum Error Codes of Industrial AI?"
+ @aiDotEngineer "Don't Build Agents, Build Skills Instead" (Anthropic)

CONCEPTO: Así como los errores cuánticos continuos colapsan en operadores Pauli discretos
(X=bit flip, Z=phase flip, Y=ambos), los outputs probabilísticos del LLM colapsan en 
resultados deterministas discretos cuando pasan por skills bien definidos.

Cada skill actúa como un "operador de medición" que:
  1. COLAPSA la incertidumbre del LLM → resultado determinista
  2. DETECTA desviaciones (errores de formato, alucinaciones)
  3. CORRIGE automáticamente con reintentos variados
  4. VERIFICA que el output cumple el contrato

ARQUITECTURA:
  Input → [Pre-condición] → LLM Call → [Medición] → [Corrección] → [Verificación] → Output
                                  ↑_______________| (reintento con variación si falla)
"""

import functools
import json
import time
import traceback
import hashlib
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from dataclasses import dataclass, field
from enum import Enum


# ─── Tipos de Error (inspirados en Pauli operators) ───

class SkillErrorType(Enum):
    """Tipos de error que un skill puede detectar y corregir."""
    BIT_FLIP = "bit_flip"        # X: formato incorrecto (JSON malformado, tipo equivocado)
    PHASE_FLIP = "phase_flip"    # Z: alucinación, información inventada
    COMBINED = "combined"        # Y: ambos errores simultáneos
    TIMEOUT = "timeout"          # T: timeout o recurso no disponible
    EMPTY = "empty"              # E: output vacío


@dataclass
class SkillMeasurement:
    """Resultado de una "medición" sobre el output del LLM."""
    success: bool
    error_type: Optional[SkillErrorType] = None
    error_detail: str = ""
    corrected_output: Any = None
    attempts: int = 1
    confidence: float = 1.0
    trace: List[str] = field(default_factory=list)


@dataclass
class SkillContract:
    """Define el contrato que un skill debe cumplir (pre/post condiciones)."""
    input_schema: Optional[Dict] = None       # JSON Schema esperado del input
    output_schema: Optional[Dict] = None      # JSON Schema esperado del output
    output_type: Optional[Type] = None        # Tipo Python esperado
    min_length: int = 1                       # Longitud mínima del output
    max_length: Optional[int] = None          # Longitud máxima
    forbidden_patterns: List[str] = field(default_factory=list)  # Patrones que indican error
    required_patterns: List[str] = field(default_factory=list)   # Patrones que deben aparecer
    max_attempts: int = 3                     # Máximo de reintentos
    correction_strategies: List[str] = field(default_factory=lambda: [
        "retry_with_temperature",  # Subir temperatura
        "retry_with_explicit",     # Pedir más explícitamente
        "retry_with_schema",       # Mostrar schema esperado
        "retry_with_example",      # Dar ejemplo
    ])


# ─── Corrector Principal ───

class QuantumSkillCorrector:
    """
    Envuelve cualquier función de skill con corrección de errores cuántica.
    
    Uso:
        corrector = QuantumSkillCorrector()
        
        @corrector.skill(contract=SkillContract(
            output_type=dict,
            required_patterns=["result"],
            forbidden_patterns=["I don't know", "as an AI"]
        ))
        def my_skill(input_data: str) -> dict:
            ...
    """
    
    def __init__(self, default_max_attempts: int = 3):
        self.default_max_attempts = default_max_attempts
        self.measurements_log: List[SkillMeasurement] = []
    
    def skill(self, contract: Optional[SkillContract] = None, max_attempts: int = None):
        """Decorador principal para skills."""
        if contract is None:
            contract = SkillContract()
        if max_attempts is not None:
            contract.max_attempts = max_attempts
        
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                return self._execute_with_correction(func, contract, *args, **kwargs)
            return wrapper
        return decorator
    
    def _execute_with_correction(self, func: Callable, contract: SkillContract, *args, **kwargs) -> Any:
        """Ejecuta un skill con corrección de errores."""
        trace = []
        
        for attempt in range(contract.max_attempts):
            try:
                # 1. Ejecutar el skill
                trace.append(f"Attempt {attempt+1}/{contract.max_attempts}")
                start_time = time.time()
                output = func(*args, **kwargs)
                elapsed = time.time() - start_time
                trace.append(f"  Execution: {elapsed:.2f}s")
                
                # 2. MEDIR el output (colapsar incertidumbre → detección de error)
                measurement = self._measure(output, contract)
                measurement.attempts = attempt + 1
                measurement.trace = trace
                
                if measurement.success:
                    self.measurements_log.append(measurement)
                    return measurement.corrected_output if measurement.corrected_output is not None else output
                
                # 3. CORREGIR si falló
                trace.append(f"  Error: {measurement.error_type.value} - {measurement.error_detail}")
                correction = self._correct(output, contract, measurement, attempt)
                
                if correction is not None:
                    trace.append(f"  Corrected in-measurement")
                    measurement.corrected_output = correction
                    measurement.success = True
                    self.measurements_log.append(measurement)
                    return correction
                
                # 4. Si no se pudo corregir, preparar estrategia para reintento
                strategy = contract.correction_strategies[min(attempt, len(contract.correction_strategies)-1)]
                trace.append(f"  Strategy: {strategy}")
                
                # Modificar kwargs para el reintento según estrategia
                kwargs = self._apply_strategy(kwargs, strategy, contract, measurement)
                
            except Exception as e:
                trace.append(f"  Exception: {type(e).__name__}: {str(e)[:100]}")
                if attempt == contract.max_attempts - 1:
                    measurement = SkillMeasurement(
                        success=False,
                        error_type=SkillErrorType.TIMEOUT,
                        error_detail=str(e),
                        attempts=attempt + 1,
                        trace=trace,
                    )
                    self.measurements_log.append(measurement)
                    raise
        
        # Si llegamos aquí, fallaron todos los intentos
        measurement = SkillMeasurement(
            success=False,
            error_type=SkillErrorType.COMBINED,
            error_detail=f"Failed after {contract.max_attempts} attempts",
            attempts=contract.max_attempts,
            trace=trace,
        )
        self.measurements_log.append(measurement)
        raise SkillExecutionError(measurement)
    
    def _measure(self, output: Any, contract: SkillContract) -> SkillMeasurement:
        """
        MEDIR el output — como colapsar la función de onda cuántica.
        Detecta errores de tipo BIT_FLIP (formato), PHASE_FLIP (contenido), etc.
        """
        # Verificar output no vacío
        if output is None or (isinstance(output, (str, list, dict)) and len(output) == 0):
            return SkillMeasurement(
                success=False,
                error_type=SkillErrorType.EMPTY,
                error_detail="Output is empty"
            )
        
        # Verificar tipo (BIT_FLIP detection)
        if contract.output_type is not None:
            if not isinstance(output, contract.output_type):
                # Intentar corrección de tipo
                try:
                    if contract.output_type == dict and isinstance(output, str):
                        corrected = json.loads(output)
                        return SkillMeasurement(
                            success=False,
                            error_type=SkillErrorType.BIT_FLIP,
                            error_detail=f"Output is str, expected dict. Auto-corrected.",
                            corrected_output=corrected,
                            confidence=0.8
                        )
                    elif contract.output_type == str and isinstance(output, dict):
                        corrected = json.dumps(output)
                        return SkillMeasurement(
                            success=False,
                            error_type=SkillErrorType.BIT_FLIP,
                            error_detail=f"Output is dict, expected str. Auto-corrected.",
                            corrected_output=corrected,
                            confidence=0.9
                        )
                except:
                    pass
                
                return SkillMeasurement(
                    success=False,
                    error_type=SkillErrorType.BIT_FLIP,
                    error_detail=f"Expected {contract.output_type.__name__}, got {type(output).__name__}"
                )
        
        # Verificar longitud
        if isinstance(output, str):
            if len(output) < contract.min_length:
                return SkillMeasurement(
                    success=False,
                    error_type=SkillErrorType.EMPTY,
                    error_detail=f"Output too short: {len(output)} < {contract.min_length}"
                )
            if contract.max_length and len(output) > contract.max_length:
                return SkillMeasurement(
                    success=False,
                    error_type=SkillErrorType.BIT_FLIP,
                    error_detail=f"Output too long: {len(output)} > {contract.max_length}"
                )
        
        # Verificar patrones prohibidos (PHASE_FLIP detection - alucinaciones)
        if isinstance(output, str) and contract.forbidden_patterns:
            for pattern in contract.forbidden_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    return SkillMeasurement(
                        success=False,
                        error_type=SkillErrorType.PHASE_FLIP,
                        error_detail=f"Forbidden pattern detected: '{pattern}'"
                    )
        
        # Verificar patrones requeridos
        if isinstance(output, str) and contract.required_patterns:
            for pattern in contract.required_patterns:
                if not re.search(pattern, output, re.IGNORECASE):
                    return SkillMeasurement(
                        success=False,
                        error_type=SkillErrorType.BIT_FLIP,
                        error_detail=f"Required pattern missing: '{pattern}'"
                    )
        
        # Verificar JSON schema si existe
        if contract.output_schema and isinstance(output, dict):
            errors = self._validate_json_schema(output, contract.output_schema)
            if errors:
                return SkillMeasurement(
                    success=False,
                    error_type=SkillErrorType.BIT_FLIP,
                    error_detail=f"Schema validation failed: {errors[:3]}"
                )
        
        # ¡Éxito! Medición limpia
        return SkillMeasurement(success=True, confidence=0.95)
    
    def _correct(self, output: Any, contract: SkillContract, measurement: SkillMeasurement, attempt: int) -> Optional[Any]:
        """Intenta corregir automáticamente el output (sin re-ejecutar el LLM)."""
        
        # Corrección de JSON malformado
        if measurement.error_type == SkillErrorType.BIT_FLIP and isinstance(output, str):
            # Intentar extraer JSON de un texto más largo
            json_match = re.search(r'\{[^{}]*\}', output, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass
            
            # Intentar reparar JSON común (comillas simples, trailing commas)
            try:
                fixed = output.replace("'", '"')
                fixed = re.sub(r',\s*}', '}', fixed)
                fixed = re.sub(r',\s*]', ']', fixed)
                return json.loads(fixed)
            except:
                pass
        
        # Corrección de alucinaciones leves (quitar frases de rechazo)
        if measurement.error_type == SkillErrorType.PHASE_FLIP and isinstance(output, str):
            refusal_patterns = [
                r"I('?m| am) sorry.*?\.",
                r"As an AI.*?\.",
                r"I (can'?t|can not|don'?t have).*?\.",
                r"unfortunately.*?\.",
            ]
            cleaned = output
            for pat in refusal_patterns:
                cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)
            if cleaned != output and len(cleaned.strip()) > 50:
                return cleaned
        
        return None
    
    def _apply_strategy(self, kwargs: dict, strategy: str, contract: SkillContract, measurement: SkillMeasurement) -> dict:
        """Modifica los kwargs para el reintento según la estrategia."""
        new_kwargs = dict(kwargs)
        
        if strategy == "retry_with_temperature":
            new_kwargs['temperature'] = kwargs.get('temperature', 0.3) + 0.3
            new_kwargs['_correction_hint'] = f"Previous error: {measurement.error_detail}"
        
        elif strategy == "retry_with_explicit":
            new_kwargs['_correction_hint'] = (
                f"ERROR DETECTED: {measurement.error_type.value}. "
                f"Detail: {measurement.error_detail}. "
                f"Please provide a valid response."
            )
        
        elif strategy == "retry_with_schema":
            schema_hint = json.dumps(contract.output_schema, indent=2) if contract.output_schema else "valid JSON"
            new_kwargs['_correction_hint'] = (
                f"Your response must match this schema: {schema_hint}. "
                f"Previous attempt failed: {measurement.error_detail}"
            )
        
        elif strategy == "retry_with_example":
            new_kwargs['_correction_hint'] = (
                f"Example of valid output: {self._generate_example(contract)}. "
                f"Please follow this format exactly."
            )
        
        return new_kwargs
    
    def _validate_json_schema(self, data: dict, schema: dict) -> List[str]:
        """Validación simple de JSON Schema."""
        errors = []
        if 'required' in schema:
            for field in schema['required']:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        if 'properties' in schema:
            for field, spec in schema['properties'].items():
                if field in data:
                    expected_type = spec.get('type')
                    if expected_type == 'string' and not isinstance(data[field], str):
                        errors.append(f"Field {field}: expected string, got {type(data[field]).__name__}")
                    elif expected_type == 'number' and not isinstance(data[field], (int, float)):
                        errors.append(f"Field {field}: expected number")
                    elif expected_type == 'array' and not isinstance(data[field], list):
                        errors.append(f"Field {field}: expected array")
        return errors
    
    def _generate_example(self, contract: SkillContract) -> str:
        """Genera un ejemplo de output válido basado en el contrato."""
        if contract.output_schema:
            example = {}
            if 'properties' in contract.output_schema:
                for field, spec in contract.output_schema['properties'].items():
                    t = spec.get('type', 'string')
                    if t == 'string':
                        example[field] = f"example_{field}"
                    elif t == 'number':
                        example[field] = 42
                    elif t == 'array':
                        example[field] = ["item1", "item2"]
                    elif t == 'object':
                        example[field] = {"key": "value"}
            return json.dumps(example)
        return '{"result": "ok"}'
    
    def get_stats(self) -> Dict:
        """Estadísticas de correcciones."""
        total = len(self.measurements_log)
        if total == 0:
            return {"total": 0}
        
        success = sum(1 for m in self.measurements_log if m.success)
        corrections = sum(1 for m in self.measurements_log if m.corrected_output is not None)
        
        return {
            "total_executions": total,
            "success_rate": success / total,
            "corrections_applied": corrections,
            "avg_attempts": sum(m.attempts for m in self.measurements_log) / total,
            "error_distribution": {
                et.value: sum(1 for m in self.measurements_log if m.error_type == et)
                for et in SkillErrorType
            },
        }


class SkillExecutionError(Exception):
    """Excepción cuando un skill falla después de todos los reintentos."""
    def __init__(self, measurement: SkillMeasurement):
        self.measurement = measurement
        super().__init__(
            f"Skill failed after {measurement.attempts} attempts: "
            f"{measurement.error_type.value} - {measurement.error_detail}"
        )


# ─── Corrector Global de la Colonia ───

# Instancia única para toda la colonia
colony_corrector = QuantumSkillCorrector(default_max_attempts=3)


def quantum_skill(contract: SkillContract = None, **kwargs):
    """Decorador rápido para usar el corrector de la colonia."""
    return colony_corrector.skill(contract=contract, **kwargs)
