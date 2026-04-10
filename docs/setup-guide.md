# CasaControl — Setup Guide

Complete guide to deploy CasaControl from scratch.

## Prerequisites

- Node.js 18+ (for the webapp)
- Python 3.11+ (for the bot)
- Git

## 1. Supabase (Database + Auth + Storage)

1. Create a free project at [supabase.com](https://supabase.com)
2. From **Settings > API**, copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY` (for the webapp)
   - `service_role` key → `SUPABASE_SERVICE_KEY` (for the bot — keep secret)
3. Go to **SQL Editor** and run the full schema from [`docs/init.sql`](./init.sql)
4. Go to **Authentication > Settings**:
   - Enable **Magic Link** sign-in
   - Set **Site URL** to your webapp URL
5. Go to **Storage**:
   - Create a **public** bucket named `tickets`

## 2. Telegram Bot

1. Open Telegram, message [@BotFather](https://t.me/BotFather)
2. `/newbot` → follow prompts → copy the **token** → `TELEGRAM_TOKEN`
3. To get your Chat ID:
   - Deploy the bot (step 4 below)
   - Send `/myid` to your bot
   - Copy the Chat ID → add to `ALLOWED_CHAT_IDS`
4. Optional: create a **group** for family members
   - Add the bot to the group
   - Get the group's Chat ID (negative number) → `GROUP_CHAT_ID`

## 3. Groq (LLM for classification)

1. Register at [console.groq.com](https://console.groq.com)
2. Go to **API Keys** → create a key → `GROQ_API_KEY`
3. Free tier is sufficient for personal use

## 4. Railway (Bot hosting)

1. Sign up at [railway.app](https://railway.app)
2. **New Project** → Deploy from GitHub repo
3. Set **Root Directory** to `bot/`
4. Add environment variables:

| Variable | Value |
|---|---|
| `TELEGRAM_TOKEN` | From BotFather |
| `GROQ_API_KEY` | From Groq console |
| `SUPABASE_URL` | From Supabase Settings > API |
| `SUPABASE_SERVICE_KEY` | From Supabase Settings > API (service_role key) |
| `ALLOWED_CHAT_IDS` | Comma-separated Telegram Chat IDs |
| `GROUP_CHAT_ID` | Group chat ID (optional, negative number) |

5. Railway will auto-deploy on push

## 5. Vercel (Webapp hosting)

1. Sign up at [vercel.com](https://vercel.com)
2. **Import Project** → select the GitHub repo
3. Set **Root Directory** to `webapp/`
4. Add environment variables:

| Variable | Value |
|---|---|
| `VITE_SUPABASE_URL` | Same as `SUPABASE_URL` |
| `VITE_SUPABASE_ANON_KEY` | The anon/public key from Supabase |

5. Deploy. Set up a custom domain if desired.

## 6. Create a user

1. Open the webapp URL
2. Enter your email → you'll receive a magic link
3. Click the link to log in
4. In Supabase **Table Editor > users**, update your row:
   - Set `telegram_id` to your Telegram Chat ID
   - This links your bot messages to your webapp user

## 7. iOS Shortcut (optional — automatic Apple Pay tracking)

For automatic expense tracking when paying with Apple Pay:

1. Open the **Shortcuts** app on iPhone
2. Create a new Shortcut triggered by **Wallet** (after payment)
3. The shortcut should:
   - Extract **Merchant** and **Amount** from the transaction
   - Send a POST request to the Telegram Bot API:
     ```
     POST https://api.telegram.org/bot<TOKEN>/sendMessage
     Body: {"chat_id": "<YOUR_CHAT_ID>", "text": "[shortcut] <Merchant> <Amount>€"}
     ```
4. The bot will classify and register the expense automatically

Alternative: POST directly to Supabase REST API (see CLAUDE.md for details).

## Environment Variables Summary

| Variable | Service | Where to find |
|---|---|---|
| `TELEGRAM_TOKEN` | Telegram | @BotFather |
| `GROQ_API_KEY` | Groq | console.groq.com > API Keys |
| `SUPABASE_URL` | Supabase | Settings > API > URL |
| `SUPABASE_SERVICE_KEY` | Supabase | Settings > API > service_role key |
| `SUPABASE_ANON_KEY` | Supabase | Settings > API > anon key |
| `ALLOWED_CHAT_IDS` | Telegram | /myid command (comma-separated) |
| `GROUP_CHAT_ID` | Telegram | Group chat ID (optional) |
| `VITE_SUPABASE_URL` | Supabase | Same as SUPABASE_URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase | Same as SUPABASE_ANON_KEY |

## Default Categories

The system comes with 16 pre-configured expense categories:

| Slug | Label | Icon |
|---|---|---|
| vivienda | Vivienda | 🏡 |
| super | Supermercado | 🛒 |
| salud | Salud | 🏥 |
| servicios | Servicios | 💡 |
| vacaciones | Vacaciones | ✈️ |
| salidas | Salidas | 🍽️ |
| casa | Casa/Hogar | 🏠 |
| transporte | Transporte | 🚇 |
| ocio | Ocio/Kids | 🎈 |
| ropa | Ropa | 👗 |
| educacion | Educacion | 📚 |
| impuestos | Impuestos | 🏛️ |
| deportes | Deportes | 🏋️ |
| coche | Coche | 🚘 |
| sin_clasificar | Sin clasificar | ❓ |
| otros | Otros | 📦 |

Categories can be added, renamed, or adjusted from the webapp (Presupuesto > + Categoria).

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Show help |
| `/resumen` | Monthly expense summary |
| `/presupuesto` | Budget status |
| `/pendientes` | Expenses needing classification |
| `/recurrentes` | List recurring fixed expenses |
| `/recurrente` | Add a recurring expense |
| `/borrar_recurrente` | Deactivate a recurring expense |
| `/myid` | Show your Telegram Chat ID |
