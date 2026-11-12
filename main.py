import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from translatepy import Translator


MODEL_NAME = "base"
SAMPLE_RATE = 16000
CHUNK_SECONDS = 1.5


class TranslatorApp:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.running = False
        self.stream = None
        self.whisper_model = None
        self.translator = None
        self.current_device = None
        self.current_label = ""

        self.root = tk.Tk()
        self.root.title("Live Translator")
        self.root.geometry("460x280")
        self.root.resizable(False, False)

        tk.Label(self.root, text="Dispositivo de entrada", anchor="w").pack(fill="x", padx=12, pady=(10, 2))
        self.device_var = tk.StringVar(value="")
        self.device_combo = ttk.Combobox(self.root, textvariable=self.device_var, state="readonly")
        self.device_combo.pack(fill="x", padx=12)

        tk.Label(self.root, text="Dirección de traducción", anchor="w").pack(fill="x", padx=12, pady=(10, 2))
        self.direction_var = tk.StringVar(value="en-es")
        self.direction_combo = ttk.Combobox(self.root, textvariable=self.direction_var, state="readonly", values=["en-es", "es-en"])
        self.direction_combo.pack(fill="x", padx=12)

        tk.Label(self.root, text="(Puedes elegir un micrófono o un loopback del sistema si tu sistema lo expone)", justify="left").pack(fill="x", padx=12, pady=(4, 0))

        self.status_var = tk.StringVar(value="Listo para iniciar")
        tk.Label(self.root, textvariable=self.status_var, fg="#1f5a1f", justify="left").pack(fill="x", padx=12, pady=(8, 0))

        ttk.Button(self.root, text="Iniciar subtítulos", command=self.start).pack(pady=(10, 6))
        ttk.Button(self.root, text="Detener", command=self.stop).pack()

        self.subtitle_window = None

        self._load_models()
        self._populate_devices()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _load_models(self):
        try:
            self.status_var.set("Cargando modelo Whisper…")
            self.root.update_idletasks()
            self.whisper_model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
        except Exception as exc:
            self.status_var.set(f"No se pudo cargar Whisper: {exc}")
            self.whisper_model = None
            return

        try:
            self.status_var.set("Cargando traductor…")
            self.root.update_idletasks()
            self.translator = Translator()
        except Exception as exc:
            self.status_var.set(f"No se pudo cargar traductor: {exc}")
            self.translator = None

        if self.whisper_model is not None:
            self.status_var.set("Listo para iniciar")

    def _populate_devices(self):
        devices = sd.query_devices()
        labels = []
        for index, device in enumerate(devices):
            if device.get("max_input_channels", 0) > 0:
                labels.append(f"{index}: {device['name']}")
        self.device_combo['values'] = labels
        if labels:
            self.device_combo.current(0)

    def _device_index_from_label(self, label):
        return int(label.split(":", 1)[0])

    def start(self):
        if self.running:
            return

        if not self.device_var.get():
            self.status_var.set("Selecciona un dispositivo de entrada primero")
            return

        if self.whisper_model is None:
            self.status_var.set("Whisper no está disponible. Revisa la instalación.")
            return

        index = self._device_index_from_label(self.device_var.get())
        device = sd.query_devices(index)
        self.current_label = device["name"]

        self.status_var.set(f"Capturando desde: {self.current_label}")
        self.root.update_idletasks()

        self.running = True
        self._start_subtitle_window()

        try:
            self.stream = sd.InputStream(
                device=index,
                channels=1,
                samplerate=SAMPLE_RATE,
                blocksize=int(SAMPLE_RATE * CHUNK_SECONDS),
                dtype="int16",
                callback=self._audio_callback,
            )
            self.stream.start()
        except Exception as exc:
            self.running = False
            self.status_var.set(f"No se pudo abrir el dispositivo: {exc}")
            return

        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def _start_subtitle_window(self):
        if self.subtitle_window is not None:
            return

        self.subtitle_window = tk.Toplevel(self.root)
        self.subtitle_window.overrideredirect(True)
        self.subtitle_window.attributes("-topmost", True)
        self.subtitle_window.attributes("-alpha", 0.88)
        self.subtitle_window.configure(bg="#111111")

        self.subtitle_window.geometry("640x110+40+40")
        self.subtitle_window.resizable(True, True)

        self.subtitle_label = tk.Label(self.subtitle_window, text="", fg="white", bg="#111111", font=("Segoe UI", 26, "bold"), wraplength=620, justify="center")
        self.subtitle_label.pack(expand=True, fill="both", padx=18, pady=12)

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(status)
        audio = np.frombuffer(indata, dtype=np.int16).astype(np.float32) / 32768.0
        self.audio_queue.put(audio)

    def _worker_loop(self):
        buffer = []
        last_process = time.time()
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.2)
                buffer.append(chunk)
                if time.time() - last_process >= CHUNK_SECONDS:
                    self._process_buffer(buffer)
                    buffer = []
                    last_process = time.time()
            except queue.Empty:
                pass

        if buffer:
            self._process_buffer(buffer)

    def _process_buffer(self, buffer):
        if not buffer:
            return

        audio = np.concatenate(buffer, axis=0).astype(np.float32)
        if audio.shape[0] < SAMPLE_RATE * 0.2:
            return

        try:
            source_lang = "en" if self.direction_var.get() == "en-es" else "es"
            segments, _ = self.whisper_model.transcribe(audio, language=source_lang, beam_size=1)
            text = " ".join(seg.text for seg in segments).strip()
            if text:
                translated = text
                if self.translator is not None:
                    translated = self.translator.translate_text(text, target_language="es" if self.direction_var.get() == "en-es" else "en")
                    translated = getattr(translated, "result", None) or str(translated)
                self._update_subtitles(translated)
        except Exception as exc:
            self.status_var.set(f"Error de audio: {exc}")

    def _update_subtitles(self, translation):
        if self.subtitle_window is None:
            return
        self.subtitle_label.config(text=translation)
        self.subtitle_window.title("Subtítulos en vivo")

    def stop(self):
        self.running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.status_var.set("Detenido")
        if self.subtitle_window is not None:
            self.subtitle_window.destroy()
            self.subtitle_window = None

    def on_close(self):
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    app = TranslatorApp()
    app.root.mainloop()
