"""
CasaControl Telegram Bot
Processes photos (tickets), voice notes, and text messages from the family group.
Extracts expenses via Claude API and stores them in Supabase.
"""

import os
import re
import json
import logging
from datetime import date, datetime
from typing import Optional

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from supabase import create_client, Client

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("casacontrol")
# Enable DEBUG on telegram.ext to see all incoming updates
logging.getLogger("telegram.ext").setLevel(logging.DEBUG)

# ── Environment variables ─────────────────────────────────────────────────────
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY      = os.environ["GROQ_API_KEY"]
SUPABASE_URL      = os.environ["SUPABASE_URL"]
SUPABASE_KEY      = os.environ["SUPABASE_SERVICE_KEY"]
ALLOWED_CHAT_IDS  = set(
    int(x) for x in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip()
)

# ── Supabase client ───────────────────────────────────────────────────────────
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Category slugs ────────────────────────────────────────────────────────────
CATEGORY_SLUGS = [
    "vivienda", "super", "salud", "servicios", "vacaciones",
    "salidas", "casa", "transporte", "ocio", "ropa", "educacion",
]

CATEGORY_LABELS = {
    "vivienda":   "🏡 Vivienda",
    "super":      "🛒 Supermercado",
    "salud":      "🏥 Salud",
    "servicios":  "💡 Servicios",
    "vacaciones": "✈️ Vacaciones",
    "salidas":    "🍽️ Salidas",
    "casa":       "🏠 Casa/Hogar",
    "transporte": "🚗 Transporte",
    "ocio":       "🎈 Ocio/Kids",
    "ropa":       "👗 Ropa",
    "educacion":  "📚 Educación",
}

# ── Groq helpers ─────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


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


async def extract_expense_from_text(text: str) -> dict:
    system = f"""You are the expense parser for CasaControl, a family budget app for Martin and Romina in Madrid.
Extract structured expense data from the user message.
Return ONLY valid JSON (no markdown, no extra text) with these fields:
  description    (string, short expense name)
  amount_eur     (number, euros — null if not found)
  category_slug  (one of: {', '.join(CATEGORY_SLUGS)} — pick the best match)
  store          (string or null)
  payment_method (string or null — e.g. "Caixa", "Visa", "Efectivo")
  date           (string YYYY-MM-DD, today if not mentioned — today is {date.today().isoformat()})
Context clues: alquiler→vivienda, luz/gas/internet/móvil→servicios, médico/farmacia/mapfre→salud,
mercadona/aldi/lidl/costco/frutería/makro→super, restaurante/bar/cafetería→salidas,
taxi/uber/metro/bus→transporte, cole/guardería→educacion, ropa/zapatos→ropa."""

    response = await call_llm(text, system=system)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON: {response}")


async def extract_expense_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    import base64
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
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
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

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON: {response}")


# ── Supabase helpers ──────────────────────────────────────────────────────────

def resolve_user_id(telegram_id: int) -> Optional[str]:
    try:
        result = supabase.table("users").select("id").eq("telegram_id", telegram_id).maybe_single().execute()
        return result.data["id"] if result.data else None
    except Exception as e:
        logger.warning("Could not resolve user_id for telegram_id=%s: %s", telegram_id, e)
        return None


def save_expense(data: dict, user_id: Optional[str], source: str = "telegram") -> dict:
    row = {
        "date":           data.get("date") or date.today().isoformat(),
        "description":    data.get("description", "Gasto sin descripción"),
        "amount_eur":     data.get("amount_eur"),
        "category_slug":  data.get("category_slug", "super"),
        "payment_method": data.get("payment_method"),
        "store":          data.get("store"),
        "source":         source,
        "user_id":        user_id,
    }
    result = supabase.table("expenses").insert(row).execute()
    return result.data[0]


def save_ticket(data: dict, image_url: str, user_id: Optional[str],
                telegram_msg_id: int, telegram_chat_id: int) -> dict:
    ticket_row = {
        "date":             data.get("date") or date.today().isoformat(),
        "store":            data.get("store"),
        "total_eur":        data.get("amount_eur"),
        "image_url":        image_url,
        "status":           "confirmed",
        "telegram_msg_id":  telegram_msg_id,
        "telegram_chat_id": telegram_chat_id,
        "user_id":          user_id,
    }
    ticket_result = supabase.table("tickets").insert(ticket_row).execute()
    ticket = ticket_result.data[0]

    items = data.get("items", [])
    if items:
        item_rows = [
            {
                "ticket_id":     ticket["id"],
                "name":          i.get("name", "Artículo"),
                "quantity":      i.get("quantity", 1),
                "unit_price":    i.get("unit_price"),
                "total_price":   i.get("total_price"),
                "category_slug": data.get("category_slug", "super"),
            }
            for i in items
        ]
        supabase.table("ticket_items").insert(item_rows).execute()

    return ticket


def upload_photo_to_storage(image_bytes: bytes, filename: str) -> str:
    path = f"tickets/{filename}"
    supabase.storage.from_("tickets").upload(
        path, image_bytes, {"content-type": "image/jpeg"}
    )
    return supabase.storage.from_("tickets").get_public_url(path)


# ── Message formatters ────────────────────────────────────────────────────────

def format_confirmation(data: dict, expense_id: str) -> str:
    cat   = CATEGORY_LABELS.get(data.get("category_slug", ""), data.get("category_slug", "—"))
    amt   = f"€{float(data['amount_eur']):.2f}" if data.get("amount_eur") else "❓ importe no detectado"
    desc  = data.get("description", "—")
    store = data.get("store") or "—"
    dt    = data.get("date") or date.today().isoformat()
    return (
        f"✅ *Gasto registrado*\n\n"
        f"📝 {desc}\n"
        f"💶 *{amt}*\n"
        f"🏷️ {cat}\n"
        f"🏪 {store}\n"
        f"📅 {dt}\n\n"
        f"_ID: {expense_id[:8]}…_"
    )


def build_edit_keyboard(expense_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Editar categoría", callback_data=f"editcat:{expense_id}"),
            InlineKeyboardButton("💶 Editar importe",   callback_data=f"editamt:{expense_id}"),
        ],
        [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"delete:{expense_id}")],
    ])


# ── Access guard ──────────────────────────────────────────────────────────────

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return (
        update.effective_chat.id in ALLOWED_CHAT_IDS
        or update.effective_user.id in ALLOWED_CHAT_IDS
    )


def get_message(update: Update):
    """Return the message object whether it's a new message or an edited one."""
    return update.message or update.edited_message


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("cmd_start TRIGGERED — chat_id=%s", update.effective_chat.id)
    msg = get_message(update)
    if not msg:
        return
    await msg.reply_text(
        "👋 *CasaControl Bot* activo\n\n"
        "Podés enviarme:\n"
        "📸 Foto de un ticket → lo registro automáticamente\n"
        "💬 Texto libre → \"Mercadona 45€\" o \"Alquiler 1430\"\n"
        "🎤 Audio → próximamente\n\n"
        "Comandos:\n"
        "/resumen — gastos del mes actual\n"
        "/presupuesto — estado vs. presupuesto",
        parse_mode="Markdown",
    )


async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    result = (
        supabase.table("expenses")
        .select("category_slug, amount_eur")
        .gte("date", month_start)
        .execute()
    )
    totals: dict[str, float] = {}
    for row in result.data:
        slug = row["category_slug"] or "super"
        totals[slug] = totals.get(slug, 0) + float(row["amount_eur"])
    grand_total = sum(totals.values())
    lines = [f"📊 *Gastos {today.strftime('%B %Y')}*\n"]
    for slug, label in CATEGORY_LABELS.items():
        if slug in totals:
            lines.append(f"{label}: *€{totals[slug]:.2f}*")
    lines.append(f"\n💶 *Total: €{grand_total:.2f}*")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_presupuesto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    cats_result  = supabase.table("budget_categories").select("slug, label, budget_eur").execute()
    spent_result = (
        supabase.table("expenses")
        .select("category_slug, amount_eur")
        .gte("date", month_start)
        .execute()
    )
    spent: dict[str, float] = {}
    for row in spent_result.data:
        slug = row["category_slug"] or "super"
        spent[slug] = spent.get(slug, 0) + float(row["amount_eur"])
    lines = [f"💰 *Presupuesto {today.strftime('%B %Y')}*\n"]
    total_budget = 0.0
    total_spent  = 0.0
    for cat in sorted(cats_result.data, key=lambda c: c["slug"]):
        slug   = cat["slug"]
        budget = float(cat["budget_eur"])
        s      = spent.get(slug, 0.0)
        pct    = (s / budget * 100) if budget else 0
        bar    = "🔴" if pct >= 90 else "🟡" if pct >= 70 else "🟢"
        label  = CATEGORY_LABELS.get(slug, cat["label"])
        lines.append(f"{bar} {label}: €{s:.0f} / €{budget:.0f} ({pct:.0f}%)")
        total_budget += budget
        total_spent  += s
    lines.append(f"\n💶 *Total: €{total_spent:.0f} / €{total_budget:.0f}*")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a free-text expense message, or a pending amount correction."""
    logger.info(
        "handle_text TRIGGERED — chat_id=%s, user_id=%s, text=%r",
        update.effective_chat.id,
        update.effective_user.id if update.effective_user else None,
        (update.message or update.edited_message or {}).text if (update.message or update.edited_message) else None,
    )
    if not is_allowed(update):
        logger.warning(
            "handle_text BLOCKED by is_allowed — chat_id=%s not in ALLOWED_CHAT_IDS=%s",
            update.effective_chat.id,
            ALLOWED_CHAT_IDS,
        )
        return
    msg = get_message(update)
    if not msg:
        logger.warning("handle_text — no message object found")
        return

    text = msg.text.strip() if msg.text else ""
    if not text or text.startswith("/"):
        logger.info("handle_text — empty or command text, skipping")
        return

    # Handle pending amount correction from inline keyboard
    expense_id = context.user_data.pop("awaiting_amount_for", None)
    if expense_id:
        clean = text.replace(",", ".")
        try:
            amount = float(re.sub(r"[^\d.]", "", clean))
            supabase.table("expenses").update({"amount_eur": amount}).eq("id", expense_id).execute()
            await msg.reply_text(f"✅ Importe actualizado a €{amount:.2f}")
        except ValueError:
            await msg.reply_text("⚠️ No entendí el importe. Ingresá solo el número, ej: *45.30*", parse_mode="Markdown")
        return

    processing = await msg.reply_text("⏳ Procesando…")

    try:
        data = await extract_expense_from_text(text)
    except Exception as e:
        logger.exception("Error parsing text expense")
        await processing.edit_text(f"⚠️ No pude interpretar el gasto: {e}")
        return

    if not data.get("amount_eur"):
        await processing.edit_text(
            "❓ No detecté el importe. Probá con algo como:\n_\"Mercadona 45,30€\"_ o _\"Alquiler 1430\"_",
            parse_mode="Markdown",
        )
        return

    user_id = resolve_user_id(update.effective_user.id)
    try:
        expense = save_expense(data, user_id=user_id, source="telegram")
    except Exception as e:
        logger.exception("Error saving expense")
        await processing.edit_text(f"⚠️ Error guardando el gasto: {e}")
        return

    await processing.edit_text(
        format_confirmation(data, expense["id"]),
        parse_mode="Markdown",
        reply_markup=build_edit_keyboard(expense["id"]),
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download a ticket photo, run OCR via Claude, save to Supabase."""
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return

    processing = await msg.reply_text("📸 Leyendo ticket…")
    photo = msg.photo[-1]
    tg_file = await photo.get_file()

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(tg_file.file_path)
        r.raise_for_status()
        image_bytes = r.content

    try:
        data = await extract_expense_from_image(image_bytes)
    except Exception as e:
        logger.exception("Error parsing ticket image")
        await processing.edit_text(f"⚠️ No pude leer el ticket: {e}")
        return

    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{photo.file_unique_id}.jpg"
    try:
        image_url = upload_photo_to_storage(image_bytes, filename)
    except Exception as e:
        logger.warning(f"Could not upload photo to storage: {e}")
        image_url = ""

    user_id = resolve_user_id(update.effective_user.id)

    try:
        ticket = save_ticket(
            data,
            image_url=image_url,
            user_id=user_id,
            telegram_msg_id=msg.message_id,
            telegram_chat_id=update.effective_chat.id,
        )
        expense = save_expense(data, user_id=user_id, source="telegram")
        supabase.table("expenses").update({"ticket_id": ticket["id"]}).eq("id", expense["id"]).execute()
    except Exception as e:
        logger.exception("Error saving ticket/expense")
        await processing.edit_text(f"⚠️ Error guardando el ticket: {e}")
        return

    items = data.get("items", [])
    items_text = ""
    if items:
        item_lines = [f"  • {i['name']} — €{i.get('total_price') or '?'}" for i in items[:8]]
        if len(items) > 8:
            item_lines.append(f"  … y {len(items) - 8} artículos más")
        items_text = "\n\n🧾 *Artículos:*\n" + "\n".join(item_lines)

    await processing.edit_text(
        format_confirmation(data, expense["id"]) + items_text,
        parse_mode="Markdown",
        reply_markup=build_edit_keyboard(expense["id"]),
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Voice notes: placeholder until audio transcription is available."""
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return
    await msg.reply_text(
        "🎤 Por ahora no proceso voz. Escribí el gasto en texto, ej: _\"Frutería 18€\"_",
        parse_mode="Markdown",
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    action, expense_id = query.data.split(":", 1)

    if action == "delete":
        try:
            supabase.table("expenses").delete().eq("id", expense_id).execute()
            await query.edit_message_text("🗑️ Gasto eliminado.")
        except Exception as e:
            await query.edit_message_text(f"⚠️ Error eliminando: {e}")

    elif action == "editcat":
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"setcat:{expense_id}:{slug}")]
            for slug, label in CATEGORY_LABELS.items()
        ]
        await query.edit_message_reply_markup(InlineKeyboardMarkup(buttons))

    elif action == "setcat":
        _, eid, new_slug = query.data.split(":", 2)
        try:
            supabase.table("expenses").update({"category_slug": new_slug}).eq("id", eid).execute()
            await query.edit_message_text(
                f"✅ Categoría actualizada a {CATEGORY_LABELS.get(new_slug, new_slug)}"
            )
        except Exception as e:
            await query.edit_message_text(f"⚠️ Error actualizando: {e}")

    elif action == "editamt":
        context.user_data["awaiting_amount_for"] = expense_id
        await query.edit_message_text(
            "💶 Enviame el importe correcto (solo el número, ej: *45.30*)",
            parse_mode="Markdown",
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler — notify the user instead of failing silently."""
    logger.exception("Unhandled exception: %s", context.error)
    if update and isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Error interno: {context.error}",
            )
        except Exception:
            logger.exception("Failed to send error message to chat")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("resumen",     cmd_resumen))
    app.add_handler(CommandHandler("presupuesto", cmd_presupuesto))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_error_handler(error_handler)

    logger.info("CasaControl bot starting…")
    logger.info("ALLOWED_CHAT_IDS = %s", ALLOWED_CHAT_IDS)
    logger.info(
        "Registered handlers: %s",
        [(type(h).__name__, getattr(h, 'callback', None).__name__ if hasattr(getattr(h, 'callback', None), '__name__') else str(h)) for h in app.handlers.get(0, [])],
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
