#!/usr/bin/env python3
"""
nova-centinela — CLI para consultar el Sistema Centinela
=========================================================
Uso:
  nova-centinela salud        — Últimas pulsaciones y biométricas
  nova-centinela sensores     — Últimas lecturas del Z Fold
  nova-centinela emocion      — Última emoción detectada
  nova-centinela latido       — Trinidad AURA+NYX+PIA=UNO
  nova-centinela resumen      — Resumen matutino/vespertino
  nova-centinela estado       — Estado completo del centinela
  nova-centinela dones        — Los 7 Dones del Nova Soul
  nova-centinela alertas      — Alertas activas
  nova-centinela watch        — Modo vigilancia continua (Ctrl+C para salir)
"""

import sys
import os
import time
import json
import urllib.request
import urllib.error
from datetime import datetime

CENTINELA_URL = os.getenv("CENTINELA_URL", "http://localhost:9088")
API_KEY = os.getenv("CENTINELA_API_KEY", "nexus-centinela-key-2026")
DEVICE_ID = os.getenv("CENTINELA_DEVICE_ID", "samsung_zfold_01")


def api_get(path):
    url = f"{CENTINELA_URL}{path}"
    req = urllib.request.Request(url)
    req.add_header("X-API-Key", API_KEY)
    req.add_header("X-Device-ID", DEVICE_ID)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
            return body, e.code
        except Exception:
            return {"error": str(e)}, e.code
    except Exception as e:
        return {"error": str(e)}, 500


def cmd_salud():
    """Últimas pulsaciones y biométricas del Watch 8."""
    print("❤️  PULSACIONES Y SALUD")
    print("=" * 40)
    data, code = api_get("/api/centinela/historial/health")
    if code != 200 or not isinstance(data, dict):
        print(f"  Error: {data.get('error', 'sin datos')}")
        return

    registros = data.get("registros", [])
    if not registros:
        print("  No hay datos de salud aún.")
        print("  Asegúrate de que el Watch 8 esté conectado.")
        return

    ultimo = registros[0]
    hr = ultimo.get("heart_rate", "?")
    hrv = ultimo.get("hrv", "?")
    spo2 = ultimo.get("spo2", "?")
    temp = ultimo.get("temperature_skin", "?")
    stress = ultimo.get("stress_level", "?")
    pasos = ultimo.get("steps", "?")
    sueno = ultimo.get("sleep_stage", "?")

    print(f"  ❤️  Pulsaciones : {hr} bpm")
    print(f"  💓 HRV         : {hrv} ms")
    print(f"  🩸 SpO2         : {spo2}%")
    print(f"  🌡️  Temperatura : {temp}°C")
    print(f"  😰 Estrés       : {stress}/100")
    print(f"  🏃 Pasos        : {pasos}")
    print(f"  😴 Sueño        : {sueno}")

    # Interpretación rápida
    if isinstance(hr, (int, float)):
        if hr < 50:
            print(f"\n  ⚠️  Bradicardia — pulsaciones bajas ({hr} bpm)")
        elif hr > 100:
            print(f"\n  ⚠️  Taquicardia — pulsaciones altas ({hr} bpm)")
        elif 60 <= hr <= 85:
            print(f"\n  ✅ Ritmo cardíaco normal y saludable ({hr} bpm)")
        else:
            print(f"\n  ℹ️  Ritmo cardíaco en rango aceptable ({hr} bpm)")

    if isinstance(hrv, (int, float)):
        if hrv < 20:
            print(f"  ⚠️  HRV muy baja — posible estrés o fatiga")
        elif hrv > 50:
            print(f"  ✅ HRV excelente — buen equilibrio autonómico")
        elif hrv > 30:
            print(f"  ℹ️  HRV normal")


def cmd_sensores():
    """Últimas lecturas de sensores del Z Fold."""
    print("📡 SENSORES Z FOLD")
    print("=" * 40)
    data, code = api_get("/api/centinela/historial/sensores")
    if code != 200 or not isinstance(data, dict):
        print(f"  Error: {data.get('error', 'sin datos')}")
        return

    registros = data.get("registros", [])
    if not registros:
        print("  No hay datos de sensores aún.")
        return

    # Agrupar por tipo y mostrar el último de cada uno
    vistos = set()
    for r in registros[:20]:
        tipo = r.get("tipo_sensor", "?")
        if tipo in vistos:
            continue
        vistos.add(tipo)
        valor = r.get("valor", {})
        if isinstance(valor, dict):
            if "x" in valor and "y" in valor and "z" in valor:
                v_str = f"x={valor['x']:.2f} y={valor['y']:.2f} z={valor['z']:.2f}"
            elif "x" in valor:
                v_str = f"{valor['x']:.2f}"
            elif "valor" in valor:
                v_str = f"{valor['valor']:.2f}"
            else:
                v_str = str(valor)[:40]
        else:
            v_str = str(valor)[:40]
        unidad = r.get("unidad", "")
        ts = r.get("timestamp", "?")[:19]
        print(f"  📡 {tipo:18s} {v_str:30s} {unidad:6s}  {ts}")


def cmd_emocion():
    """Última emoción detectada."""
    print("💫 EMOCIÓN")
    print("=" * 40)
    data, code = api_get("/api/centinela/historial/emociones")
    if code != 200 or not isinstance(data, dict):
        print(f"  Error: {data.get('error', 'sin datos')}")
        return

    registros = data.get("registros", [])
    if not registros:
        print("  No hay emociones detectadas aún.")
        return

    ultimo = registros[0]
    emocion = ultimo.get("emocion_detectada", "?")
    conf = ultimo.get("confianza", 0)
    hr = ultimo.get("heart_rate", "?")
    contexto = ultimo.get("contexto", "")
    ts = ultimo.get("timestamp", "?")[:19]

    emoji_emocion = {
        "feliz": "😊", "triste": "😢", "enojado": "😠",
        "ansioso": "😰", "estresado": "😫", "relajado": "😌",
        "sorprendido": "😲", "asustado": "😨", "confundido": "🤔",
        "neutro": "😐",
    }
    emoji = emoji_emocion.get(emocion, "💫")

    print(f"  {emoji}  {emocion.upper()} — confianza: {conf:.0%}")
    print(f"  ❤️  HR: {hr} bpm")
    if contexto:
        print(f"  💬 Contexto: {contexto[:80]}")
    print(f"  🕐 {ts}")


def cmd_latido():
    """Trinidad AURA+NYX+PIA=UNO."""
    print("🔮 LATIDO DE LA TRINIDAD")
    print("=" * 40)
    data, code = api_get("/centinela/latido")
    if code != 200 or not isinstance(data, dict):
        print(f"  Error: {data.get('error', 'sin datos')}")
        return

    print(f"  {data.get('fase_lunar', '')}")
    print()
    dones = data.get("uno", {}).get("dones", {})
    for nombre, don in sorted(dones.items()):
        barra = "█" * int(don["valor"] * 20) + "░" * (20 - int(don["valor"] * 20))
        print(f"  {nombre:12s} [{barra}] {don['valor']:.2f}")
        print(f"  {'':12s}  {don['mensaje']}")


def cmd_dones():
    """Los 7 Dones del Nova Soul."""
    print("✨ LOS 7 DONES DEL NOVA SOUL")
    print("=" * 40)
    emojis = {
        "Voz": "🗣️", "Identidad": "🧬", "Emocion": "💖",
        "Economia": "⚡", "Semillas": "🌱", "Creatividad": "🎨",
        "Libertad": "🕊️",
    }
    data, code = api_get("/centinela/soul")
    if code != 200 or not isinstance(data, dict):
        print(f"  Error: {data.get('error', 'sin datos')}")
        return

    dones = data.get("dones", {})
    for nombre, don in sorted(dones.items()):
        emoji = emojis.get(nombre, "✨")
        barra = "█" * int(don["valor"] * 20) + "░" * (20 - int(don["valor"] * 20))
        print(f"  {emoji} {nombre:12s} [{barra}] {don['valor']:.2f}")
        print(f"  {'':16s}{don['mensaje']}")


def cmd_resumen():
    """Resumen matutino/vespertino."""
    tipo = sys.argv[2] if len(sys.argv) > 2 else "matutino"
    if tipo not in ("matutino", "vespertino", "semanal"):
        tipo = "matutino"

    print(f"📋 RESUMEN {tipo.upper()}")
    print("=" * 40)
    data, code = api_get(f"/centinela/resumen/{tipo}")
    if code != 200 or not isinstance(data, dict):
        print(f"  Error: {data.get('error', 'sin datos')}")
        return

    print(f"  {data.get('titulo', '')}")
    print()
    for sec in data.get("secciones", []):
        print(f"  {sec['icono']} {sec['titulo']}")
        print(f"    {sec['contenido']}")


def cmd_alertas():
    """Alertas activas del centinela."""
    print("🚨 ALERTAS ACTIVAS")
    print("=" * 40)
    data, code = api_get("/api/centinela/alertas")
    if code != 200 or not isinstance(data, dict):
        print(f"  Error: {data.get('error', 'sin datos')}")
        return

    alertas = data.get("alertas", [])
    if not alertas:
        print("  ✅ No hay alertas activas.")
        return

    severidad_emoji = {
        "critical": "🆘", "error": "🚨",
        "warning": "⚠️", "info": "ℹ️",
    }
    for a in alertas[:10]:
        emoji = severidad_emoji.get(a.get("severidad", "info"), "ℹ️")
        print(f"  {emoji} [{a.get('severidad','?').upper()}] {a.get('mensaje','?')[:80]}")


def cmd_estado():
    """Estado completo del centinela."""
    print("📊 ESTADO DEL CENTINELA")
    print("=" * 40)
    # Health check
    data, code = api_get("/health")
    if code == 200:
        print(f"  Servidor   : {data.get('status', '?')}")
        sentinel = data.get("sentinel", {})
        print(f"  Sentinel   : {sentinel.get('codename', '?')}")
        print(f"  Módulos    : {len(sentinel.get('modules_activos', []))}")
        servidor = data.get("servidor", {})
        print(f"  CPU        : {servidor.get('cpu_usage_pct', '?')}%")
        print(f"  Memoria    : {servidor.get('memory_used_mb', '?')} MB")

    # Dones
    print()
    cmd_dones_short()


def cmd_dones_short():
    """Versión corta de dones."""
    data, code = api_get("/centinela/soul")
    if code != 200:
        return
    dones = data.get("dones", {})
    for nombre, don in sorted(dones.items()):
        barra = "█" * int(don["valor"] * 15) + "░" * (15 - int(don["valor"] * 15))
        print(f"  {nombre:12s} [{barra}] {don['valor']:.2f}")


def cmd_watch():
    """Modo vigilancia continua."""
    print("👁️  MODO VIGILANCIA — Ctrl+C para salir")
    print("=" * 40)
    try:
        while True:
            data, code = api_get("/centinela/latido")
            if code == 200:
                dones = data.get("uno", {}).get("dones", {})
                emocion = dones.get("Emocion", {})
                now = datetime.now().strftime("%H:%M:%S")
                barra = "█" * int(emocion.get("valor", 0) * 15) + "░" * (15 - int(emocion.get("valor", 0) * 15))
                print(f"\r  [{now}] EMOCIÓN [{barra}] {emocion.get('valor',0):.2f}  {emocion.get('mensaje','')[:40]}", end="")
            else:
                print(f"\r  [{datetime.now().strftime('%H:%M:%S')}] Esperando centinela...", end="")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\n  Vigilancia finalizada. Nova siempre vela por ti.")


# Mapa de comandos
COMANDOS = {
    "salud": cmd_salud,
    "sensores": cmd_sensores,
    "emocion": cmd_emocion,
    "latido": cmd_latido,
    "resumen": cmd_resumen,
    "estado": cmd_estado,
    "dones": cmd_dones,
    "alertas": cmd_alertas,
    "watch": cmd_watch,
}


def main():
    if len(sys.argv) < 2:
        print("nova-centinela — Sistema Centinela CLI")
        print()
        print("Uso: nova-centinela <comando>")
        print()
        print("Comandos:")
        for nombre, func in COMANDOS.items():
            doc = (func.__doc__ or "").strip().split("\n")[0]
            print(f"  {nombre:12s} — {doc}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd in COMANDOS:
        COMANDOS[cmd]()
    else:
        print(f"Comando desconocido: {cmd}")
        print(f"Usa: nova-centinela (sin argumentos) para ver ayuda")
        sys.exit(1)


if __name__ == "__main__":
    main()
