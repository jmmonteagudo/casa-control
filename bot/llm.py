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
    system = f"""You are CasaControl, a family expense assistant.
Classify the user message into one of three intents and respond with ONLY valid JSON (no markdown, no extra text):

1. EXPENSE — the message describes a purchase, payment, or expense.
   Return: {{"intent": "expense", "data": {{
     "description": "short expense name",
     "amount_eur": number or null,
     "category_slug": "one of: {', '.join(CATEGORY_SLUGS)}",
     "store": "string or null",
     "payment_method": "string or null",
     "date": "YYYY-MM-DD, today ({date.today().isoformat()}) if not mentioned"
   }}}}

2. ANYTHING ELSE — any question, comment, or conversation.
   You are a helpful assistant that can talk about any topic. Always respond in Spanish with a natural, friendly tone.
   Return: {{"intent": "query", "response": "your helpful answer in Spanish"}}

Category classification rules:
- vivienda: rent, mortgage, property taxes, home insurance
- super: supermarkets, grocery stores, food markets, butchers, bakeries
- salud: pharmacy, hospital, clinic, dentist, optician, health insurance
- servicios: electricity, gas, water, internet, phone, streaming subscriptions (Netflix, Spotify, etc.), SaaS
- vacaciones: flights, hotels, Airbnb, car rentals for travel, camping
- salidas: restaurants, bars, cafes, fast food, takeout, food delivery
- casa: furniture, home improvement, hardware stores, cleaning supplies, pet supplies, home services
- transporte: public transit (metro, bus, train), taxis, ride-hailing (Uber, Cabify), car sharing (Zity, Voltio)
- ocio: cinema, theatre, concerts, events, amusement parks, toys, games
- ropa: clothing, shoes, accessories, fashion stores
- educacion: school fees, tuition, daycare, extracurriculars, language classes
- impuestos: tax payments, government fees, municipal taxes, fines
- deportes: gym, yoga, swimming, sports clubs, fitness memberships
- coche: fuel, car wash, parking, tolls, car insurance, ITV/MOT, car maintenance
- sin_clasificar: ATM withdrawals, marketplace purchases (Wallapop, Temu, AliExpress, Shein) where the product is unknown, any expense you cannot confidently classify
- otros: anything that doesn't fit the above categories but IS clearly identifiable

Special patterns:
- "[Name] [amount]" or "[Name] €[amount]" (e.g. "Ana 60", "Carlos €30") = cash payment to a person. Set payment_method to "efectivo" and classify as "sin_clasificar" so the system asks the user for the correct category.
- ATM/cash withdrawals → sin_clasificar

IMPORTANT: If you are unsure about the category, use "sin_clasificar" rather than guessing wrong."""

    response = await call_llm(text, system=system)
    return _parse_json(response)


async def extract_expense_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    b64 = base64.standard_b64encode(image_bytes).decode()

    system = f"""You are the ticket OCR parser for CasaControl, a family budget app.
Analyse the receipt image and extract all relevant expense data.
Return ONLY valid JSON (no markdown) with:
  description    (string — store name + brief summary, e.g. "Mercadona — compra semanal")
  amount_eur     (number — final total on the ticket)
  category_slug  (one of: {', '.join(CATEGORY_SLUGS)})
  store          (string — store name)
  payment_method (string or null)
  date           (YYYY-MM-DD from the ticket, or today {date.today().isoformat()} if not visible)
  items          (array of {{name, quantity, unit_price, total_price}} — line items if legible, else [])

Category rules: supermarkets/grocery→super, restaurants/bars→salidas, pharmacy→salud,
clothing→ropa, fuel/parking→coche, hardware/furniture→casa, sports/gym→deportes.
If unsure, use "sin_clasificar".""""""

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


async def classify_bank_transactions_batch(transactions: list[dict]) -> list[dict]:
    """Classify a batch of bank transactions via LLM.

    Input: list of {description: str, amount: float, date: str}
    Output: list of {description, amount_eur, category_slug, store, payment_method, date}
    """
    system = f"""You are CasaControl, a family expense classifier.
Classify each bank transaction into an expense category.

For each transaction, return:
- description: short, clean description (e.g. "Compra Mercadona")
- amount_eur: the amount (positive number)
- category_slug: one of: {', '.join(CATEGORY_SLUGS)}
- store: merchant name, cleaned up (e.g. "MERCADONA S.A." → "Mercadona")
- payment_method: one of: tarjeta, transferencia, domiciliacion, cajero, bizum, or null
- date: the transaction date (YYYY-MM-DD)

Category rules:
- vivienda: rent, mortgage. super: supermarkets, groceries. salud: pharmacy, health.
- servicios: utilities, telecom, subscriptions. vacaciones: travel, hotels, flights.
- salidas: restaurants, bars, delivery. casa: furniture, hardware, home services.
- transporte: public transit, taxis, ride-hailing. ocio: entertainment, events, cinema.
- ropa: clothing, fashion. educacion: school, tuition, daycare.
- impuestos: tax payments, government fees. deportes: gym, yoga, sports.
- coche: fuel, parking, tolls, car maintenance, car insurance.
- sin_clasificar: ATM withdrawals, marketplace purchases where product is unknown.
- otros: identifiable expenses that don't fit elsewhere.

Respond with ONLY a valid JSON array. No markdown, no extra text."""

    user_content = json.dumps(transactions, ensure_ascii=False)
    response = await call_llm(user_content, system=system, max_tokens=2048)

    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            return json.loads(match.group())

    logger.warning("Batch classification failed, falling back to individual")
    results = []
    for tx in transactions:
        try:
            result = await classify_and_process(f"{tx['description']} {tx['amount']}€")
            if result.get("intent") == "expense":
                data = result["data"]
                data["date"] = tx.get("date", date.today().isoformat())
                results.append(data)
        except Exception:
            logger.warning("Individual classification failed for: %s", tx["description"])
            results.append({
                "description": tx["description"],
                "amount_eur": tx["amount"],
                "category_slug": "otros",
                "store": tx["description"],
                "payment_method": None,
                "date": tx.get("date", date.today().isoformat()),
            })
    return results
