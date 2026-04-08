"""
CasaControl Telegram Bot
Processes photos (tickets), voice notes, and text messages from the family group.
Extracts expenses via Groq API and stores them in Supabase.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import logging
from datetime import date, datetime

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

from config import TELEGRAM_TOKEN, ALLOWED_CHAT_IDS, CATEGORY_LABELS
from llm import classify_and_process, extract_expense_from_image, transcribe_audio
from db import (
    supabase, resolve_user_id, save_expense, save_ticket,
    upload_photo_to_storage, check_duplicate,
    get_monthly_expenses, get_budget_categories,
)
from formatters import (
    format_confirmation, build_edit_keyboard,
    build_duplicate_keyboard, build_ticket_prompt_keyboard,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("casacontrol")
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


# ── Access guard ──────────────────────────────────────────────────────────────

def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return (
        update.effective_chat.id in ALLOWED_CHAT_IDS
        or update.effective_user.id in ALLOWED_CHAT_IDS
    )


def get_message(update: Update):
    return update.message or update.edited_message


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = get_message(update)
    if not msg:
        return
    await msg.reply_text(
        "👋 *CasaControl Bot* activo\n\n"
        "Podés enviarme:\n"
        "📸 Foto de un ticket → lo registro automáticamente\n"
        "💬 Texto libre → \"Mercadona 45€\" o \"Alquiler 1430\"\n"
        "🎤 Audio → lo transcribo y registro\n"
        "❓ Pregunta → \"cuánto llevamos en super?\"\n\n"
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
    rows = get_monthly_expenses(month_start)
    totals: dict[str, float] = {}
    for row in rows:
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
    cats = get_budget_categories()
    rows = get_monthly_expenses(month_start)
    spent: dict[str, float] = {}
    for row in rows:
        slug = row["category_slug"] or "super"
        spent[slug] = spent.get(slug, 0) + float(row["amount_eur"])
    lines = [f"💰 *Presupuesto {today.strftime('%B %Y')}*\n"]
    total_budget = 0.0
    total_spent = 0.0
    for cat in sorted(cats, key=lambda c: c["slug"]):
        slug = cat["slug"]
        budget = float(cat["budget_eur"])
        s = spent.get(slug, 0.0)
        pct = (s / budget * 100) if budget else 0
        bar = "🔴" if pct >= 90 else "🟡" if pct >= 70 else "🟢"
        label = CATEGORY_LABELS.get(slug, cat["label"])
        lines.append(f"{bar} {label}: €{s:.0f} / €{budget:.0f} ({pct:.0f}%)")
        total_budget += budget
        total_spent += s
    lines.append(f"\n💶 *Total: €{total_spent:.0f} / €{total_budget:.0f}*")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process text: classify intent (expense / query / off_topic)."""
    logger.info(
        "handle_text triggered — chat_id=%s user_id=%s text=%r",
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
        (update.message or update.edited_message or {}).text[:80] if (update.message or update.edited_message) else None,
    )
    if not is_allowed(update):
        logger.warning("handle_text BLOCKED by is_allowed — chat_id=%s user_id=%s ALLOWED=%s",
                        update.effective_chat.id, update.effective_user.id, ALLOWED_CHAT_IDS)
        return
    msg = get_message(update)
    if not msg:
        logger.warning("handle_text: no message object")
        return

    text = msg.text.strip() if msg.text else ""
    if not text or text.startswith("/"):
        return

    # Handle pending amount correction
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

    # Handle pending ticket photo — user says "no"
    pending_ticket_expense = context.user_data.get("awaiting_ticket_photo_for")
    if pending_ticket_expense and text.lower() in ("no", "no tengo", "no tengo ticket", "nop", "nah"):
        context.user_data.pop("awaiting_ticket_photo_for", None)
        await msg.reply_text("👍 Perfecto, gasto registrado sin ticket.")
        return

    processing = await msg.reply_text("⏳ Procesando…")

    try:
        result = await classify_and_process(text)
    except Exception as e:
        logger.exception("Error classifying message")
        await processing.edit_text(f"⚠️ Error procesando el mensaje: {e}")
        return

    intent = result.get("intent", "off_topic")

    if intent == "query":
        await processing.edit_text(result.get("response", "No tengo respuesta para eso."))
        return

    if intent == "off_topic":
        await processing.edit_text(result.get("response", "Soy CasaControl, tu asistente de gastos."))
        return

    # intent == "expense"
    data = result.get("data", {})

    if not data.get("amount_eur"):
        await processing.edit_text(
            "❓ No detecté el importe. Probá con algo como:\n_\"Mercadona 45,30€\"_ o _\"Alquiler 1430\"_",
            parse_mode="Markdown",
        )
        return

    # Deduplication check
    duplicate = check_duplicate(
        store=data.get("store"),
        amount=data.get("amount_eur"),
        expense_date=data.get("date"),
    )
    if duplicate:
        dup_amt = float(duplicate["amount_eur"])
        dup_store = duplicate.get("store") or "sin tienda"
        context.user_data["pending_expense_data"] = data
        await processing.edit_text(
            f"⚠️ Ya registraste *{dup_store}* €{dup_amt:.2f} hoy.\n¿Querés registrarlo igual o es duplicado?",
            parse_mode="Markdown",
            reply_markup=build_duplicate_keyboard("pending"),
        )
        return

    user_id = resolve_user_id(update.effective_user.id)
    try:
        expense = save_expense(data, user_id=user_id, source="telegram")
    except Exception as e:
        logger.exception("Error saving expense")
        await processing.edit_text(f"⚠️ Error guardando el gasto: {e}")
        return

    confirmation = format_confirmation(data, expense["id"])

    # If super category, ask for ticket photo
    if data.get("category_slug") == "super":
        context.user_data["awaiting_ticket_photo_for"] = expense["id"]
        await processing.edit_text(
            confirmation + "\n\n🧾 *¿Tenés foto del ticket?*",
            parse_mode="Markdown",
            reply_markup=build_ticket_prompt_keyboard(expense["id"]),
        )
    else:
        await processing.edit_text(
            confirmation,
            parse_mode="Markdown",
            reply_markup=build_edit_keyboard(expense["id"]),
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download a ticket photo, run OCR via Groq, save to Supabase."""
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
        logger.warning("Could not upload photo to storage: %s", e)
        image_url = ""

    user_id = resolve_user_id(update.effective_user.id)

    # Check if this photo is for a pending super expense
    pending_expense_id = context.user_data.pop("awaiting_ticket_photo_for", None)

    try:
        if pending_expense_id:
            ticket = save_ticket(
                data,
                image_url=image_url,
                user_id=user_id,
                telegram_msg_id=msg.message_id,
                telegram_chat_id=update.effective_chat.id,
                expense_id=pending_expense_id,
            )
            expense_id = pending_expense_id
        else:
            expense = save_expense(data, user_id=user_id, source="telegram")
            expense_id = expense["id"]
            ticket = save_ticket(
                data,
                image_url=image_url,
                user_id=user_id,
                telegram_msg_id=msg.message_id,
                telegram_chat_id=update.effective_chat.id,
                expense_id=expense_id,
            )
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
        format_confirmation(data, expense_id) + items_text,
        parse_mode="Markdown",
        reply_markup=build_edit_keyboard(expense_id),
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Transcribe voice note via Groq Whisper, then process as text."""
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return

    processing = await msg.reply_text("🎤 Transcribiendo audio…")

    voice = msg.voice
    tg_file = await voice.get_file()

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(tg_file.file_path)
        r.raise_for_status()
        audio_bytes = r.content

    try:
        transcribed = await transcribe_audio(audio_bytes, mime_type=voice.mime_type or "audio/ogg")
    except Exception as e:
        logger.exception("Error transcribing audio")
        await processing.edit_text(f"⚠️ No pude transcribir el audio: {e}")
        return

    await processing.edit_text(f"🎤 _{transcribed}_\n\n⏳ Procesando…", parse_mode="Markdown")

    try:
        result = await classify_and_process(transcribed)
    except Exception as e:
        logger.exception("Error classifying transcribed text")
        await processing.edit_text(f"🎤 _{transcribed}_\n\n⚠️ Error: {e}", parse_mode="Markdown")
        return

    intent = result.get("intent", "off_topic")

    if intent in ("query", "off_topic"):
        await processing.edit_text(
            f"🎤 _{transcribed}_\n\n{result.get('response', '')}",
            parse_mode="Markdown",
        )
        return

    # intent == "expense"
    data = result.get("data", {})

    if not data.get("amount_eur"):
        await processing.edit_text(
            f"🎤 _{transcribed}_\n\n❓ No detecté el importe.",
            parse_mode="Markdown",
        )
        return

    user_id = resolve_user_id(update.effective_user.id)
    try:
        expense = save_expense(data, user_id=user_id, source="telegram")
    except Exception as e:
        logger.exception("Error saving expense from voice")
        await processing.edit_text(f"🎤 _{transcribed}_\n\n⚠️ Error: {e}", parse_mode="Markdown")
        return

    await processing.edit_text(
        f"🎤 _{transcribed}_\n\n{format_confirmation(data, expense['id'])}",
        parse_mode="Markdown",
        reply_markup=build_edit_keyboard(expense["id"]),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    data_str = query.data
    action = data_str.split(":", 1)[0]

    if action == "delete":
        expense_id = data_str.split(":", 1)[1]
        try:
            supabase.table("expenses").delete().eq("id", expense_id).execute()
            await query.edit_message_text("🗑️ Gasto eliminado.")
        except Exception as e:
            await query.edit_message_text(f"⚠️ Error eliminando: {e}")

    elif action == "editcat":
        expense_id = data_str.split(":", 1)[1]
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"setcat:{expense_id}:{slug}")]
            for slug, label in CATEGORY_LABELS.items()
        ]
        await query.edit_message_reply_markup(InlineKeyboardMarkup(buttons))

    elif action == "setcat":
        _, eid, new_slug = data_str.split(":", 2)
        try:
            supabase.table("expenses").update({"category_slug": new_slug}).eq("id", eid).execute()
            await query.edit_message_text(
                f"✅ Categoría actualizada a {CATEGORY_LABELS.get(new_slug, new_slug)}"
            )
        except Exception as e:
            await query.edit_message_text(f"⚠️ Error actualizando: {e}")

    elif action == "editamt":
        expense_id = data_str.split(":", 1)[1]
        context.user_data["awaiting_amount_for"] = expense_id
        await query.edit_message_text(
            "💶 Enviame el importe correcto (solo el número, ej: *45.30*)",
            parse_mode="Markdown",
        )

    elif action == "force_save":
        pending_data = context.user_data.pop("pending_expense_data", None)
        if not pending_data:
            await query.edit_message_text("⚠️ No hay gasto pendiente.")
            return
        user_id = resolve_user_id(update.effective_user.id)
        try:
            expense = save_expense(pending_data, user_id=user_id, source="telegram")
            confirmation = format_confirmation(pending_data, expense["id"])
            if pending_data.get("category_slug") == "super":
                context.user_data["awaiting_ticket_photo_for"] = expense["id"]
                await query.edit_message_text(
                    confirmation + "\n\n🧾 *¿Tenés foto del ticket?*",
                    parse_mode="Markdown",
                    reply_markup=build_ticket_prompt_keyboard(expense["id"]),
                )
            else:
                await query.edit_message_text(
                    confirmation,
                    parse_mode="Markdown",
                    reply_markup=build_edit_keyboard(expense["id"]),
                )
        except Exception as e:
            await query.edit_message_text(f"⚠️ Error guardando: {e}")

    elif action == "skip_dup":
        context.user_data.pop("pending_expense_data", None)
        await query.edit_message_text("👍 Duplicado descartado.")

    elif action == "ticket_yes":
        expense_id = data_str.split(":", 1)[1]
        context.user_data["awaiting_ticket_photo_for"] = expense_id
        await query.edit_message_text("📸 Mandame la foto del ticket.")

    elif action == "ticket_no":
        context.user_data.pop("awaiting_ticket_photo_for", None)
        await query.edit_message_text("👍 Perfecto, gasto registrado sin ticket.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("resumen", cmd_resumen))
    app.add_handler(CommandHandler("presupuesto", cmd_presupuesto))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_error_handler(error_handler)

    logger.info("CasaControl bot starting…")
    logger.info("ALLOWED_CHAT_IDS = %s", ALLOWED_CHAT_IDS)
    logger.info("Handlers registered: start, resumen, presupuesto, callback, text, photo, voice")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query", "edited_message"])


if __name__ == "__main__":
    main()
