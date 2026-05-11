"""
Modelos SQLAlchemy para el Sistema Centinela
Nova Homonexus - MAYORDOMO
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, BigInteger, SmallInteger, Integer, String, Text,
    Float, Boolean, DateTime, ForeignKey, Index, JSON, Enum as SAEnum,
    UniqueConstraint, CheckConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression
import uuid

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


# =============================================================================
# centinela_sensores
# =============================================================================
class SensorLectura(Base):
    __tablename__ = "centinela_sensores"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, default="samsung_zfold_01")
    tipo_sensor = Column(String(64), nullable=False, index=True)
    valor = Column(JSONB, nullable=False)
    precision_val = Column(Float)
    unidad = Column(String(32))
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    batch_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_sensores_device_ts", "device_id", "timestamp"),
        Index("idx_sensores_batch", "batch_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "tipo_sensor": self.tipo_sensor,
            "valor": self.valor,
            "precision": self.precision_val,
            "unidad": self.unidad,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# centinela_ubicacion
# =============================================================================
class Ubicacion(Base):
    __tablename__ = "centinela_ubicacion"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, default="samsung_zfold_01")
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    altitud = Column(Float)
    velocidad = Column(Float)
    rumbo = Column(Float)
    precision_h = Column(Float)
    precision_v = Column(Float)
    proveedor = Column(String(32), default="gps")
    num_satelites = Column(SmallInteger)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_ubicacion_device_ts", "device_id", "timestamp"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "lat": self.lat,
            "lon": self.lon,
            "altitud": self.altitud,
            "velocidad": self.velocidad,
            "rumbo": self.rumbo,
            "precision_h": self.precision_h,
            "precision_v": self.precision_v,
            "proveedor": self.proveedor,
            "num_satelites": self.num_satelites,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# centinela_health
# =============================================================================
class HealthRecord(Base):
    __tablename__ = "centinela_health"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, default="samsung_watch8_01")
    heart_rate = Column(SmallInteger)
    heart_rate_status = Column(String(16))
    ecg_data = Column(JSONB)
    ecg_interval_ms = Column(Float)
    blood_pressure_sys = Column(SmallInteger)
    blood_pressure_dia = Column(SmallInteger)
    blood_pressure_map = Column(SmallInteger)
    temperature_skin = Column(Float)
    temperature_core = Column(Float)
    spo2 = Column(Float)
    spo2_status = Column(String(16))
    stress_level = Column(SmallInteger)
    stress_status = Column(String(16))
    sleep_stage = Column(String(32))
    sleep_quality = Column(SmallInteger)
    steps = Column(Integer)
    calories = Column(Float)
    distance_m = Column(Float)
    bioimpedance = Column(JSONB)
    bia_body_fat = Column(Float)
    bia_muscle_mass = Column(Float)
    bia_bone_mass = Column(Float)
    bia_body_water = Column(Float)
    bia_bmr = Column(SmallInteger)
    hrv = Column(Float)
    hrv_sdnn = Column(Float)
    hrv_rmssd = Column(Float)
    battery_level = Column(SmallInteger)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_health_hr_ts", "heart_rate", "timestamp"),
        Index("idx_health_device_ts", "device_id", "timestamp"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "heart_rate": self.heart_rate,
            "heart_rate_status": self.heart_rate_status,
            "blood_pressure_sys": self.blood_pressure_sys,
            "blood_pressure_dia": self.blood_pressure_dia,
            "temperature_skin": self.temperature_skin,
            "temperature_core": self.temperature_core,
            "spo2": self.spo2,
            "stress_level": self.stress_level,
            "sleep_stage": self.sleep_stage,
            "steps": self.steps,
            "hrv": self.hrv,
            "battery_level": self.battery_level,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# centinela_emociones
# =============================================================================
class Emocion(Base):
    __tablename__ = "centinela_emociones"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, default="samsung_zfold_01")
    emocion_detectada = Column(String(32), nullable=False)
    confianza = Column(Float, nullable=False)
    heart_rate = Column(SmallInteger)
    hrv = Column(Float)
    gsr_estimado = Column(Float)
    skin_temperature = Column(Float)
    accelerometer_var = Column(Float)
    speech_prosody = Column(JSONB)
    facial_expression = Column(JSONB)
    emociones_secundarias = Column(JSONB)
    conversacion_id = Column(String(64))
    contexto = Column(String(256))
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_emociones_emocion_ts", "emocion_detectada", "timestamp"),
        Index("idx_emociones_conversacion", "conversacion_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "emocion_detectada": self.emocion_detectada,
            "confianza": self.confianza,
            "heart_rate": self.heart_rate,
            "hrv": self.hrv,
            "gsr_estimado": self.gsr_estimado,
            "skin_temperature": self.skin_temperature,
            "conversacion_id": self.conversacion_id,
            "contexto": self.contexto,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# centinela_alertas
# =============================================================================
class Alerta(Base):
    __tablename__ = "centinela_alertas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tipo = Column(String(32), nullable=False)
    severidad = Column(String(16), nullable=False, default="info")
    mensaje = Column(Text, nullable=False)
    datos = Column(JSONB)
    device_id = Column(String(64))
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    resuelta = Column(Boolean, nullable=False, default=False)
    resuelta_por = Column(String(64))
    resuelta_en = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_alertas_activas", "resuelta", "severidad"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "severidad": self.severidad,
            "mensaje": self.mensaje,
            "datos": self.datos,
            "device_id": self.device_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "resuelta": self.resuelta,
        }


# =============================================================================
# centinela_eventos
# =============================================================================
class Evento(Base):
    __tablename__ = "centinela_eventos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tipo_evento = Column(String(64), nullable=False)
    descripcion = Column(Text)
    datos_json = Column(JSONB)
    device_id = Column(String(64))
    ubicacion_id = Column(BigInteger, ForeignKey("centinela_ubicacion.id"))
    sensor_id = Column(BigInteger, ForeignKey("centinela_sensores.id"))
    health_id = Column(BigInteger, ForeignKey("centinela_health.id"))
    emocion_id = Column(BigInteger, ForeignKey("centinela_emociones.id"))
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    ubicacion = relationship("Ubicacion")
    sensor = relationship("SensorLectura")
    health = relationship("HealthRecord")
    emocion = relationship("Emocion")

    __table_args__ = (
        Index("idx_eventos_tipo_ts", "tipo_evento", "timestamp"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tipo_evento": self.tipo_evento,
            "descripcion": self.descripcion,
            "datos_json": self.datos_json,
            "device_id": self.device_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# centinela_sesiones
# =============================================================================
class SesionMonitoreo(Base):
    __tablename__ = "centinela_sesiones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(64), nullable=False)
    inicio = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    fin = Column(DateTime(timezone=True))
    estado = Column(String(16), nullable=False, default="activa")
    sensores_activos = Column(JSONB)
    watch_conectado = Column(Boolean, default=False)
    total_lecturas = Column(BigInteger, default=0)
    ip_origen = Column(INET)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_sesiones_activas", "estado", "device_id"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "device_id": self.device_id,
            "inicio": self.inicio.isoformat() if self.inicio else None,
            "fin": self.fin.isoformat() if self.fin else None,
            "estado": self.estado,
            "sensores_activos": self.sensores_activos,
            "watch_conectado": self.watch_conectado,
            "total_lecturas": self.total_lecturas,
        }
