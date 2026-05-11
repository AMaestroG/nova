"""
Configuración del Sistema Centinela
Nova Homonexus - MAYORDOMO
"""

import os
from pathlib import Path

# =============================================================================
# BASE DE DATOS
# =============================================================================
DB_CONFIG = {
    "host": os.getenv("CENTINELA_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("CENTINELA_DB_PORT", "5433")),
    "database": os.getenv("CENTINELA_DB_NAME", "nexus_metamorfosis"),
    "user": os.getenv("CENTINELA_DB_USER", "nexus_master"),
    "password": os.getenv("CENTINELA_DB_PASSWORD", "nexus_password_dev"),
}

DB_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Alias para compatibilidad con tests existentes
DATABASE = DB_URL

# =============================================================================
# SERVIDOR
# =============================================================================
SERVER_HOST = os.getenv("CENTINELA_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("CENTINELA_PORT", "9088"))
DASHBOARD_URL = os.getenv("CENTINELA_DASHBOARD_URL", "http://127.0.0.1:9088")

# =============================================================================
# DISPOSITIVOS
# =============================================================================
DEVICE_ZFOLD_ID = os.getenv("CENTINELA_ZFOLD_ID", "samsung_zfold_01")
DEVICE_WATCH8_ID = os.getenv("CENTINELA_WATCH8_ID", "samsung_watch8_01")

# =============================================================================
# FRECUENCIAS DE MUESTREO (en segundos)
# =============================================================================
SAMPLE_RATES = {
    "acelerometro": 0.1,       # 10 Hz
    "giroscopio": 0.1,         # 10 Hz
    "magnetometro": 0.2,       # 5 Hz
    "barometro": 1.0,          # 1 Hz
    "proximidad": 1.0,         # 1 Hz
    "luz_ambiental": 2.0,      # 0.5 Hz
    "gps": 5.0,                # cada 5 segundos
    "health_heart_rate": 1.0,  # 1 Hz
    "health_ecg": 0.002,       # 500 Hz (cada 2ms)
    "health_spo2": 5.0,        # cada 5 segundos
    "health_temperature": 60.0,# cada 1 minuto
    "health_bp": 300.0,        # cada 5 minutos
    "emocion": 10.0,           # cada 10 segundos
}

# =============================================================================
# UMBRALES DE ALERTA
# =============================================================================
ALERT_THRESHOLDS = {
    "heart_rate_min": 40,
    "heart_rate_max": 180,
    "heart_rate_critical_min": 30,
    "heart_rate_critical_max": 220,
    "spo2_min": 90.0,
    "spo2_critical_min": 85.0,
    "temperature_min": 35.0,
    "temperature_max": 39.0,
    "temperature_critical_min": 34.0,
    "temperature_critical_max": 41.0,
    "blood_pressure_sys_max": 180,
    "blood_pressure_dia_max": 120,
    "blood_pressure_sys_min": 70,
    "blood_pressure_dia_min": 40,
    "stress_level_max": 80,
    "stress_level_critical": 95,
    "battery_min": 15,
    "battery_critical": 5,
    "gps_accuracy_max": 50,    # metros
}

# =============================================================================
# DETECCIÓN EMOCIONAL
# =============================================================================
EMOTION_CONFIG = {
    "enabled": True,
    "model_path": str(Path(__file__).parent / "models" / "emotion_model.pkl"),
    "features": [
        "heart_rate", "hrv", "gsr_estimado", "skin_temperature",
        "spo2", "accelerometer_variance", "speech_prosody",
    ],
    "emotion_labels": [
        "neutro", "feliz", "triste", "enojado", "ansioso",
        "estresado", "relajado", "sorprendido", "asustado", "confundido",
    ],
    "min_confidence": 0.4,
}

# =============================================================================
# TERMUX
# =============================================================================
TERMUX_CONFIG = {
    "sensor_batch_size": 10,
    "max_retries": 3,
    "retry_delay": 1.0,
    "websocket_reconnect": True,
    "websocket_reconnect_delay": 5.0,
    "health_connect_package": "com.samsung.android.health",
    "use_mock_sensors": os.getenv("CENTINELA_MOCK", "false").lower() == "true",
}

# =============================================================================
# SEGURIDAD
# =============================================================================
SECURITY = {
    "api_key_required": True,
    "api_key": os.getenv("CENTINELA_API_KEY", "nexus-centinela-key-2026"),
    "rate_limit_per_minute": 600,
    "max_payload_size_mb": 10,
    "encryption_enabled": True,
    "allowed_origins": [
        "http://127.0.0.1:9088",
        "http://localhost:9088",
        "http://192.168.*:*",
    ],
}

# =============================================================================
# LOGGING
# =============================================================================
LOG_CONFIG = {
    "level": os.getenv("CENTINELA_LOG_LEVEL", "INFO"),
    "file": str(Path.home() / "nova" / "logs" / "centinela.log"),
    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    "max_bytes": 10 * 1024 * 1024,  # 10 MB
    "backup_count": 5,
}

# =============================================================================
# WEBSOCKET
# =============================================================================
WEBSOCKET_CONFIG = {
    "ping_interval": 30,
    "ping_timeout": 10,
    "max_message_size": 1024 * 1024,  # 1 MB
    "channel": "centinela:stream",
}
