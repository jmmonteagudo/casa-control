# Roadmap

## Fase 1 — Reorganización del repo + documentación
- [x] Crear `docs/` con documentación completa
- [x] Crear `CLAUDE.md` en raíz
- [x] Mover bot a `bot/`, eliminar `files.zip`
- [x] Configurar Railway root directory a `bot/`

## Fase 2 — Bot de Telegram (COMPLETO)
- [x] Modularizar bot (config.py, llm.py, db.py, formatters.py)
- [x] Conversación inteligente (classify_and_process)
- [x] Deduplicación de gastos (check_duplicate)
- [x] Flujo ticket para super (pregunta foto después de registrar)
- [x] Logging producción (telegram.ext → WARNING)
- [x] Transcripción de audio — Groq Whisper
- [x] Comando /myid para obtener chat_id
- [x] Fix deploy: bot/bot.py launcher + allowed_updates en run_polling

## Fase 3 — App Web React (PWA) — parcialmente hecho
- [x] Setup webapp (Vite + React + TS + Tailwind + Supabase)
- [x] Dashboard con gauges por categoría
- [x] Historial de gastos con filtros y paginación
- [x] Presupuestos editables
- [ ] PWA manifest + service worker
- [x] Deploy en Vercel (casa-control-two.vercel.app)
- [ ] Fix login: verificar anon key en Vercel env vars + redeploy con cache clear

## Fase 4 — iOS Shortcut: entrada automática de gastos (EN DESARROLLO)
- [x] Shortcut "Gasto" funcional (envía POST a Telegram Bot API)
- [x] Automatización Cartera/Wallet activada (trigger "toque tarjeta")
- [x] Transaction trigger RESUELTO — tipo "Transacción" disponible con campos: Comercio, Importe, Nombre, Tarjeta
- [ ] Configurar anon key de Supabase + RLS policy para INSERT en expenses
- [ ] Armar Shortcut completo: extraer Comercio+Importe → mapear categoría → POST a Supabase
- [ ] Agregar notificación Telegram si categoría es "super" (pedir foto ticket)
- [ ] Probar con una transacción real de Apple Pay
- [ ] Mapeo de comercios a categorías (tabla en CLAUDE.md)

## Fase 5 — Features avanzados (webapp)
- [ ] Catálogo de productos (tabla editable, filtros, nutriscore)
- [ ] Planificador de compras (vista semanal por comercio)
- [ ] Historial de tickets con miniaturas
- [ ] Buscador de chollos (LLM estima mejor precio)

## Fase 6 — Features futuros
- [ ] Resumen automático semanal (cron Railway → mensaje domingos)
- [ ] GoCardless Open Banking (conexión directa con bancos — backup si iOS no es suficiente)
- [ ] Importación CSV bancario
- [ ] Life Goals / planificación financiera a largo plazo
