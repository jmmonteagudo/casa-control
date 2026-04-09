"""CasaControl — Bank CSV import via Telegram.

Users send a CSV/Excel bank statement to the bot.
The bot auto-detects the format (CaixaBank, ING, generic),
classifies each transaction via LLM, deduplicates, and imports.
"""

import csv
import io
import logging
import re
from datetime import date, datetime
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from config import ALLOWED_CHAT_IDS
from db import (
    supabase, resolve_user_id, save_expense, check_duplicate,
    save_synced_transaction,
)
from llm import classify_bank_transactions_batch

logger = logging.getLogger("casacontrol.banking")

# ── Access guard ─────────────────────────────────────────────────────────────

def _is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    return (
        update.effective_chat.id in ALLOWED_CHAT_IDS
        or update.effective_user.id in ALLOWED_CHAT_IDS
    )


# ── CSV Parsing ──────────────────────────────────────────────────────────────

def _detect_delimiter(sample: str) -> str:
    """Detect CSV delimiter from first lines."""
    for delim in [";", ",", "\t"]:
        if delim in sample:
            return delim
    return ","


def _parse_amount(raw: str) -> Optional[float]:
    """Parse amount string handling European/Spanish formatting."""
    if not raw or not raw.strip():
        return None
    clean = raw.strip().replace(" ", "")
    # Remove currency symbols
    clean = re.sub(r"[€$£]", "", clean)
    # European format: 1.234,56 → 1234.56
    if "," in clean and "." in clean:
        if clean.rindex(",") > clean.rindex("."):
            clean = clean.replace(".", "").replace(",", ".")
        else:
            clean = clean.replace(",", "")
    elif "," in clean:
        clean = clean.replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None


def _parse_date(raw: str) -> Optional[str]:
    """Parse date string into YYYY-MM-DD format."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _find_columns(headers: list[str]) -> dict:
    """Auto-detect column indices for date, concept, amount from headers."""
    headers_lower = [h.strip().lower() for h in headers]
    mapping = {"date": None, "concept": None, "amount": None}

    # Date column
    for i, h in enumerate(headers_lower):
        if h in ("fecha", "date", "fecha operación", "fecha operacion", "fecha valor", "f. operación"):
            mapping["date"] = i
            break

    # Concept/description column
    for i, h in enumerate(headers_lower):
        if h in ("concepto", "concept", "descripción", "descripcion", "movimiento", "detalle"):
            mapping["concept"] = i
            break

    # Amount column
    for i, h in enumerate(headers_lower):
        if h in ("importe", "amount", "cantidad", "importe (eur)", "importe(eur)"):
            mapping["amount"] = i
            break

    # Fallback: if we can't detect, try common patterns
    # CaixaBank: Fecha;Fecha valor;Concepto;Importe;Saldo
    # ING: Fecha;Fecha valor;Concepto;Importe;Divisa;Saldo
    if mapping["date"] is None and len(headers) >= 3:
        mapping["date"] = 0
    if mapping["concept"] is None and len(headers) >= 3:
        mapping["concept"] = 2 if len(headers) >= 4 else 1
    if mapping["amount"] is None and len(headers) >= 4:
        mapping["amount"] = 3

    return mapping


def parse_bank_csv(content: str) -> list[dict]:
    """Parse a bank CSV file and return transactions.

    Returns list of {date, description, amount} dicts.
    Only returns expenses (negative amounts), with amount as positive.
    """
    # Skip BOM
    if content.startswith("\ufeff"):
        content = content[1:]

    # Skip blank lines at start
    lines = content.strip().split("\n")
    # Find header line (first line with multiple delimited fields)
    header_idx = 0
    delimiter = _detect_delimiter(lines[0] if lines else "")
    for i, line in enumerate(lines):
        if line.count(delimiter) >= 2:
            header_idx = i
            break

    # Parse as CSV
    reader = csv.reader(lines[header_idx:], delimiter=delimiter)
    rows = list(reader)
    if len(rows) < 2:
        return []

    headers = rows[0]
    mapping = _find_columns(headers)
    logger.info("CSV columns detected: %s from headers %s", mapping, headers)

    transactions = []
    for row in rows[1:]:
        if len(row) <= max(v for v in mapping.values() if v is not None):
            continue

        tx_date = _parse_date(row[mapping["date"]]) if mapping["date"] is not None else None
        concept = row[mapping["concept"]].strip() if mapping["concept"] is not None else ""
        amount = _parse_amount(row[mapping["amount"]]) if mapping["amount"] is not None else None

        if not concept or amount is None:
            continue

        # Only expenses (negative amounts)
        if amount >= 0:
            continue

        transactions.append({
            "date": tx_date or date.today().isoformat(),
            "description": concept,
            "amount": abs(amount),
        })

    return transactions


# ── Import logic ─────────────────────────────────────────────────────────────

async def import_transactions(transactions: list[dict], user_id: Optional[str]) -> dict:
    """Import parsed transactions: classify, deduplicate, save.

    Returns {new: int, skipped: int, total_eur: float, errors: int}
    """
    stats = {"new": 0, "skipped": 0, "total_eur": 0.0, "errors": 0}

    to_classify = []
    for tx in transactions:
        # Check cross-source duplicate
        duplicate = check_duplicate(
            store=tx["description"],
            amount=tx["amount"],
            expense_date=tx["date"],
        )
        if duplicate:
            stats["skipped"] += 1
            continue
        to_classify.append(tx)

    if not to_classify:
        return stats

    # Batch classify in chunks of 10
    for i in range(0, len(to_classify), 10):
        batch = to_classify[i:i+10]
        try:
            classified = await classify_bank_transactions_batch(batch)
        except Exception as e:
            logger.error("Batch classification failed: %s", e)
            stats["errors"] += len(batch)
            continue

        for cls_data in classified:
            try:
                save_expense(cls_data, user_id=user_id, source="csv_import")
                stats["new"] += 1
                stats["total_eur"] += float(cls_data.get("amount_eur", 0))
            except Exception as e:
                logger.error("Error saving CSV expense: %s", e)
                stats["errors"] += 1

    return stats


# ── Telegram handler ─────────────────────────────────────────────────────────

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle CSV/Excel file uploads — parse and import bank transactions."""
    if not _is_allowed(update):
        return
    msg = update.message or update.edited_message
    if not msg or not msg.document:
        return

    doc = msg.document
    filename = (doc.file_name or "").lower()

    # Only process CSV files
    if not (filename.endswith(".csv") or filename.endswith(".txt") or
            doc.mime_type in ("text/csv", "text/plain", "application/csv")):
        return

    processing = await msg.reply_text("Procesando extracto bancario...")

    # Download file
    tg_file = await doc.get_file()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(tg_file.file_path)
        r.raise_for_status()
        content = r.content

    # Try common encodings
    for encoding in ("utf-8", "latin-1", "cp1252", "iso-8859-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        await processing.edit_text("No pude leer el archivo. Proba exportando como CSV con codificacion UTF-8.")
        return

    # Parse CSV
    try:
        transactions = parse_bank_csv(text)
    except Exception as e:
        logger.exception("Error parsing CSV")
        await processing.edit_text(f"Error parseando el CSV: {e}")
        return

    if not transactions:
        await processing.edit_text(
            "No encontre transacciones (gastos) en el archivo.\n"
            "Verifica que sea un CSV de extracto bancario con columnas de fecha, concepto e importe."
        )
        return

    await processing.edit_text(
        f"Encontre {len(transactions)} gastos en el extracto.\n"
        f"Clasificando y deduplicando..."
    )

    user_id = resolve_user_id(update.effective_user.id)
    stats = await import_transactions(transactions, user_id=user_id)

    lines = [
        "*Importacion completada:*\n",
        f"Transacciones en el archivo: {len(transactions)}",
        f"Nuevos gastos importados: {stats['new']}",
        f"Duplicados omitidos: {stats['skipped']}",
    ]
    if stats["errors"]:
        lines.append(f"Errores: {stats['errors']}")
    if stats["total_eur"]:
        lines.append(f"\nTotal importado: {stats['total_eur']:.2f}")
    await processing.edit_text("\n".join(lines), parse_mode="Markdown")
