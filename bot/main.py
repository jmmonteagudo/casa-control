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

from config import TELEGRAM_TOKEN, ALLOWED_CHAT_IDS, CATEGORY_LABELS, GROUP_CHAT_ID
from llm import classify_and_process, extract_expense_from_image, transcribe_audio
from db import (
    supabase, resolve_user_id, save_expense, save_ticket,
    upload_photo_to_storage, check_duplicate,
    get_monthly_expenses, get_budget_categories,
    get_pending_review_count, get_pending_review_expenses,
    get_recurring_expenses, save_recurring_expense, deactivate_recurring_expense,
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
        "/presupuesto — estado vs. presupuesto\n"
        "/pendientes — gastos sin clasificar\n"
        "/recurrentes — gastos fijos mensuales\n"
        "/recurrente — agregar gasto fijo\n"
        "/myid — tu chat\\_id (para Shortcuts iOS)\n\n"
        "Tambien podes enviar un CSV bancario para importar gastos.",
        parse_mode="Markdown",
    )


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = get_message(update)
    if not msg:
        return
    await msg.reply_text(
        f"🆔 *Tu info:*\n"
        f"Chat ID: `{update.effective_chat.id}`\n"
        f"User ID: `{update.effective_user.id}`",
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
    pending = get_pending_review_count()
    if pending > 0:
        lines.append(f"\n⚠️ Tenes {pending} gastos pendientes de clasificar. /pendientes")
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


async def cmd_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return
    expenses = get_pending_review_expenses(limit=10)
    if not expenses:
        await msg.reply_text("✅ No hay gastos pendientes de clasificar.")
        return
    total = get_pending_review_count()
    lines = [f"⚠️ *{total} gastos sin clasificar* (mostrando {len(expenses)}):\n"]
    for exp in expenses:
        amt = float(exp["amount_eur"])
        desc = exp.get("description", "—")
        store = exp.get("store") or ""
        dt = exp.get("date", "")
        lines.append(f"• {desc} — *€{amt:.2f}* ({dt})")
    lines.append("\nPodes reclasificarlos desde la webapp en Movimientos > Sin clasificar")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_recurrente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a recurring expense: /recurrente Seguro salud 85 salud"""
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return
    text = msg.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await msg.reply_text(
            "Uso: `/recurrente Descripcion MONTO CATEGORIA [DIA]`\n"
            "Ej: `/recurrente Seguro salud 85 salud`\n"
            "Ej: `/recurrente Alquiler 1430 vivienda 1`",
            parse_mode="Markdown",
        )
        return

    args = parts[1].strip()
    # Parse from the end: optional day, required category, required amount, rest is description
    tokens = args.split()
    if len(tokens) < 3:
        await msg.reply_text("⚠️ Necesito al menos: descripcion, monto y categoria.")
        return

    # Check if last token is a day number
    day_of_month = 1
    if tokens[-1].isdigit() and 1 <= int(tokens[-1]) <= 31:
        day_of_month = int(tokens.pop())

    category_slug = tokens.pop().lower()
    if category_slug not in [s for s in CATEGORY_LABELS.keys()]:
        await msg.reply_text(
            f"⚠️ Categoria '{category_slug}' no existe.\n"
            f"Categorias validas: {', '.join(CATEGORY_LABELS.keys())}"
        )
        return

    # Amount is the last remaining numeric token
    amount_str = tokens.pop()
    try:
        amount = float(amount_str.replace(",", ".").replace("€", ""))
    except ValueError:
        await msg.reply_text("⚠️ No entendi el monto. Usa numeros, ej: 85 o 85.50")
        return

    description = " ".join(tokens).strip()
    if not description:
        await msg.reply_text("⚠️ Falta la descripcion.")
        return

    data = {
        "description": description,
        "amount_eur": amount,
        "category_slug": category_slug,
        "day_of_month": day_of_month,
    }
    rec = save_recurring_expense(data)
    label = CATEGORY_LABELS.get(category_slug, category_slug)
    await msg.reply_text(
        f"✅ *Gasto recurrente creado*\n\n"
        f"📝 {description}\n"
        f"💶 *€{amount:.2f}*\n"
        f"🏷️ {label}\n"
        f"📅 Dia {day_of_month} de cada mes\n\n"
        f"_ID: {rec['id'][:8]}…_",
        parse_mode="Markdown",
    )


async def cmd_recurrentes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return
    recurrentes = get_recurring_expenses()
    if not recurrentes:
        await msg.reply_text("No hay gastos recurrentes activos.")
        return
    lines = ["📋 *Gastos recurrentes activos:*\n"]
    total = 0.0
    for r in recurrentes:
        amt = float(r["amount_eur"])
        total += amt
        label = CATEGORY_LABELS.get(r["category_slug"], r["category_slug"])
        lines.append(f"• {r['description']} — *€{amt:.2f}* {label} (dia {r.get('day_of_month', 1)})")
        lines.append(f"  _/borrar\\_recurrente {r['id'][:8]}_")
    lines.append(f"\n💶 *Total fijo mensual: €{total:.2f}*")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_borrar_recurrente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    msg = get_message(update)
    if not msg:
        return
    parts = msg.text.strip().split()
    if len(parts) < 2:
        await msg.reply_text("Uso: `/borrar_recurrente ID`", parse_mode="Markdown")
        return
    partial_id = parts[1]
    # Find the full ID from partial
    recurrentes = get_recurring_expenses()
    match = [r for r in recurrentes if r["id"].startswith(partial_id)]
    if not match:
        await msg.reply_text("⚠️ No encontre un gasto recurrente con ese ID.")
        return
    rec = match[0]
    if deactivate_recurring_expense(rec["id"]):
        await msg.reply_text(f"✅ Gasto recurrente desactivado: {rec['description']}")
    else:
        await msg.reply_text("⚠️ Error desactivando el gasto recurrente.")


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

    # Detect shortcut prefixes from iOS Shortcut
    from_shortcut = text.startswith("[shortcut]") or text.startswith("[Apple Pay]")
    if from_shortcut:
        text = re.sub(r"^\[(?:shortcut|Apple Pay)\]\s*", "", text)

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

    if from_shortcut:
        data["payment_method"] = "apple_pay"

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
        context.user_data["pending_from_shortcut"] = from_shortcut
        await processing.edit_text(
            f"⚠️ Ya registraste *{dup_store}* €{dup_amt:.2f} hoy.\n¿Querés registrarlo igual o es duplicado?",
            parse_mode="Markdown",
            reply_markup=build_duplicate_keyboard("pending"),
        )
        return

    source = "shortcut" if from_shortcut else "telegram"
    user_id = resolve_user_id(update.effective_user.id)
    try:
        expense = save_expense(data, user_id=user_id, source=source)
    except Exception as e:
        logger.exception("Error saving expense")
        await processing.edit_text(f"⚠️ Error guardando el gasto: {e}")
        return

    confirmation = format_confirmation(data, expense["id"])

    # Repost to group if this came from shortcut (private chat)
    if from_shortcut and GROUP_CHAT_ID and update.effective_chat.id != GROUP_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=f"📱 *Shortcut*\n{confirmation}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning("Could not repost to group: %s", e)

    # If super category, ask for ticket photo
    if data.get("category_slug") == "super":
        context.user_data["awaiting_ticket_photo_for"] = expense["id"]
        await processing.edit_text(
            confirmation + "\n\n🧾 *¿Tenés foto del ticket?*",
            parse_mode="Markdown",
            reply_markup=build_ticket_prompt_keyboard(expense["id"]),
        )
    elif data.get("category_slug") == "sin_clasificar":
        # Show category keyboard so user can reclassify immediately
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"setcat:{expense['id']}:{slug}")]
            for slug, label in CATEGORY_LABELS.items()
            if slug != "sin_clasificar"
        ]
        await processing.edit_text(
            confirmation + "\n\n❓ *¿A qué categoria pertenece?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
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
            supabase.table("expenses").update({"category_slug": new_slug, "needs_review": False}).eq("id", eid).execute()
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
        pending_from_shortcut = context.user_data.pop("pending_from_shortcut", False)
        if not pending_data:
            await query.edit_message_text("⚠️ No hay gasto pendiente.")
            return
        source = "shortcut" if pending_from_shortcut else "telegram"
        user_id = resolve_user_id(update.effective_user.id)
        try:
            expense = save_expense(pending_data, user_id=user_id, source=source)
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
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("resumen", cmd_resumen))
    app.add_handler(CommandHandler("presupuesto", cmd_presupuesto))
    app.add_handler(CommandHandler("pendientes", cmd_pendientes))
    app.add_handler(CommandHandler("recurrente", cmd_recurrente))
    app.add_handler(CommandHandler("recurrentes", cmd_recurrentes))
    app.add_handler(CommandHandler("borrar_recurrente", cmd_borrar_recurrente))

    # CSV import handler
    from banking import handle_document
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_error_handler(error_handler)

    logger.info("CasaControl bot starting…")
    logger.info("ALLOWED_CHAT_IDS = %s", ALLOWED_CHAT_IDS)
    logger.info("GROUP_CHAT_ID = %s", GROUP_CHAT_ID)
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query", "edited_message"])


if __name__ == "__main__":
    main()
