# Roadmap

## Fase 1 — Reorganización del repo + documentación
- [x] Crear `docs/` con documentación completa
- [x] Crear `CLAUDE.md` en raíz
- [x] Mover bot a `bot/`, eliminar `files.zip`
- [ ] Configurar Railway root directory a `bot/` (manual en dashboard)

## Fase 2 — Mejoras al Bot
- [x] Modularizar bot (config.py, llm.py, db.py, formatters.py)
- [x] Conversación inteligente (classify_and_process)
- [x] Deduplicación de gastos (check_duplicate)
- [x] Flujo ticket para super
- [x] Logging producción (telegram.ext → WARNING)

## Fase 3 — App Web React (PWA)
- [ ] Setup webapp (Vite + React + TS + Tailwind + Supabase)
- [ ] Dashboard con gauges por categoría
- [ ] Historial de gastos con filtros
- [ ] Presupuestos editables
- [ ] PWA manifest + service worker
- [ ] Deploy en Vercel

## Fase 4 — Features avanzados
- [ ] Catálogo de productos (webapp)
- [ ] Planificador de compras (webapp)
- [ ] Transcripción de audio — Groq Whisper (bot)
- [ ] Importación CSV bancario (bot + webapp)

## Fase 5 — Features futuros
- [ ] Historial de tickets con miniaturas en webapp
- [ ] Buscador de chollos (LLM estima mejor precio)
- [ ] Resumen automático semanal (cron Railway → mensaje domingos)
- [ ] GoCardless Open Banking (conexión directa con bancos)
