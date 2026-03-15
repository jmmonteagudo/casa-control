# CasaControl

Sistema de gestión financiera familiar para Martin y Romina (Madrid).

## Stack

| Componente | Tecnología | Hosting |
|---|---|---|
| Bot Telegram | Python (python-telegram-bot) | Railway |
| App web | React + TypeScript + Vite + Tailwind | Vercel |
| Base de datos | PostgreSQL (Supabase) | Supabase |
| Auth | Supabase Auth | Supabase |
| Storage | Supabase Storage (fotos tickets) | Supabase |
| LLM texto | Groq — llama-3.3-70b-versatile | Groq (gratis) |
| LLM visión | Groq — llama-4-scout-17b-16e-instruct | Groq (gratis) |
| Audio | Groq Whisper — whisper-large-v3-turbo | Groq (gratis) |

## Estructura del repo

```
casa-control/
├── CLAUDE.md
├── docs/              # Documentación del proyecto
├── bot/               # Bot de Telegram (Python) — deploy Railway
│   ├── bot.py         # Handlers + main
│   ├── config.py      # Env vars, categorías, constantes
│   ├── llm.py         # Llamadas a Groq (texto, visión, audio)
│   ├── db.py          # Operaciones Supabase
│   ├── formatters.py  # Formateo de mensajes y teclados
│   ├── Procfile       # Railway worker
│   └── requirements.txt
└── webapp/            # App web React (PWA) — deploy Vercel
```

## Base de datos

Tablas en inglés: `expenses`, `tickets`, `ticket_items`, `budget_categories`, `users`.
Ver esquema completo en `docs/database.md`.

## Categorías de gastos

`vivienda`, `super`, `salud`, `servicios`, `vacaciones`, `salidas`, `casa`, `transporte`, `ocio`, `ropa`, `educacion`

## Convenciones

- Código del bot en español (mensajes al usuario) pero variables/funciones en inglés
- Env vars: TELEGRAM_TOKEN, GROQ_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, ALLOWED_CHAT_IDS
- Railway deploya `bot/` (root directory = bot/)
- Vercel deploya `webapp/` (root directory = webapp/)
- Documentación detallada en `docs/`
