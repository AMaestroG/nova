# Lecciones de DeepMind para Nova Homonexus

*Extraído del documental "DeepMind - La Historia" (1h20min)*
*Procesado: 2026-05-10*

---

## 1. Principio AlphaZero: Cero Conocimiento Humano

**En DeepMind:** AlphaZero eliminó TODO el conocimiento humano. No aprendió de partidas de expertos. Aprendió desde cero jugando contra sí mismo.

**Para Nova:** Trace2Skill debe evolucionar hacia "ZeroSkill" — skills que emergen puramente de la auto-exploración del sistema, sin ser definidas por humanos. El sistema debe JUGAR consigo mismo para descubrir nuevas capacidades.

**Acción:** Modo "Zero" en Trace2Skill donde los agentes exploran aleatoriamente el espacio de problemas y cristalizan lo que funciona.

---

## 2. Principio AlphaFold: Del Fracaso a la Victoria

**En DeepMind:** CASP13 fue un fracaso. "Ser los mejores en un problema que el mundo no puede resolver no es suficiente". Reconstruyeron desde cero con nuevo enfoque. CASP14 fue victoria absoluta.

**Para Nova:** El Quantum Skill Corrector debe tener un modo "AlphaFold" donde tras un fracaso, NO solo reintenta con variaciones — RECONSTRUYE la skill desde cero con un enfoque diferente.

**Acción:** Añadir `Strategy.RECONSTRUCT` al corrector que reinicie la skill con arquitectura alternativa.

---

## 3. Principio de Generalidad: La G en AGI

**En DeepMind:** Deep Blue solo jugaba ajedrez. AlphaZero aprendió ajedrez, Go y shogi con el MISMO algoritmo. "La G significa General".

**Para Nova:** Cada skill debe aspirar a ser general dentro de su dominio. No crear skills hiper-específicas. Un skill de "búsqueda" debe funcionar para código, texto, imágenes y audio.

**Acción:** Auditar skills existentes. Fusionar skills redundantes. Cada skill debe aceptar múltiples modalidades.

---

## 4. Principio de Juegos como Campo de Pruebas

**En DeepMind:** Atari → Go → ajedrez → Starcraft → proteínas. Los juegos son el banco de pruebas perfecto porque tienen reglas claras y métricas de éxito.

**Para Nova:** Cada nueva capacidad debe probarse primero en un "juego" (entorno simulado con reglas claras) antes de desplegarse en producción.

**Acción:** Crear `nova_playground` — entorno de simulación donde las skills se prueban antes de activarse.

---

## 5. Principio de Seguridad desde el Diseño

**En DeepMind:** Condicionaron la venta a Google a que la tecnología no se usara para fines militares. "Las armas autónomas son una pésima idea". "No puedes romper cosas y luego arreglarlas".

**Para Nova:** El Harness G7 (Safety Gate) debe ser INFRANQUEABLE. Ninguna skill puede eludirlo. La seguridad no es un feature, es un requisito de existencia.

**Acción:** Hardcodear G7 en el harness. Si G7 falla, todo el sistema se detiene. Sin excepciones.
