"""CasaControl — LLM interactions via Groq API."""

import json
import re
import base64
import logging
from datetime import date

import httpx

from config import (
    GROQ_API_KEY, GROQ_API_URL, GROQ_AUDIO_URL,
    GROQ_MODEL, GROQ_VISION_MODEL, GROQ_WHISPER_MODEL,
    CATEGORY_SLUGS,
)

logger = logging.getLogger("casacontrol.llm")


async def call_llm(user_content: str, system: str, max_tokens: int = 1024) -> str:
    payload = {
        "model": GROQ_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if r.status_code != 200:
            logger.error("Groq API error %s: %s", r.status_code, r.text)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]


def _parse_json(response: str) -> dict:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON: {response}")


async def classify_and_process(text: str) -> dict:
    """Classify user message intent and extract data accordingly.

    Returns dict with:
      - intent: "expense" | "query" | "off_topic"
      - For expense: data dict with description, amount_eur, etc.
      - For query/off_topic: response string
    """
    system = f"""You are CasaControl, a family expense assistant for Martin and Romina in Madrid.
Classify the user message into one of three intents and respond with ONLY valid JSON (no markdown, no extra text):

1. EXPENSE — the message describes a purchase or expense.
   Return: {{"intent": "expense", "data": {{
     "description": "short expense name",
     "amount_eur": number or null,
     "category_slug": "one of: {', '.join(CATEGORY_SLUGS)}",
     "store": "string or null",
     "payment_method": "string or null",
     "date": "YYYY-MM-DD, today ({date.today().isoformat()}) if not mentioned"
   }}}}

2. ANYTHING ELSE — any question, comment, or conversation (about finances, general knowledge, weather, whatever).
   You are a helpful assistant that can talk about any topic. Always respond in Spanish with a natural, friendly tone.
   Return: {{"intent": "query", "response": "your helpful answer in Spanish"}}

Context clues for categories: alquiler→vivienda, luz/gas/internet/móvil→servicios, médico/farmacia/mapfre→salud,
mercadona/aldi/lidl/costco/frutería/makro→super, restaurante/bar/cafetería→salidas,
taxi/uber/metro/bus→transporte, cole/guardería→educacion, ropa/zapatos→ropa."""

    response = await call_llm(text, system=system)
    return _parse_json(response)


async def extract_expense_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    b64 = base64.standard_b64encode(image_bytes).decode()

    system = f"""You are the ticket OCR parser for CasaControl, a family budget app in Madrid.
Analyse the receipt image and extract all relevant expense data.
Return ONLY valid JSON (no markdown) with:
  description    (string — store name + brief summary, e.g. "Mercadona — compra semanal")
  amount_eur     (number — final total on the ticket)
  category_slug  (one of: {', '.join(CATEGORY_SLUGS)})
  store          (string — store name)
  payment_method (string or null)
  date           (YYYY-MM-DD from the ticket, or today {date.today().isoformat()} if not visible)
  items          (array of {{name, quantity, unit_price, total_price}} — line items if legible, else [])"""

    payload = {
        "model": GROQ_VISION_MODEL,
        "max_tokens": 2048,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                    {"type": "text", "text": "Extrae los datos de este ticket de compra."},
                ],
            },
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if r.status_code != 200:
            logger.error("Groq vision API error %s: %s", r.status_code, r.text)
        r.raise_for_status()
        data = r.json()
        response = data["choices"][0]["message"]["content"]

    return _parse_json(response)


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """Transcribe audio using Groq Whisper API."""
    ext = "ogg" if "ogg" in mime_type else "mp3"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            GROQ_AUDIO_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            data={"model": GROQ_WHISPER_MODEL, "language": "es"},
            files={"file": (f"audio.{ext}", audio_bytes, mime_type)},
        )
        if r.status_code != 200:
            logger.error("Groq Whisper error %s: %s", r.status_code, r.text)
        r.raise_for_status()
        return r.json()["text"]
