# Bot de Telegram

## Módulos

| Archivo | Responsabilidad |
|---|---|
| `bot.py` | Handlers de Telegram + main() |
| `config.py` | Variables de entorno, categorías, constantes |
| `llm.py` | Llamadas a Groq: classify_and_process, extract_expense_from_image, transcribe_audio |
| `db.py` | Operaciones Supabase: save_expense, save_ticket, check_duplicate, etc. |
| `formatters.py` | Formateo de confirmaciones y teclados inline |

## Flujos por tipo de input

### Texto libre
```
Usuario envía texto
→ classify_and_process(text)
  → intent: "expense" → save_expense + confirmar con teclado inline
  → intent: "query"   → responder con texto del LLM
  → intent: "off_topic" → indicar scope del bot
```

### Foto de ticket
```
Usuario envía foto
→ extract_expense_from_image(image_bytes) via Groq Vision
→ upload_photo_to_storage
→ save_ticket + save_expense + vincular
→ Confirmar con resumen de artículos + teclado inline
```

### Audio
```
Usuario envía nota de voz
→ transcribe_audio(audio_bytes) via Groq Whisper
→ classify_and_process(transcribed_text) (mismo flujo que texto)
```

## Comandos

| Comando | Descripción |
|---|---|
| `/start` | Mensaje de bienvenida |
| `/resumen` | Gastos del mes actual por categoría |
| `/presupuesto` | Estado vs presupuesto por categoría con semáforo |

## Deduplicación

Antes de guardar un gasto, se busca en las últimas 24h si hay otro con:
- Mismo store (case-insensitive)
- Mismo amount (±€0.50)
- Misma fecha

Si hay match, se pregunta al usuario con teclado inline antes de guardar.

## Flujo ticket para super

Cuando se registra un gasto con `category_slug == "super"`:
1. Bot pregunta: "¿Tenés foto del ticket?"
2. Si envía foto → extraer items, vincular ticket, guardar en ticket_items
3. Si dice "No" → continúa normalmente

## Categorías

```python
CATEGORY_SLUGS = [
    "vivienda", "super", "salud", "servicios", "vacaciones",
    "salidas", "casa", "transporte", "ocio", "ropa", "educacion",
]
```

## Teclado inline post-registro

- Editar categoría → muestra todas las categorías
- Editar importe → pide nuevo monto por texto
- Eliminar → borra el gasto
