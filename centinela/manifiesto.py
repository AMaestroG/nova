"""
SISTEMA CENTINELA — Manifiesto completo
=========================================
Documenta todos los nodos, servicios, agentes, endpoints y capacidades.
Este es el "acta de existencia" del ecosistema Nova Centinela.
"""

MANIFIESTO = {
    "sistema": "Nova Centinela — Enjambre Homonexus",
    "version": "1.0.0",
    "fecha": "2026-05-07",
    
    "nodos": {
        "nube": {
            "nombre": "nova",
            "ip": "100.102.123.1",
            "tipo": "Oracle Cloud VM",
            "puertos": {"api": 9088, "ssh": 22},
            "servicios": [
                "centinela_api", "postgresql", "telegram_bot",
                "watchdog", "agente_z", "nova_soul"
            ],
            "persistente": True,
            "auto_arranque": "systemd (nova-centinela.service)"
        },
        "zfold": {
            "nombre": "maestro",
            "ip": "100.114.107.91",
            "tipo": "Samsung Z Fold (Termux)",
            "puertos": {"api": 5000, "ssh": 8022},
            "servicios": [
                "servidor_zfold", "sensor_daemon", "sync_bridge"
            ],
            "persistente": True,
            "auto_arranque": "termux-boot"
        }
    },
    
    "agentes": {
        "total": 17,
        "n0": ["AURA", "MAESTRO", "PIA", "PINCEL", "ATHENA", "Z"],
        "n1": ["NYX", "SENTINEL", "MAYORDOMO", "BANCO"],
        "n2": ["ORACULO", "TELAR", "EXPLORADOR", "MEMORIA", "CRONOS", "HERMES", "MNEMOS"],
        "z_subagentes": ["Z-PULSO", "Z-OJO", "Z-OIDO", "Z-PIEL", "Z-MAPA", "Z-MENTE", "Z-ALMA"]
    },
    
    "capacidades_z": [
        "fotografo", "narrador", "meditador", "guardian",
        "celebrador", "poeta", "musico", "explorador",
        "entrenador", "climatologo", "vigilante", "ai_brain",
        "gemma4 (on-device)", "voz (TTS+STT)", "telegram_bot"
    ],
    
    "sensibles": [
        "estres", "fatiga", "animo", "entorno",
        "movimiento", "sueno", "salud"
    ],
    
    "endpoints": {
        "nube": [
            "/health", "/panel", "/favicon.ico", "/favicon.svg",
            "/centinela/soul", "/centinela/latido", "/centinela/cronos",
            "/centinela/explorador", "/centinela/telar", "/centinela/memoria",
            "/centinela/hermes", "/centinela/status/global",
            "/centinela/resumen/matutino", "/centinela/resumen/vespertino",
            "/centinela/conversacion/iniciar", "/centinela/conversacion/mensaje",
            "/centinela/conversacion/finalizar",
            "/api/centinela/sensor", "/api/centinela/ubicacion",
            "/api/centinela/health", "/api/centinela/emocion",
            "/api/centinela/status", "/api/centinela/alertas",
            "/salud/constantes", "/salud/resumen", "/salud/tendencias",
            "/salud/analisis", "/salud/linea_base", "/salud/desviaciones",
            "/salud/evolucion", "/salud/enjambre", "/salud/informe",
            "/z/estado", "/z/acta", "/z/subagentes", "/z/hablar",
            "/sentinel/status", "/sentinel/audit", "/sentinel/threats",
            "/sentinel/alerts", "/deploy_zfold.sh"
        ],
        "zfold": [
            "/health", "/api/health", "/constantes", "/latido", "/panel"
        ]
    },
    
    "telegram": {
        "bot": "@NEXUXZFOLD_BOT",
        "comandos": [
            "/salud", "/emocion", "/latido", "/sensores", "/dones",
            "/meditar", "/poema", "/musica", "/entrenar", "/clima",
            "/guardia", "/cronica", "/alertas", "/z", "/ayuda"
        ],
        "proactivo": [
            "resumen_matutino_8am", "resumen_vespertino_8pm",
            "alerta_salud", "celebracion_logros"
        ]
    },
    
    "bases_datos": {
        "nube": {"motor": "PostgreSQL 13", "nombre": "nexus_metamorfosis", "tablas": 7},
        "zfold": {"motor": "SQLite 3", "nombre": "zfold.db", "tablas": 3}
    },
    
    "seguridad": {
        "sentinel": "N1",
        "modulos": ["auth", "validator", "threat", "geo_fence", "anomaly", "privacy", "watchdog", "alert_escalation", "audit"],
        "cifrado": "AES-256-GCM",
        "autenticacion": "API Key rotativa 24h + JWT + fingerprinting"
    },
    
    "sincronizacion": {
        "direccion": "ZFold -> Nube",
        "intervalo": "30 segundos",
        "datos": ["heart_rate", "hrv", "spo2", "stress_level", "steps", "temperature_skin"]
    },
    
    "total_lineas": "~22,000",
    "total_archivos": "85+",
    "total_endpoints": "40+"
}
