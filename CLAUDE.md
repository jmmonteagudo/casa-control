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
│   ├── bot.py         # Launcher (Procfile ejecuta este)
│   ├── main.py        # Handlers + main()
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

## Credenciales del bot

- **Telegram Bot**: @hauscntrl987bot (token en Railway como TELEGRAM_TOKEN)
- **Chat ID Martin**: 6346673033
- **Supabase URL**: https://iughwrfnoiwqhbtufgbn.supabase.co
- **Webapp URL**: casa-control-two.vercel.app

## Entrada automática de gastos — iOS Shortcut (EN DESARROLLO)

### Objetivo
Registrar gastos 100% automático desde iPhone sin intervención manual al pagar con Apple Pay.

### Estado actual (2026-04-09)
- Existe un Shortcut "Gasto" funcional que envía POST a la API de Telegram Bot
- Endpoint: `https://api.telegram.org/bot<TOKEN>/sendMessage` con `chat_id=6346673033` y `text`
- El bot recibe el mensaje, clasifica con LLM y registra en Supabase
- Hay una automatización de "Cartera" (Wallet) que dispara el Shortcut al tocar una tarjeta
- PROBLEMA: la versión actual NO extrae datos de la transacción automáticamente

### Transaction trigger — RESUELTO (2026-04-09)

El tipo **"Transacción"** SÍ está disponible en iOS 26.2.1 beta. Aparece dentro de las acciones del Shortcut al configurar la variable "Entrada de atajo" cuando el trigger es "Cartera".

**Campos disponibles del tipo Transacción:**
- `Transacción` — objeto completo
- `Tarjeta o pase` — tarjeta usada
- `Comercio` — nombre del comercio (ej: "Mercadona")
- `Importe` — monto de la transacción
- `Nombre` — nombre de la transacción

**Cómo acceder:**
1. Automatización → trigger "Cartera" → seleccionar tarjeta(s)
2. Primera acción: "Recibir transacción como entrada"
3. Al tocar "Entrada de atajo" → Tipo → seleccionar "Transacción"
4. Luego usar "Obtener detalle de Entrada de atajo" para extraer Comercio, Importe, etc.

### Arquitectura del Shortcut — INSERT directo a Supabase

**Flujo:**
```
Apple Pay → trigger Cartera → Shortcut automático:
  1. Recibir transacción como entrada
  2. Extraer Comercio e Importe de la transacción
  3. Mapear comercio → category_slug (tabla hardcodeada)
  4. POST directo a Supabase REST API → insert en expenses
  5. (Si category == "super") → enviar mensaje Telegram pidiendo foto ticket
```

**POST a Supabase:**
- URL: `https://iughwrfnoiwqhbtufgbn.supabase.co/rest/v1/expenses`
- Método: POST
- Headers: `apikey: <ANON_KEY>`, `Authorization: Bearer <ANON_KEY>`, `Content-Type: application/json`, `Prefer: return=representation`
- Body: `{"date": "YYYY-MM-DD", "description": "[comercio]", "amount_eur": [importe], "category_slug": "[categoria]", "store": "[comercio]", "source": "shortcut", "payment_method": "apple_pay"}`

**Requiere:** anon key de Supabase + RLS policy que permita INSERT en expenses

### Vías de registro al resolver el trigger

**Vía A — Enviar mensaje al bot de Telegram (recomendada):**
- Shortcut envía `"[COMERCIO] [MONTO]€"` al bot via `POST https://api.telegram.org/bot<TOKEN>/sendMessage`
- Bot clasifica con LLM → registra en Supabase → si es super, pide foto ticket
- Pro: ya funciona, toda la lógica de clasificación está en el bot

**Vía B — Insert directo a Supabase REST API:**
- `POST https://iughwrfnoiwqhbtufgbn.supabase.co/rest/v1/expenses`
- Headers: `apikey: <SUPABASE_ANON_KEY>`, `Authorization: Bearer <SUPABASE_ANON_KEY>`
- Body: `{"date": "2026-04-09", "description": "Mercadona", "amount_eur": 45.30, "category_slug": "super", "store": "Mercadona", "source": "shortcut"}`
- Pro: más directo. Con: necesita mapear categoría en el Shortcut (sin LLM)

### Mapeo de categorías para Shortcut (si se usa Vía B)

| Palabra clave en comercio | category_slug |
|---|---|
| Mercadona, Lidl, Carrefour, Aldi, Dia, Alcampo, BM, Ahorramas | super |
| Farmacia, Hospital, Clínica, Dentista, Óptica | salud |
| Renfe, Metro, Cabify, Uber, Gasolina, BP, Repsol | transporte |
| Zara, H&M, Primark, Mango, Nike | ropa |
| Bar, Restaurante, Café, Burger, Pizza, McDonald | salidas |
| Netflix, Spotify, Amazon, Steam, Cine | ocio |
| Ikea, Leroy Merlin, Bricomart, Ferretería | casa |
| Vodafone, Movistar, Orange, Endesa, Iberdrola, Naturgy, Agua | servicios |
| Booking, Airbnb, Vueling, Ryanair, Hotel | vacaciones |
| Default (no match) | super |

### Esquema de la tabla expenses (para referencia en Shortcut)

```sql
-- Campos requeridos para insert:
date           -- formato: "YYYY-MM-DD"
description    -- texto libre, ej: "Mercadona compra semanal"
amount_eur     -- número decimal, ej: 45.30
category_slug  -- uno de: vivienda, super, salud, servicios, vacaciones, salidas, casa, transporte, ocio, ropa, educacion
-- Campos opcionales:
store          -- nombre del comercio
source         -- "shortcut" para identificar origen
payment_method -- "apple_pay"
user_id        -- uuid de Martin en tabla users (se puede omitir)
```

### Contexto técnico
- iPhone con iOS 26.2.1 (beta developer)
- Apple Pay con tarjetas CaixaBank
- La app Cartera envía notificación post-pago con formato "Pago de XX,XX € en COMERCIO"
- Shortcut "Gasto" ya existe (versión manual, funciona)
- Automatización Cartera configurada como trigger
- Video referencia: https://www.youtube.com/watch?v=9Q67BMZ7BEM (iOS 18, muestra Transaction type funcionando)
