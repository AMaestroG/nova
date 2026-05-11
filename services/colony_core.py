"""
colony_core.py — Persistencia y Propagación Unificada de la Colonia

SISTEMA CENTRAL que une TODOS los módulos:
  - ColonyStateManager: Persistencia unificada en archivo JSON
  - ColonyEventBus: Propagación pub/sub entre módulos
  - ColonyNucleus: Inicialización y orquestación central

PRINCIPIO: Un solo archivo de estado. Un solo bus de eventos.
Cada módulo publica cambios. Cada módulo reacciona a cambios de otros.
El estado sobrevive a reinicios. La colonia es UN organismo.
"""

import json
import os
import time
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path


# ═══════════════════════════════════════════════
# COLONY STATE MANAGER — Persistencia Unificada
# ═══════════════════════════════════════════════

class ColonyStateManager:
    """
    Gestor de estado unificado de la colonia.
    
    Un solo archivo JSON contiene el estado de TODOS los módulos.
    Cada módulo lee/escribe su namespace.
    Auto-save después de cada cambio.
    """
    
    def __init__(self, state_file: str = None):
        self.state_file = state_file or str(
            Path(__file__).parent / ".colony_state.json"
        )
        self.state: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.dirty = False
        self.save_count = 0
        self.load_count = 0
        
        # Cargar estado previo
        self.load()
    
    def load(self) -> Dict:
        """Carga el estado desde disco."""
        with self.lock:
            if os.path.exists(self.state_file):
                try:
                    with open(self.state_file) as f:
                        self.state = json.load(f)
                    self.load_count += 1
                except Exception:
                    self.state = {}
            else:
                self.state = {}
            
            # Asegurar namespaces base
            self.state.setdefault("_meta", {
                "created_at": time.time(),
                "version": 2,
                "modules": [],
            })
            
            return dict(self.state)
    
    def save(self, force: bool = False):
        """Guarda el estado a disco."""
        with self.lock:
            if not self.dirty and not force:
                return
            
            try:
                self.state["_meta"]["last_saved"] = time.time()
                self.state["_meta"]["save_count"] = self.save_count + 1
                
                # Atomic write
                tmp_file = self.state_file + ".tmp"
                with open(tmp_file, 'w') as f:
                    json.dump(self.state, f, indent=2, ensure_ascii=False)
                os.replace(tmp_file, self.state_file)
                
                self.save_count += 1
                self.dirty = False
            except Exception as e:
                print(f"⚠️ Error guardando estado: {e}")
    
    def get_module_state(self, module: str, default: Any = None) -> Any:
        """Obtiene el estado de un módulo específico."""
        return self.state.get(module, default if default is not None else {})
    
    def set_module_state(self, module: str, data: Any, auto_save: bool = True):
        """Establece el estado de un módulo y propaga el cambio."""
        with self.lock:
            self.state[module] = data
            
            # Registrar módulo
            if module not in self.state["_meta"]["modules"]:
                self.state["_meta"]["modules"].append(module)
            
            self.state[module + "._updated"] = time.time()
            self.dirty = True
        
        if auto_save:
            self.save()
        
        # Notificar al bus de eventos (si existe)
        try:
            from colony_core import colony_bus
            colony_bus.emit(f"{module}.state.changed", {
                "module": module,
                "timestamp": time.time(),
            })
        except ImportError:
            pass
    
    def update_module_state(self, module: str, updates: Dict, auto_save: bool = True):
        """Actualiza parcialmente el estado de un módulo."""
        current = self.get_module_state(module, {})
        if isinstance(current, dict):
            current.update(updates)
        else:
            current = updates
        self.set_module_state(module, current, auto_save)
    
    def get_all(self) -> Dict:
        """Obtiene el estado completo de la colonia."""
        return dict(self.state)
    
    def get_meta(self) -> Dict:
        """Metadatos de la colonia."""
        return self.state.get("_meta", {})
    
    def reset_module(self, module: str):
        """Reinicia el estado de un módulo."""
        self.set_module_state(module, {})
    
    def health_check(self) -> Dict:
        """Verificación de salud de la persistencia."""
        return {
            "state_file": self.state_file,
            "exists": os.path.exists(self.state_file),
            "size_kb": os.path.getsize(self.state_file) // 1024 if os.path.exists(self.state_file) else 0,
            "modules": len(self.state.get("_meta", {}).get("modules", [])),
            "saves": self.save_count,
            "loads": self.load_count,
            "last_saved": self.state.get("_meta", {}).get("last_saved", 0),
            "dirty": self.dirty,
        }


# ═══════════════════════════════════════════════
# COLONY EVENT BUS — Propagación Pub/Sub
# ═══════════════════════════════════════════════

@dataclass
class Event:
    """Un evento en la colonia."""
    name: str
    data: Any = None
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    propagation_count: int = 0


class ColonyEventBus:
    """
    Bus de eventos central de la colonia.
    
    Patrón Pub/Sub:
      - Los módulos PUBLICAN eventos cuando cambian
      - Los módulos se SUSCRIBEN a eventos que les importan
      - El bus PROPAGA eventos a todos los suscriptores
    
    Eventos estándar de la colonia:
      agent.task.completed     → Una tarea del lifecycle se completó
      agent.task.failed        → Una tarea falló
      memory.mos.created       → Nueva MOS en memoria jerárquica
      tournament.round.end     → Terminó una ronda del torneo
      tournament.completed     → Terminó un torneo completo
      entropy.phase.changed    → Cambió la fase entrópica
      skill.crystallized       → Trace2Skill cristalizó una nueva skill
      harness.gate.triggered   → Un gate del harness se activó
      colony.state.saved       → El estado se persistió
      colony.module.registered → Un nuevo módulo se registró
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.wildcard_subscribers: List[Callable] = []
        self.event_log: List[Event] = []
        self.max_log_size = 1000
        self.propagation_count = 0
        self.lock = threading.Lock()
    
    def subscribe(self, event_name: str, callback: Callable):
        """
        Suscribe un callback a un evento.
        
        Args:
            event_name: Nombre del evento (ej: 'agent.task.completed')
                       Puede usar wildcard: 'agent.*' o '*'
            callback: Función que recibe un Event
        """
        if event_name == '*':
            self.wildcard_subscribers.append(callback)
        else:
            self.subscribers[event_name].append(callback)
    
    def unsubscribe(self, event_name: str, callback: Callable):
        """Desuscribe un callback."""
        if event_name == '*':
            if callback in self.wildcard_subscribers:
                self.wildcard_subscribers.remove(callback)
        elif event_name in self.subscribers:
            if callback in self.subscribers[event_name]:
                self.subscribers[event_name].remove(callback)
    
    def emit(self, event_name: str, data: Any = None, source: str = ""):
        """
        Emite un evento a todos los suscriptores.
        
        La propagación es SINCRÓNICA (en orden de suscripción).
        """
        event = Event(name=event_name, data=data, source=source)
        
        with self.lock:
            # Notificar suscriptores exactos
            callbacks = self.subscribers.get(event_name, [])
            
            # Notificar wildcards
            callbacks = list(callbacks) + list(self.wildcard_subscribers)
            
            # También notificar suscriptores de patrones (ej: 'agent.*')
            parts = event_name.split('.')
            for i in range(len(parts)):
                pattern = '.'.join(parts[:i+1]) + '.*'
                callbacks.extend(self.subscribers.get(pattern, []))
        
        # Ejecutar callbacks (fuera del lock para evitar deadlocks)
        for callback in callbacks:
            try:
                callback(event)
                event.propagation_count += 1
            except Exception as e:
                print(f"⚠️ Error en callback de {event_name}: {e}")
                traceback.print_exc()
        
        self.propagation_count += 1
        
        # Guardar en log
        self.event_log.append(event)
        if len(self.event_log) > self.max_log_size:
            self.event_log = self.event_log[-self.max_log_size:]
        
        return event
    
    def get_recent_events(self, n: int = 50, filter_name: str = None) -> List[Event]:
        """Obtiene los eventos más recientes."""
        events = self.event_log[-n:]
        if filter_name:
            events = [e for e in events if filter_name in e.name]
        return events
    
    def get_stats(self) -> Dict:
        """Estadísticas del bus."""
        return {
            "total_subscriptions": sum(len(v) for v in self.subscribers.values()) + len(self.wildcard_subscribers),
            "unique_events": len(self.subscribers),
            "total_emissions": self.propagation_count,
            "events_logged": len(self.event_log),
            "top_events": sorted(
                [(k, len(v)) for k, v in self.subscribers.items()],
                key=lambda x: -x[1]
            )[:10],
        }


# ═══════════════════════════════════════════════
# COLONY NUCLEUS — Inicialización Central
# ═══════════════════════════════════════════════

class ColonyNucleus:
    """
    Núcleo central de la colonia.
    
    Inicializa el StateManager y el EventBus.
    Conecta todos los módulos entre sí mediante eventos.
    Proporciona la API unificada para toda la colonia.
    """
    
    def __init__(self, state_file: str = None):
        self.state_manager = ColonyStateManager(state_file)
        self.event_bus = ColonyEventBus()
        self.start_time = time.time()
        self.modules_registered: List[str] = []
        
        # Conectar persistencia ↔ bus
        self._wire_persistence()
    
    def _wire_persistence(self):
        """Conecta el ciclo de persistencia con el bus de eventos."""
        def on_state_changed(event: Event):
            """Cuando cualquier módulo cambia, auto-save."""
            self.state_manager.save()
        
        self.event_bus.subscribe('*.state.changed', on_state_changed)
    
    def register_module(self, module_name: str, initial_state: Any = None):
        """
        Registra un módulo en la colonia.
        
        1. Inicializa su estado si no existe
        2. Lo registra en el bus
        3. Emite evento de registro
        4. Propaga a otros módulos
        """
        if module_name in self.modules_registered:
            return
        
        # Inicializar estado
        if initial_state is not None:
            existing = self.state_manager.get_module_state(module_name)
            if not existing:
                self.state_manager.set_module_state(module_name, initial_state, auto_save=False)
        
        self.modules_registered.append(module_name)
        
        # Emitir evento de registro
        self.event_bus.emit("colony.module.registered", {
            "module": module_name,
            "total_modules": len(self.modules_registered),
        }, source="nucleus")
        
        # Propagar a todos los módulos existentes
        self.event_bus.emit(f"{module_name}.initialized", {
            "module": module_name,
            "state": self.state_manager.get_module_state(module_name),
        }, source="nucleus")
    
    def get_colony_health(self) -> Dict:
        """Estado de salud completo de la colonia."""
        return {
            "uptime_seconds": time.time() - self.start_time,
            "modules_registered": len(self.modules_registered),
            "modules": self.modules_registered,
            "persistence": self.state_manager.health_check(),
            "event_bus": self.event_bus.get_stats(),
            "state_keys": list(self.state_manager.state.keys()),
        }
    
    def propagate_to_all(self, event_name: str, data: Any = None):
        """Propaga un evento a TODOS los módulos registrados."""
        for module in self.modules_registered:
            self.event_bus.emit(f"{module}.{event_name}", data, source="nucleus")
        
        self.event_bus.emit(f"colony.{event_name}", data, source="nucleus")
    
    def shutdown(self):
        """Apagado seguro: guarda estado y notifica."""
        self.event_bus.emit("colony.shutdown", {
            "uptime": time.time() - self.start_time,
            "modules": len(self.modules_registered),
        })
        self.state_manager.save(force=True)


# ═══════════════════════════════════════════════
# INSTANCIAS GLOBALES — El corazón de la colonia
# ═══════════════════════════════════════════════

# Estas son LAS instancias que todos los módulos deben usar
colony_state = ColonyStateManager()
colony_bus = ColonyEventBus()
colony_nucleus = ColonyNucleus()


# ═══════════════════════════════════════════════
# API UNIFICADA
# ═══════════════════════════════════════════════

def persist(module: str, data: Any):
    """Persiste el estado de un módulo."""
    colony_state.set_module_state(module, data)

def load_state(module: str, default: Any = None) -> Any:
    """Carga el estado persistido de un módulo."""
    return colony_state.get_module_state(module, default)

def emit(event: str, data: Any = None, source: str = ""):
    """Emite un evento al bus de la colonia."""
    return colony_bus.emit(event, data, source)

def on(event: str, callback: Callable):
    """Suscribe un callback a un evento."""
    colony_bus.subscribe(event, callback)

def propagate(event: str, data: Any = None):
    """Propaga un evento a todos los módulos."""
    colony_nucleus.propagate_to_all(event, data)

def colony_health() -> Dict:
    """Salud completa de la colonia."""
    return colony_nucleus.get_colony_health()

def register(module_name: str, initial_state: Any = None):
    """Registra un módulo en la colonia."""
    colony_nucleus.register_module(module_name, initial_state)


# ─── Inicialización automática ───
# Al importar este módulo, la colonia despierta con estado persistido
_colony_started = True
