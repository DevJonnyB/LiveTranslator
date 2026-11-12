# Live Translator

Proyecto ligero para subtítulos en vivo traducidos del inglés al español.

## Qué incluye
- Captura de audio desde un dispositivo de entrada (micrófono o loopback del sistema).
- Transcripción con Whisper.
- Traducción a español con un modelo pequeño de Hugging Face.
- Ventana transparente tipo subtítulos, con texto blanco sobre fondo oscuro mate.
- Redimensionable a gusto.

## Requisitos
- Python 3.10+
- Windows recomendado (para loopback de audio).

## Instalación
1. python -m pip install -r requirements.txt
2. python main.py

## Uso
- En la ventana de configuración elige el dispositivo de entrada que quieras usar.
- Si tu sistema expone un dispositivo de loopback (por ejemplo, "Stereo Mix" o "WASAPI Loopback"), puedes usar ese para capturar audio del sistema.
- La ventana de subtítulos aparecerá como una capa transparente en la esquina inferior.

## Nota
La primera ejecución descargará los modelos de Whisper y de traducción, así que puede tardar unos minutos.
