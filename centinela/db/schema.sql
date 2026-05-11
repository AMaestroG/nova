-- =============================================================================
-- ESQUEMA SQL - Sistema Centinela
-- Nova Homonexus - MAYORDOMO
-- Base de datos: nexus_metamorfosis (PostgreSQL 16+)
-- =============================================================================

-- Extensión para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Extensión para PostGIS (mapas)
CREATE EXTENSION IF NOT EXISTS "postgis";

-- =============================================================================
-- 1. centinela_sensores - Lecturas de sensores del Samsung Z Fold
-- =============================================================================
CREATE TABLE IF NOT EXISTS centinela_sensores (
    id              BIGSERIAL PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL DEFAULT 'samsung_zfold_01',
    tipo_sensor     VARCHAR(64) NOT NULL,
    valor           JSONB NOT NULL,
    precision_val   REAL,
    unidad          VARCHAR(32),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    batch_id        UUID DEFAULT uuid_generate_v4(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensores_tipo ON centinela_sensores (tipo_sensor);
CREATE INDEX IF NOT EXISTS idx_sensores_timestamp ON centinela_sensores (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sensores_device ON centinela_sensores (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sensores_batch ON centinela_sensores (batch_id);

-- Tabla particionada por mes (opcional, para alto volumen)
-- CREATE TABLE centinela_sensores_2026_05 PARTITION OF centinela_sensores
--     FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

COMMENT ON TABLE centinela_sensores IS 'Lecturas de sensores del dispositivo centinela Z Fold';
COMMENT ON COLUMN centinela_sensores.tipo_sensor IS 'acelerometro, giroscopio, magnetometro, barometro, proximidad, luz_ambiental, huella, camara, microfono, nfc, uwb';
COMMENT ON COLUMN centinela_sensores.valor IS 'Valor del sensor en JSON (ej: {"x": 0.1, "y": -0.2, "z": 9.8})';
COMMENT ON COLUMN centinela_sensores.precision_val IS 'Precisión reportada por el sensor Android';

-- =============================================================================
-- 2. centinela_ubicacion - Datos GPS
-- =============================================================================
CREATE TABLE IF NOT EXISTS centinela_ubicacion (
    id              BIGSERIAL PRIMARY KEY,
    device_id       VARCHAR(64) NOT NULL DEFAULT 'samsung_zfold_01',
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    altitud         REAL,
    velocidad       REAL,
    rumbo           REAL,
    precision_h     REAL,
    precision_v     REAL,
    proveedor       VARCHAR(32) DEFAULT 'gps',
    num_satelites   SMALLINT,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    geom            GEOMETRY(Point, 4326) GENERATED ALWAYS AS (
                        ST_SetSRID(ST_MakePoint(lon, lat), 4326)
                    ) STORED,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ubicacion_timestamp ON centinela_ubicacion (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ubicacion_geom ON centinela_ubicacion USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_ubicacion_device ON centinela_ubicacion (device_id, timestamp DESC);

COMMENT ON TABLE centinela_ubicacion IS 'Historial de ubicaciones GPS del dispositivo centinela';
COMMENT ON COLUMN centinela_ubicacion.proveedor IS 'gps, network, fused, wifi';

-- =============================================================================
-- 3. centinela_health - Biométricas del Galaxy Watch 8 Classic
-- =============================================================================
CREATE TABLE IF NOT EXISTS centinela_health (
    id                  BIGSERIAL PRIMARY KEY,
    device_id           VARCHAR(64) NOT NULL DEFAULT 'samsung_watch8_01',
    heart_rate          SMALLINT,
    heart_rate_status   VARCHAR(16),
    ecg_data            JSONB,
    ecg_interval_ms     REAL,
    blood_pressure_sys  SMALLINT,
    blood_pressure_dia  SMALLINT,
    blood_pressure_map  SMALLINT,
    temperature_skin    REAL,
    temperature_core    REAL,
    spo2                REAL,
    spo2_status         VARCHAR(16),
    stress_level        SMALLINT,
    stress_status       VARCHAR(16),
    sleep_stage         VARCHAR(32),
    sleep_quality       SMALLINT,
    steps               INTEGER,
    calories            REAL,
    distance_m          REAL,
    bioimpedance        JSONB,
    bia_body_fat        REAL,
    bia_muscle_mass     REAL,
    bia_bone_mass       REAL,
    bia_body_water      REAL,
    bia_bmr             SMALLINT,
    hrv                 REAL,
    hrv_sdnn            REAL,
    hrv_rmssd           REAL,
    battery_level       SMALLINT,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_timestamp ON centinela_health (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_health_hr ON centinela_health (heart_rate, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_health_device ON centinela_health (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_health_stress ON centinela_health (stress_level, timestamp DESC);

COMMENT ON TABLE centinela_health IS 'Datos biométricos del Galaxy Watch 8 Classic';
COMMENT ON COLUMN centinela_health.heart_rate_status IS 'NORMAL, ELEVADO, BAJO, CRITICO';
COMMENT ON COLUMN centinela_health.ecg_data IS 'Formato JSON array de muestras ECG';
COMMENT ON COLUMN centinela_health.sleep_stage IS 'DESPIERTO, LIGERO, PROFUNDO, REM';
COMMENT ON COLUMN centinela_health.bioimpedance IS 'Datos completos de bioimpedancia (BIA)';

-- =============================================================================
-- 4. centinela_emociones - Detección emocional
-- =============================================================================
CREATE TABLE IF NOT EXISTS centinela_emociones (
    id                  BIGSERIAL PRIMARY KEY,
    device_id           VARCHAR(64) NOT NULL DEFAULT 'samsung_zfold_01',
    emocion_detectada   VARCHAR(32) NOT NULL,
    confianza           REAL NOT NULL,
    heart_rate          SMALLINT,
    hrv                 REAL,
    gsr_estimado        REAL,
    skin_temperature    REAL,
    accelerometer_var   REAL,
    speech_prosody      JSONB,
    facial_expression   JSONB,
    emociones_secundarias JSONB,
    conversacion_id     VARCHAR(64),
    contexto            VARCHAR(256),
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emociones_emocion ON centinela_emociones (emocion_detectada);
CREATE INDEX IF NOT EXISTS idx_emociones_timestamp ON centinela_emociones (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_emociones_conversacion ON centinela_emociones (conversacion_id);
CREATE INDEX IF NOT EXISTS idx_emociones_confianza ON centinela_emociones (confianza DESC);

COMMENT ON TABLE centinela_emociones IS 'Detección de emociones basada en biométricas y sensores';
COMMENT ON COLUMN centinela_emociones.emocion_detectada IS 'neutro, feliz, triste, enojado, ansioso, estresado, relajado, sorprendido, asustado, confundido';
COMMENT ON COLUMN centinela_emociones.gsr_estimado IS 'Respuesta galvánica de la piel estimada desde sensores';

-- =============================================================================
-- 5. centinela_alertas - Alertas del sistema
-- =============================================================================
CREATE TABLE IF NOT EXISTS centinela_alertas (
    id              BIGSERIAL PRIMARY KEY,
    tipo            VARCHAR(32) NOT NULL,
    severidad       VARCHAR(16) NOT NULL DEFAULT 'info',
    mensaje         TEXT NOT NULL,
    datos           JSONB,
    device_id       VARCHAR(64),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resuelta        BOOLEAN NOT NULL DEFAULT FALSE,
    resuelta_por    VARCHAR(64),
    resuelta_en     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alertas_severidad ON centinela_alertas (severidad, resuelta);
CREATE INDEX IF NOT EXISTS idx_alertas_timestamp ON centinela_alertas (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alertas_tipo ON centinela_alertas (tipo);
CREATE INDEX IF NOT EXISTS idx_alertas_activas ON centinela_alertas (resuelta, severidad) WHERE resuelta = FALSE;

COMMENT ON TABLE centinela_alertas IS 'Alertas generadas por el sistema centinela';
COMMENT ON COLUMN centinela_alertas.tipo IS 'salud, sensor, bateria, conectividad, seguridad, emocion, sistema';
COMMENT ON COLUMN centinela_alertas.severidad IS 'info, warning, error, critical';

-- =============================================================================
-- 6. centinela_eventos - Registro de eventos detectados
-- =============================================================================
CREATE TABLE IF NOT EXISTS centinela_eventos (
    id              BIGSERIAL PRIMARY KEY,
    tipo_evento     VARCHAR(64) NOT NULL,
    descripcion     TEXT,
    datos_json      JSONB,
    device_id       VARCHAR(64),
    ubicacion_id    BIGINT REFERENCES centinela_ubicacion(id),
    sensor_id       BIGINT REFERENCES centinela_sensores(id),
    health_id       BIGINT REFERENCES centinela_health(id),
    emocion_id      BIGINT REFERENCES centinela_emociones(id),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eventos_tipo ON centinela_eventos (tipo_evento);
CREATE INDEX IF NOT EXISTS idx_eventos_timestamp ON centinela_eventos (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_eventos_device ON centinela_eventos (device_id, timestamp DESC);

COMMENT ON TABLE centinela_eventos IS 'Registro de eventos detectados por el sistema centinela';
COMMENT ON COLUMN centinela_eventos.tipo_evento IS 'movimiento_brusco, caida_detectada, ubicacion_fija, sonido_fuerte, rostro_detectado, etc';

-- =============================================================================
-- 7. centinela_sesiones - Sesiones de monitoreo
-- =============================================================================
CREATE TABLE IF NOT EXISTS centinela_sesiones (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id       VARCHAR(64) NOT NULL,
    inicio          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fin             TIMESTAMPTZ,
    estado          VARCHAR(16) NOT NULL DEFAULT 'activa',
    sensores_activos JSONB,
    watch_conectado BOOLEAN DEFAULT FALSE,
    total_lecturas  BIGINT DEFAULT 0,
    ip_origen       INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sesiones_device ON centinela_sesiones (device_id, inicio DESC);
CREATE INDEX IF NOT EXISTS idx_sesiones_estado ON centinela_sesiones (estado) WHERE estado = 'activa';

COMMENT ON TABLE centinela_sesiones IS 'Sesiones de monitoreo activas del sistema centinela';

-- =============================================================================
-- FUNCIONES Y TRIGGERS
-- =============================================================================

-- Actualizar timestamp de created_at automáticamente
CREATE OR REPLACE FUNCTION update_created_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para alertas de salud crítica
CREATE OR REPLACE FUNCTION check_health_alert()
RETURNS TRIGGER AS $$
BEGIN
    -- Frecuencia cardíaca crítica
    IF NEW.heart_rate IS NOT NULL AND (NEW.heart_rate < 30 OR NEW.heart_rate > 220) THEN
        INSERT INTO centinela_alertas (tipo, severidad, mensaje, datos, device_id)
        VALUES (
            'salud', 'critical',
            'Frecuencia cardiaca critica: ' || NEW.heart_rate || ' bpm',
            jsonb_build_object('heart_rate', NEW.heart_rate, 'health_id', NEW.id),
            NEW.device_id
        );
    END IF;

    -- SpO2 crítico
    IF NEW.spo2 IS NOT NULL AND NEW.spo2 < 85 THEN
        INSERT INTO centinela_alertas (tipo, severidad, mensaje, datos, device_id)
        VALUES (
            'salud', 'critical',
            'Saturacion de oxigeno critica: ' || NEW.spo2 || '%',
            jsonb_build_object('spo2', NEW.spo2, 'health_id', NEW.id),
            NEW.device_id
        );
    END IF;

    -- Estrés crítico
    IF NEW.stress_level IS NOT NULL AND NEW.stress_level > 95 THEN
        INSERT INTO centinela_alertas (tipo, severidad, mensaje, datos, device_id)
        VALUES (
            'salud', 'warning',
            'Nivel de estres critico: ' || NEW.stress_level || '%',
            jsonb_build_object('stress_level', NEW.stress_level, 'health_id', NEW.id),
            NEW.device_id
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_health_alert
    AFTER INSERT ON centinela_health
    FOR EACH ROW
    EXECUTE FUNCTION check_health_alert();

-- Vista resumen de última hora
CREATE OR REPLACE VIEW centinela_resumen_hora AS
SELECT
    'sensores' AS tipo,
    COUNT(*) AS total,
    COUNT(DISTINCT tipo_sensor) AS tipos_unicos,
    MAX(timestamp) AS ultimo_registro
FROM centinela_sensores
WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT
    'ubicaciones',
    COUNT(*),
    1,
    MAX(timestamp)
FROM centinela_ubicacion
WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT
    'health',
    COUNT(*),
    COUNT(DISTINCT device_id),
    MAX(timestamp)
FROM centinela_health
WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT
    'emociones',
    COUNT(*),
    COUNT(DISTINCT emocion_detectada),
    MAX(timestamp)
FROM centinela_emociones
WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT
    'alertas_activas',
    COUNT(*),
    1,
    MAX(timestamp)
FROM centinela_alertas
WHERE resuelta = FALSE;

-- =============================================================================
-- PERMISOS
-- =============================================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nexus_master;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nexus_master;
