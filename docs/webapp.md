# App Web

## Stack

React + TypeScript + Vite + Tailwind CSS + Supabase JS

## Secciones

### Dashboard
- Gauge global: gastado vs presupuesto total del mes
- Cards por categoría con barra de progreso + semáforo (verde <70%, ámbar 70-90%, rojo >90%)
- Proyección a fin de mes basada en ritmo actual
- Últimos 10 movimientos
- Responsive: en móvil cards apiladas, en desktop grid 3 columnas

### Historial de gastos
- Tabla paginada con filtros: categoría, rango de fechas, tienda
- Click para ver detalle + ticket asociado
- Edición inline de categoría y monto

### Presupuestos
- Tabla editable por categoría
- Barra de progreso mensual con semáforo

## Auth

Supabase Auth — solo Martin y Romina tienen acceso.

## PWA

- `manifest.json` para instalación en móvil
- Service worker para cache offline básico
- Instalable desde Safari (iOS) y Chrome (Android)

## Deploy

Vercel con root directory = `webapp/`.

## Estructura

```
webapp/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── public/
│   └── manifest.json
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── lib/supabase.ts
    ├── pages/
    │   ├── Dashboard.tsx
    │   ├── Expenses.tsx
    │   └── Budget.tsx
    └── components/
        ├── Layout.tsx
        ├── CategoryGauge.tsx
        └── ExpenseList.tsx
```
