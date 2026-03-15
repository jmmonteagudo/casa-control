# Base de datos

Supabase PostgreSQL. Todas las tablas usan nombres en inglés.

## Tablas

### expenses
```sql
CREATE TABLE expenses (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  date            date NOT NULL,
  description     text NOT NULL,
  amount_eur      numeric(10,2) NOT NULL,
  category_slug   text NOT NULL,
  payment_method  text,
  store           text,
  source          text,          -- 'telegram', 'web', 'csv'
  user_id         uuid REFERENCES users(id),
  ticket_id       uuid REFERENCES tickets(id),
  notes           text,
  created_at      timestamptz DEFAULT now()
);
```

### tickets
```sql
CREATE TABLE tickets (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  date              date,
  store             text,
  total_eur         numeric(10,2),
  image_url         text,
  status            text DEFAULT 'confirmed',
  telegram_msg_id   bigint,
  telegram_chat_id  bigint,
  user_id           uuid REFERENCES users(id),
  created_at        timestamptz DEFAULT now()
);
```

### ticket_items
```sql
CREATE TABLE ticket_items (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id       uuid REFERENCES tickets(id),
  name            text NOT NULL,
  quantity         numeric(10,3) DEFAULT 1,
  unit_price       numeric(10,2),
  total_price      numeric(10,2),
  category_slug    text,
  created_at       timestamptz DEFAULT now()
);
```

### budget_categories
```sql
CREATE TABLE budget_categories (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug        text UNIQUE NOT NULL,
  label       text NOT NULL,
  budget_eur  numeric(10,2) NOT NULL
);
```

Presupuestos iniciales:

| Slug | Label | Budget €/mes |
|---|---|---|
| vivienda | Vivienda | 1.430 |
| super | Supermercado | 800 |
| salud | Salud | 260 |
| servicios | Servicios | 250 |
| vacaciones | Vacaciones | 500 |
| salidas | Salidas | 250 |
| casa | Casa/Hogar | 200 |
| transporte | Transporte | 150 |
| ocio | Ocio/Kids | 150 |
| ropa | Ropa | 100 |
| educacion | Educación | 100 |

### users
```sql
CREATE TABLE users (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name         text NOT NULL,
  telegram_id  bigint UNIQUE,
  created_at   timestamptz DEFAULT now()
);
```

## Storage

Bucket `tickets` en Supabase Storage para fotos de tickets.
Path: `tickets/{timestamp}_{file_unique_id}.jpg`
