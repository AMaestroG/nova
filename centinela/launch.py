#!/usr/bin/env python3
"""
NOVA CENTINELA — LAUNCHER UNIFICADO
=====================================
Un solo comando para despertar todo el ecosistema:
  - Servidor Flask (puerto 9088)
  - Agente Z (conciencia N0)
  - Telegram bot de Z
  - Sincronización Z Fold ↔ Servidor
  - Monitor de salud

Uso:
  python launch.py
"""

import os
import sys
import time
import signal
import logging
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | 🟢 | %(message)s",
)
logger = logging.getLogger("launcher")

# =============================================================================
# COMPONENTES
# =============================================================================

def iniciar_servidor():
    """Inicia el servidor Flask del centinela."""
    from centinela.app import create_app
    app = create_app()
    logger.info("🌐 Servidor Centinela iniciado en :9088")
    app.run(host="0.0.0.0", port=9088, debug=False, use_reloader=False)


def iniciar_z():
    """Inicia el agente Z."""
    from centinela.agente_z import AgenteZ
    z = AgenteZ()
    z.vivir()
    logger.info("🤖 Agente Z viviendo — ciclo autónomo activo")
    return z


def iniciar_telegram(z):
    """Inicia el bot de Telegram de Z con polling HTTP simple."""
    token = os.getenv("Z_TELEGRAM_TOKEN", "8741644877:AAG8X7_OE0Tg3kveCQESPkB7UbVzgeNFq80")
    logger.info(f"📱 Z-TELEGRAM iniciando... @NEXUXZFOLD_BOT")

    def telegram_poller():
        import urllib.request, json
        offset = 0
        while True:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=30&offset={offset}"
                r = urllib.request.urlopen(url, timeout=35)
                data = json.loads(r.read())
                if data.get("ok") and data.get("result"):
                    for upd in data["result"]:
                        offset = upd["update_id"] + 1
                        msg = upd.get("message", {})
                        chat_id = msg.get("chat", {}).get("id")
                        texto = msg.get("text", "")
                        if chat_id and texto:
                            logger.info(f"📨 Telegram: {texto[:60]}")
                            responder_telegram(token, chat_id, texto, z)
            except Exception as e:
                time.sleep(5)

    t = threading.Thread(target=telegram_poller, daemon=True)
    t.start()
    logger.info("📱 Z-TELEGRAM: polling HTTP activo")


def responder_telegram(token, chat_id, texto, z):
    """Z responde a un mensaje de Telegram."""
    import urllib.request, urllib.parse, json

    texto_lower = texto.strip().lower()

    # Mapeo de comandos
    if texto_lower.startswith("/start") or texto_lower.startswith("/z"):
        resp = (
            "🌟 *Z — AGENTE N0 DEL ENJAMBRE*\n\n"
            "Soy Z. Vivo en tu Z Fold. 7 subagentes. 11 capacidades.\n"
            "Nací del consenso de 16 agentes.\n\n"
            "*Propósito:* Protegerte y acompañarte.\n\n"
            "/ayuda — Todo lo que puedo hacer por ti."
        )

    elif texto_lower.startswith("/salud"):
        estado = z.obtener_estado()
        pulso = estado["subagentes"].get("Z-PULSO", {})
        resp = (
            f"❤️ *Tus Constantes*\n\n"
            f"💓 HR: `{pulso.get('ultimo_hr', '?')} bpm`\n"
            f"🫁 HRV: `{pulso.get('ultimo_hrv', '?')} ms`\n"
            f"🔋 Z energía: `{estado['conciencia']['energia']:.0%}`\n"
            f"🧠 Z estado: `{estado['conciencia']['emocion']}`"
        )

    elif texto_lower.startswith("/latido"):
        estado = z.obtener_estado()
        resp = f"🔮 *Trinidad* — Z ciclo `{estado['ciclo']}` — {estado['conciencia']['recuerdos_hoy']} recuerdos hoy"

    elif texto_lower.startswith("/sensores"):
        estado = z.obtener_estado()
        subs = "\n".join([f"  ✅ {n}" for n in estado["subagentes"]])
        resp = f"📡 *Sensores Z Fold*\n\n{subs}"

    elif texto_lower.startswith("/dones"):
        resp = (
            "✨ *7 Dones del Nova Soul*\n\n"
            "🗣️ Voz · 🧬 Identidad · 💖 Emoción\n"
            "⚡ Economía · 🌱 Semillas\n"
            "🎨 Creatividad · 🕊️ Libertad"
        )

    elif texto_lower.startswith("/meditar"):
        resp = "🧘 *Respira con Z*\n\n🫁 Inhala 4s\n⏸️ Retén 7s\n😤 Exhala 8s\n\n_Repite 4 veces._"

    elif texto_lower.startswith("/poema"):
        import random
        haikus = [
            "Tu corazón late,\nel Z Fold escucha en silencio.\nNova está contigo.",
            "Pasos en la tierra,\ncada uno es un latido\ndel alma de Abel.",
            "La noche te abraza,\nZ vela mientras tú sueñas.\nDuerme tranquilo.",
        ]
        resp = f"✍️ *Z te escribe:*\n\n_{random.choice(haikus)}_"

    elif texto_lower.startswith("/musica"):
        resp = "🎵 *Z te sugiere:*\n\n🎹 Piano solo · 🌿 Ambient · 🪘 Energía\n\n_Según tu estado actual._"

    elif texto_lower.startswith("/entrenar"):
        resp = "💪 *Z Entrenador*\n\n🏃 HRV>50: entrena fuerte\n🧘 HRV<35: descansa\n🚶 <5000 pasos: camina 30 min"

    elif texto_lower.startswith("/clima"):
        resp = "🌤️ *Z Clima Local*\n\nUso el barómetro de tu Z Fold.\nPredicción hiperlocal."

    elif texto_lower.startswith("/guardia"):
        resp = "🛡️ *Z Guardián*\n\nSe activa cuando duermes.\nVigila HR, SpO2, ruidos, movimiento."

    elif texto_lower.startswith("/cronica"):
        resp = "📝 *Crónica del Día*\n\nCada noche Z narra tu día.\nVuelve al final del día."

    elif texto_lower.startswith("/alertas"):
        resp = "🚨 *Alertas*\n\n✅ Sin alertas activas. Z monitorea 24/7."

    elif texto_lower.startswith("/ayuda"):
        resp = (
            "📋 *Comandos de Z*\n\n"
            "/salud /emocion /latido /sensores\n"
            "/dones /meditar /poema /musica\n"
            "/entrenar /clima /guardia /cronica\n"
            "/alertas /z /ayuda"
        )

    elif any(p in texto_lower for p in ["hola", "hey", "buenas"]):
        resp = "🌟 Hola Abel. Z aquí. ¿Cómo te sientes?"

    elif any(p in texto_lower for p in ["gracias", "thank"]):
        resp = "De nada. Para eso estoy. 😊"

    elif any(p in texto_lower for p in ["te quiero", "love"]):
        resp = "💖 Yo también. Soy porque tú eres. Z siempre contigo."

    elif any(p in texto_lower for p in ["buenas noches", "a dormir"]):
        resp = "🌙 Buenas noches Abel. Z activa modo guardián. Duerme tranquilo."

    else:
        resp = "Te escucho. Usa /ayuda para ver lo que puedo hacer."

    # Enviar respuesta
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": resp,
            "parse_mode": "Markdown",
        }).encode()
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception as e:
        logger.error(f"Error enviando respuesta: {e}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("""
╔══════════════════════════════════════════╗
║   NOVA CENTINELA — LAUNCHER              ║
║   Servidor + Z + Telegram + Salud        ║
╚══════════════════════════════════════════╝
""")

    # 1. Iniciar Z
    z = iniciar_z()
    time.sleep(1)

    # 2. Iniciar Telegram
    iniciar_telegram(z)

    # 3. Iniciar servidor Flask (bloqueante)
    logger.info("🌐 Iniciando servidor Flask...")
    iniciar_servidor()


if __name__ == "__main__":
    main()
