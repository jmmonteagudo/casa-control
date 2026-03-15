"""CasaControl — Supabase database operations."""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("casacontrol.db")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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
                telegram_msg_id: int, telegram_chat_id: int,
                expense_id: Optional[str] = None) -> dict:
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

    # Link ticket to expense if provided
    if expense_id:
        supabase.table("expenses").update({"ticket_id": ticket["id"]}).eq("id", expense_id).execute()

    return ticket


def upload_photo_to_storage(image_bytes: bytes, filename: str) -> str:
    path = f"tickets/{filename}"
    supabase.storage.from_("tickets").upload(
        path, image_bytes, {"content-type": "image/jpeg"}
    )
    return supabase.storage.from_("tickets").get_public_url(path)


def check_duplicate(store: Optional[str], amount: Optional[float], expense_date: Optional[str]) -> Optional[dict]:
    """Check if a similar expense was registered in the last 24 hours.

    Returns the matching expense dict if found, None otherwise.
    """
    if not amount:
        return None

    now = datetime.utcnow()
    since = (now - timedelta(hours=24)).isoformat()

    query = (
        supabase.table("expenses")
        .select("id, description, amount_eur, store, date")
        .gte("created_at", since)
        .gte("amount_eur", amount - 0.50)
        .lte("amount_eur", amount + 0.50)
    )

    if store:
        query = query.ilike("store", store)

    if expense_date:
        query = query.eq("date", expense_date)

    result = query.execute()
    return result.data[0] if result.data else None


def get_monthly_expenses(month_start: str) -> list[dict]:
    result = (
        supabase.table("expenses")
        .select("category_slug, amount_eur")
        .gte("date", month_start)
        .execute()
    )
    return result.data


def get_budget_categories() -> list[dict]:
    result = supabase.table("budget_categories").select("slug, label, budget_eur").execute()
    return result.data
