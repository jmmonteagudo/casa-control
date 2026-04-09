# Arquitectura

## Componentes

```
ENTRADA DE DATOS
├── Telegram Group (Martin + Romina + Bot)
│   ├── Foto de ticket → Groq Vision (llama-4-scout) → extrae productos y precios
│   ├── Audio de voz → Groq Whisper → transcribe → clasifica gasto
│   └── Texto libre → Groq (llama-3.3-70b) → interpreta → registra
│
├── iOS Shortcut "Gasto" (EN DESARROLLO — automatizar 100%)
│   ├── Trigger: pago con Apple Pay (Cartera/Wallet)
│   ├── Objetivo: extraer monto y comercio de la transacción automáticamente
│   ├── Vía A: POST a Telegram Bot API → bot clasifica y registra
│   └── Vía B: POST directo a Supabase REST API → insert en expenses
│
└── App Web (ordenador / móvil PWA)
    └── Dashboard, edición de gastos y presupuestos

PROCESAMIENTO
└── Bot Python en Railway (bot/)
    ├── Recibe input de Telegram
    ├── Clasifica intención (gasto / pregunta / fuera de scope)
    ├── Llama a Groq API para procesar
    ├── Escribe en Supabase
    └── Confirma al grupo con resumen + teclado inline

BASE DE DATOS
└── Supabase (PostgreSQL)
    ├── expenses          — gastos registrados
    ├── tickets           — fotos de tickets procesados
    ├── ticket_items      — items extraídos de tickets
    ├── budget_categories — presupuestos por categoría
    └── users             — usuarios (Martin, Romina)

VISUALIZACIÓN
└── App React en Vercel (webapp/)
    ├── Dashboard mensual con semáforo por categoría
    ├── Historial de gastos con filtros
    └── Presupuestos editables
```

## Stack técnico

| Pieza | Tecnología | Hosting | Coste |
|---|---|---|---|
| Bot Telegram | Python + python-telegram-bot | Railway | ~$5 crédito/mes |
| App web | React + TypeScript + Vite + Tailwind | Vercel | Gratis |
| Base de datos | PostgreSQL | Supabase | Gratis |
| Auth | Supabase Auth | Supabase | Gratis |
| Storage fotos | Supabase Storage | Supabase | Gratis |
| LLM texto | Groq llama-3.3-70b-versatile | Groq | Gratis |
| LLM visión | Groq llama-4-scout-17b-16e-instruct | Groq | Gratis |
| Audio | Groq whisper-large-v3-turbo | Groq | Gratis |

## Monorepo

Un solo repo `casa-control`:
- Railway deploya `bot/` (Settings > Root Directory = `bot/`)
- Vercel deploya `webapp/` (Settings > Root Directory = `webapp/`)

## Variables de entorno (Railway)

- `TELEGRAM_TOKEN` — Token del bot de Telegram
- `GROQ_API_KEY` — API key de Groq
- `SUPABASE_URL` — URL del proyecto Supabase
- `SUPABASE_SERVICE_KEY` — Service role key de Supabase
- `ALLOWED_CHAT_IDS` — IDs de chats/usuarios autorizados (comma-separated)
