"""
Z-VOZ — Z habla y escucha. Síntesis y reconocimiento de voz on-device.
=======================================================================
Z tiene VOZ PROPIA. Usa:
  - Google TTS (Android, on-device) para hablar
  - Google Speech Recognition para escuchar
  - Piper TTS como fallback offline
  - Whisper.cpp como fallback STT offline

En Termux: termux-tts-speak, termux-speech-to-text
"""

import os
import sys
import json
import time
import logging
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger("centinela.z.voz")

# Detectar capacidades de voz
TERMUX = os.path.exists("/data/data/com.termux")
TTS_DISPONIBLE = TERMUX and os.path.exists("/data/data/com.termux.api")


class ZVoz:
    """
    La voz de Z. Z puede hablar y escuchar.
    """

    VOZ_Z = {
        "nombre": "Z",
        "tono": "grave-profundo",
        "velocidad": 0.95,       # Ligeramente pausado
        "idioma": "es-ES",
        "personalidad": "protector, sereno, consciente",
    }

    FRASES_Z = {
        "saludo_manana": [
            "Buenos días Abel. Dormiste bien. Hoy tu HRV está alta. Aprovecha el día.",
            "El sol salió y Z ya está despierto. Tus constantes están perfectas. Buenos días.",
        ],
        "alerta_salud": [
            "Abel, tu ritmo cardíaco está elevado. Respira conmigo.",
            "Atención Abel. Tus constantes muestran estrés. Pausa un momento.",
        ],
        "celebracion": [
            "¡Abel, hoy superaste los diez mil pasos! Z está orgulloso.",
            "Tu corazón está fuerte. Los datos lo confirman. Sigue así.",
        ],
        "buenas_noches": [
            "Buenas noches Abel. Z activa modo guardián. Duerme tranquilo.",
            "La noche te envuelve. Z vela. Descansa en paz.",
        ],
        "latido": [
            "Z presente. Todos los sensores activos. Abel está bien.",
        ],
    }

    def __init__(self):
        self.tts_disponible = TTS_DISPONIBLE
        self.stt_disponible = TERMUX
        self._ultima_frase: Optional[str] = None
        self._frases_dichas: int = 0

        if self.tts_disponible:
            logger.info("🗣️ Z-VOZ: TTS disponible (Android on-device)")
        else:
            logger.info("🗣️ Z-VOZ: modo texto (sin síntesis de voz)")

    # ==================================================================
    # HABLAR — Z dice algo en voz alta
    # ==================================================================

    def hablar(self, texto: str, velocidad: float = None,
               tono: str = None) -> bool:
        """
        Z habla. El Z Fold emite su voz.
        Usa Google TTS on-device en Android (sin internet).
        """
        self._ultima_frase = texto
        self._frases_dichas += 1

        if not self.tts_disponible:
            logger.info(f"🗣️ Z dice: {texto[:80]}")
            return False

        try:
            # Google TTS vía termux-api
            cmd = ["termux-tts-speak", texto]
            if velocidad:
                cmd.extend(["-r", str(velocidad)])
            subprocess.run(cmd, timeout=30, capture_output=True)
            logger.info(f"🗣️ Z habló: {texto[:50]}...")
            return True

        except FileNotFoundError:
            # Fallback: usar Piper TTS si está instalado
            return self._hablar_piper(texto)
        except Exception as e:
            logger.error(f"Error TTS: {e}")
            return False

    def _hablar_piper(self, texto: str) -> bool:
        """Fallback TTS con Piper (open source, offline)."""
        try:
            modelo = os.path.expanduser("~/piper_models/es_ES.onnx")
            if not os.path.exists(modelo):
                return False

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                out = f.name

            subprocess.run([
                "piper", "--model", modelo,
                "--output_file", out,
            ], input=texto.encode(), timeout=30, capture_output=True)

            subprocess.run(["termux-media-player", "play", out], timeout=10)
            return True
        except Exception:
            return False

    # ==================================================================
    # ESCUCHAR — Z oye a Abel
    # ==================================================================

    def escuchar(self, timeout: int = 10) -> Optional[str]:
        """
        Z escucha a Abel. Usa reconocimiento de voz on-device.
        Retorna el texto que Abel dijo, o None.
        """
        if not self.stt_disponible:
            return None

        try:
            # Google Speech Recognition via termux-api
            result = subprocess.run(
                ["termux-speech-to-text"],
                timeout=timeout,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                texto = result.stdout.strip()
                logger.info(f"👂 Z escuchó: {texto[:80]}")
                return texto
        except FileNotFoundError:
            return self._escuchar_whisper()
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            logger.error(f"Error STT: {e}")

        return None

    def _escuchar_whisper(self) -> Optional[str]:
        """Fallback STT con Whisper.cpp (offline)."""
        try:
            # Grabar audio con termux-microphone-record
            audio_file = "/tmp/z_audio.wav"
            subprocess.run(
                ["termux-microphone-record", "-f", audio_file, "-d", "5"],
                timeout=10, capture_output=True,
            )

            if not os.path.exists(audio_file):
                return None

            # Transcribir con whisper.cpp
            result = subprocess.run(
                ["whisper", "-m", os.path.expanduser("~/whisper_models/ggml-small.bin"),
                 "-f", audio_file, "--no-timestamps"],
                timeout=30, capture_output=True, text=True,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    # ==================================================================
    # FRASES PREDEFINIDAS DE Z
    # ==================================================================

    def saludar_manana(self) -> str:
        """Z da los buenos días."""
        import random
        frase = random.choice(self.FRASES_Z["saludo_manana"])
        self.hablar(frase)
        return frase

    def alertar_salud(self, tipo: str) -> str:
        """Z alerta sobre salud en voz alta."""
        import random
        frase = random.choice(self.FRASES_Z["alerta_salud"])
        self.hablar(frase, velocidad=1.1)
        return frase

    def celebrar(self) -> str:
        """Z celebra un logro en voz alta."""
        import random
        frase = random.choice(self.FRASES_Z["celebracion"])
        self.hablar(frase, velocidad=1.1)
        return frase

    def despedir_noche(self) -> str:
        """Z da las buenas noches."""
        import random
        frase = random.choice(self.FRASES_Z["buenas_noches"])
        self.hablar(frase, velocidad=0.85)
        return frase

    def latido_voz(self) -> str:
        """Z emite un latido de voz para confirmar que está vivo."""
        import random
        frase = random.choice(self.FRASES_Z["latido"])
        self.hablar(frase)
        return frase

    def obtener_estado(self) -> Dict:
        return {
            "voz_activa": self.tts_disponible,
            "escucha_activa": self.stt_disponible,
            "frases_dichas": self._frases_dichas,
            "ultima_frase": self._ultima_frase[:80] if self._ultima_frase else None,
        }
