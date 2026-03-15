"""CasaControl — Message formatters and keyboards."""

from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import CATEGORY_LABELS


def format_confirmation(data: dict, expense_id: str) -> str:
    cat = CATEGORY_LABELS.get(data.get("category_slug", ""), data.get("category_slug", "—"))
    amt = f"€{float(data['amount_eur']):.2f}" if data.get("amount_eur") else "❓ importe no detectado"
    desc = data.get("description", "—")
    store = data.get("store") or "—"
    dt = data.get("date") or date.today().isoformat()
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
            InlineKeyboardButton("💶 Editar importe", callback_data=f"editamt:{expense_id}"),
        ],
        [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"delete:{expense_id}")],
    ])


def build_duplicate_keyboard(expense_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Registrar igual", callback_data=f"force_save:{expense_id}"),
            InlineKeyboardButton("❌ Es duplicado", callback_data=f"skip_dup:{expense_id}"),
        ],
    ])


def build_ticket_prompt_keyboard(expense_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 Sí, mando foto", callback_data=f"ticket_yes:{expense_id}"),
            InlineKeyboardButton("No tengo", callback_data=f"ticket_no:{expense_id}"),
        ],
    ])
