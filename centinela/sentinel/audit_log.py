"""
audit_log — Registro de Auditoría Inmutable
Nova Homonexus — SENTINEL

Registro de auditoría con integridad criptográfica:
  - Hash encadenado (tipo blockchain)
  - Append-only (no modificable)
  - Formato JSON estructurado
  - Búsqueda por timestamp, tipo, severidad
  - Exportación para auditoría externa
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from centinela.sentinel.rules import SecurityRules

logger = logging.getLogger("sentinel.audit")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AuditEntry:
    """Entrada individual de auditoría."""
    index: int
    timestamp: float
    level: str  # SECURITY, ACCESS, DATA, SYSTEM, ALERT
    event_type: str
    source: str
    description: str
    details: Dict[str, Any]
    previous_hash: str
    hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "level": self.level,
            "event_type": self.event_type,
            "source": self.source,
            "description": self.description,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
        }

    def to_json(self) -> str:
        """Serializa a JSON para almacenamiento."""
        d = self.to_dict()
        # Guardar timestamp como número, no string ISO
        d["timestamp"] = self.timestamp
        return json.dumps(d, ensure_ascii=False)


# =============================================================================
# AUDIT LOG
# =============================================================================

class AuditLog:
    """
    Registro de auditoría inmutable con hash encadenado.

    Características:
      - Cada entrada contiene el hash de la anterior (blockchain)
      - Append-only: no se puede modificar entradas existentes
      - Verificación de integridad de toda la cadena
      - Almacenamiento en DB y archivo JSON
      - Búsqueda y exportación
    """

    def __init__(self, rules: Optional[SecurityRules] = None):
        self._rules = rules or SecurityRules()
        audit_cfg = self._rules.audit

        # Hash algorithm
        self._hash_algo = audit_cfg.get("hash_algorithm", "sha256")

        # Genesis hash
        self._genesis_hash = audit_cfg.get(
            "genesis_hash",
            "0" * 64,  # 64 zeros for SHA-256
        )

        # Storage
        self._db_storage = audit_cfg.get("db_storage", True)
        self._file_backup = audit_cfg.get("file_backup", True)
        self._backup_path = Path(
            audit_cfg.get(
                "backup_path",
                "/home/opc/nova/logs/centinela_audit.json",
            )
        )
        self._backup_max_mb = audit_cfg.get("backup_max_mb", 100)

        # Niveles de auditoría
        self._levels = set(
            audit_cfg.get(
                "levels",
                ["SECURITY", "ACCESS", "DATA", "SYSTEM", "ALERT"],
            )
        )

        # Cadena de auditoría en memoria (caché)
        self._chain: List[AuditEntry] = []
        self._last_hash: str = self._genesis_hash
        self._next_index: int = 0

        # Cargar cadena existente
        self._load_existing_chain()

        logger.info(
            "AuditLog inicializado. "
            "Hash: %s, Entradas: %d, Último hash: %s...",
            self._hash_algo,
            len(self._chain),
            self._last_hash[:16],
        )

    # ------------------------------------------------------------------
    # CÁLCULO DE HASH
    # ------------------------------------------------------------------

    def _compute_hash(self, entry_data: Dict[str, Any]) -> str:
        """
        Calcula el hash SHA-256 de una entrada de auditoría.

        Args:
            entry_data: Datos de la entrada (sin hash).

        Returns:
            Hash hexadecimal.
        """
        # Serializar deterministicamente
        serialized = json.dumps(
            entry_data, sort_keys=True, ensure_ascii=False
        ).encode("utf-8")

        return hashlib.new(
            self._hash_algo, serialized
        ).hexdigest()

    # ------------------------------------------------------------------
    # CARGA DE CADENA EXISTENTE
    # ------------------------------------------------------------------

    def _load_existing_chain(self) -> None:
        """Carga la cadena de auditoría existente desde archivo."""
        if not self._file_backup:
            return

        if not self._backup_path.exists():
            logger.debug(
                "Archivo de auditoría no existe: %s",
                self._backup_path,
            )
            return

        try:
            with open(self._backup_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        ts = data["timestamp"]
                        if isinstance(ts, str):
                            # Convertir desde ISO a timestamp
                            ts = datetime.fromisoformat(
                                ts
                            ).timestamp()
                        entry = AuditEntry(
                            index=data["index"],
                            timestamp=ts,
                            level=data["level"],
                            event_type=data["event_type"],
                            source=data["source"],
                            description=data["description"],
                            details=data.get("details", {}),
                            previous_hash=data["previous_hash"],
                            hash=data["hash"],
                        )
                        self._chain.append(entry)
                        self._last_hash = entry.hash
                        self._next_index = entry.index + 1
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(
                            "Entrada de auditoría corrupta: %s", e
                        )
                        continue

            logger.info(
                "Cadena de auditoría cargada: %d entradas",
                len(self._chain),
            )

        except IOError as e:
            logger.error(
                "Error al cargar auditoría: %s", str(e)
            )

    # ------------------------------------------------------------------
    # REGISTRO DE ENTRADAS
    # ------------------------------------------------------------------

    def log(
        self,
        level: str,
        event_type: str,
        source: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Registra una entrada en el log de auditoría.

        Args:
            level: Nivel (SECURITY, ACCESS, DATA, SYSTEM, ALERT).
            event_type: Tipo de evento.
            source: Origen del evento.
            description: Descripción del evento.
            details: Detalles adicionales.

        Returns:
            AuditEntry creado.

        Raises:
            ValueError: Si el nivel no es válido.
        """
        if level not in self._levels:
            raise ValueError(
                f"Nivel de auditoría inválido: {level}. "
                f"Válidos: {self._levels}"
            )

        now = time.time()

        entry_data = {
            "index": self._next_index,
            "timestamp": now,
            "level": level,
            "event_type": event_type,
            "source": source,
            "description": description,
            "details": details or {},
            "previous_hash": self._last_hash,
        }

        entry_hash = self._compute_hash(entry_data)

        entry = AuditEntry(
            index=self._next_index,
            timestamp=now,
            level=level,
            event_type=event_type,
            source=source,
            description=description,
            details=details or {},
            previous_hash=self._last_hash,
            hash=entry_hash,
        )

        # Actualizar estado
        self._chain.append(entry)
        self._last_hash = entry_hash
        self._next_index += 1

        # Persistir
        self._persist_entry(entry)

        logger.debug(
            "Auditoría [%s/%s]: %s",
            level,
            source,
            description,
        )

        return entry

    def _persist_entry(self, entry: AuditEntry) -> None:
        """
        Persiste una entrada de auditoría.

        Args:
            entry: Entrada a persistir.
        """
        # Archivo JSON (append-only)
        if self._file_backup:
            try:
                self._backup_path.parent.mkdir(
                    parents=True, exist_ok=True
                )

                # Verificar tamaño
                if self._backup_path.exists():
                    size_mb = (
                        self._backup_path.stat().st_size
                        / (1024 * 1024)
                    )
                    if size_mb > self._backup_max_mb:
                        # Rotar archivo
                        backup_old = self._backup_path.with_suffix(
                            ".old.json"
                        )
                        if backup_old.exists():
                            backup_old.unlink()
                        self._backup_path.rename(backup_old)
                        logger.info(
                            "Archivo de auditoría rotado"
                        )

                with open(
                    self._backup_path,
                    "a",
                    encoding="utf-8",
                ) as f:
                    f.write(entry.to_json() + "\n")

            except IOError as e:
                logger.error(
                    "Error al persistir auditoría: %s", str(e)
                )

        # Base de datos (opcional)
        if self._db_storage:
            # La inserción en DB se maneja externamente
            pass

    # ------------------------------------------------------------------
    # VERIFICACIÓN DE INTEGRIDAD
    # ------------------------------------------------------------------

    def verify_chain(
        self, start_index: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Verifica la integridad de toda la cadena de auditoría.

        Recorre la cadena verificando que cada entrada contenga
        el hash correcto de la entrada anterior.

        Args:
            start_index: Índice desde donde verificar.

        Returns:
            Lista de anomalías encontradas (vacía si todo ok).
        """
        anomalies = []
        previous_hash = self._genesis_hash

        for entry in self._chain[start_index:]:
            # Recalcular hash
            entry_data = {
                "index": entry.index,
                "timestamp": entry.timestamp,
                "level": entry.level,
                "event_type": entry.event_type,
                "source": entry.source,
                "description": entry.description,
                "details": entry.details,
                "previous_hash": entry.previous_hash,
            }
            expected_hash = self._compute_hash(entry_data)

            # Verificar hash propio
            if entry.hash != expected_hash:
                anomalies.append({
                    "index": entry.index,
                    "tipo": "hash_modificado",
                    "esperado": expected_hash,
                    "encontrado": entry.hash,
                    "descripcion": (
                        f"Hash de entrada {entry.index} "
                        f"no coincide"
                    ),
                })

            # Verificar hash anterior
            if entry.previous_hash != previous_hash:
                anomalies.append({
                    "index": entry.index,
                    "tipo": "cadena_rota",
                    "esperado": previous_hash,
                    "encontrado": entry.previous_hash,
                    "descripcion": (
                        f"Enlace roto en entrada {entry.index}"
                    ),
                })

            previous_hash = entry.hash

        if anomalies:
            logger.warning(
                "Cadena de auditoría corrupta: %d anomalías",
                len(anomalies),
            )
        else:
            logger.info(
                "Cadena de auditoría íntegra: %d entradas",
                len(self._chain),
            )

        return anomalies

    # ------------------------------------------------------------------
    # BÚSQUEDA
    # ------------------------------------------------------------------

    def search(
        self,
        level: Optional[str] = None,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        description_contains: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Busca entradas en el log de auditoría.

        Args:
            level: Filtrar por nivel.
            event_type: Filtrar por tipo de evento.
            source: Filtrar por origen.
            description_contains: Buscar texto en descripción.
            start_time: Timestamp inicial.
            end_time: Timestamp final.
            limit: Máximo de resultados.
            offset: Desplazamiento.

        Returns:
            Lista de entradas de auditoría.
        """
        results = []

        for entry in reversed(self._chain):
            if len(results) >= limit + offset:
                break

            if level and entry.level != level:
                continue
            if event_type and entry.event_type != event_type:
                continue
            if source and entry.source != source:
                continue
            if (
                description_contains
                and description_contains.lower()
                not in entry.description.lower()
            ):
                continue
            if (
                start_time
                and entry.timestamp < start_time
            ):
                continue
            if end_time and entry.timestamp > end_time:
                continue

            results.append(entry.to_dict())

        return results[offset:offset + limit]

    def get_by_index(
        self, index: int
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene una entrada por su índice.

        Args:
            index: Índice de la entrada.

        Returns:
            Entrada o None.
        """
        for entry in self._chain:
            if entry.index == index:
                return entry.to_dict()
        return None

    # ------------------------------------------------------------------
    # EXPORTACIÓN
    # ------------------------------------------------------------------

    def export(
        self,
        output_path: Optional[str] = None,
        start_index: int = 0,
        end_index: Optional[int] = None,
    ) -> str:
        """
        Exporta la cadena de auditoría a un archivo JSON.

        Args:
            output_path: Ruta de salida (opcional).
            start_index: Índice inicial.
            end_index: Índice final (opcional).

        Returns:
            Ruta del archivo exportado.
        """
        if end_index is None:
            end_index = self._next_index - 1

        path = Path(
            output_path
            or f"/tmp/centinela_audit_export_{int(time.time())}.json"
        )

        entries = [
            entry.to_dict()
            for entry in self._chain
            if start_index <= entry.index <= end_index
        ]

        export_data = {
            "metadata": {
                "system": "Centinela Audit Log",
                "hash_algorithm": self._hash_algo,
                "genesis_hash": self._genesis_hash,
                "total_entries": len(self._chain),
                "exported_entries": len(entries),
                "export_time": datetime.now(
                    timezone.utc
                ).isoformat(),
                "verified": len(self.verify_chain()) == 0,
            },
            "entries": entries,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(
            "Auditoría exportada: %d entradas a %s",
            len(entries),
            path,
        )

        return str(path)

    # ------------------------------------------------------------------
    # ESTADO
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del log de auditoría.

        Returns:
            Dict con estadísticas.
        """
        stats: Dict[str, Any] = {
            "total_entries": len(self._chain),
            "next_index": self._next_index,
            "last_hash": self._last_hash[:16] + "...",
            "genesis_hash": self._genesis_hash[:16] + "...",
            "hash_algorithm": self._hash_algo,
            "by_level": {},
            "by_source": {},
            "by_event_type": {},
            "time_range": {},
            "verified": False,
        }

        for entry in self._chain:
            stats["by_level"][entry.level] = (
                stats["by_level"].get(entry.level, 0) + 1
            )
            stats["by_source"][entry.source] = (
                stats["by_source"].get(entry.source, 0) + 1
            )
            stats["by_event_type"][entry.event_type] = (
                stats["by_event_type"].get(entry.event_type, 0) + 1
            )

        if self._chain:
            stats["time_range"] = {
                "first": datetime.fromtimestamp(
                    self._chain[0].timestamp, tz=timezone.utc
                ).isoformat(),
                "last": datetime.fromtimestamp(
                    self._chain[-1].timestamp, tz=timezone.utc
                ).isoformat(),
            }

        # Verificar integridad
        anomalies = self.verify_chain()
        stats["verified"] = len(anomalies) == 0
        stats["anomalies"] = len(anomalies)

        return stats
