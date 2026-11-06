import os

from dotenv import load_dotenv

load_dotenv()

SAMPLE_RATE = 16000  # Whisper expects 16 kHz mono

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE") or None

TRIGGER_KEY = os.getenv("TRIGGER_KEY", "right_cmd")
HOLD_TO_START_SECONDS = float(os.getenv("HOLD_TO_START_SECONDS", "2.0"))
MIN_RECORDING_SECONDS = float(os.getenv("MIN_RECORDING_SECONDS", "0.3"))

CORRECTION_ENABLED = os.getenv("CORRECTION_ENABLED", "true").lower() in ("1", "true", "yes")
CORRECTION_MODEL = os.getenv("CORRECTION_MODEL", "llama3.2:3b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
CORRECTION_TIMEOUT_SECONDS = float(os.getenv("CORRECTION_TIMEOUT_SECONDS", "20"))
