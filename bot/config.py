"""CasaControl — Configuration and constants."""

import os

# ── Environment variables ─────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ALLOWED_CHAT_IDS = set(
    int(x) for x in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip()
)
GROUP_CHAT_ID = int(os.environ.get("GROUP_CHAT_ID", "0")) or None

# ── Category slugs ────────────────────────────────────────────────────────────
CATEGORY_SLUGS = [
    "vivienda", "super", "salud", "servicios", "vacaciones",
    "salidas", "casa", "transporte", "ocio", "ropa", "educacion",
    "otros", "impuestos", "deportes", "coche", "sin_clasificar",
]

CATEGORY_LABELS = {
    "vivienda":       "🏡 Vivienda",
    "super":          "🛒 Supermercado",
    "salud":          "🏥 Salud",
    "servicios":      "💡 Servicios",
    "vacaciones":     "✈️ Vacaciones",
    "salidas":        "🍽️ Salidas",
    "casa":           "🏠 Casa/Hogar",
    "transporte":     "🚇 Transporte",
    "ocio":           "🎈 Ocio/Kids",
    "ropa":           "👗 Ropa",
    "educacion":      "📚 Educación",
    "otros":          "📦 Otros",
    "impuestos":      "🏛️ Impuestos",
    "deportes":       "🏋️ Deportes",
    "coche":          "🚘 Coche",
    "sin_clasificar": "❓ Sin clasificar",
}

# ── Groq settings ─────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
