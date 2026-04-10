-- CasaControl — Database initialization SQL
-- Execute this in Supabase SQL Editor to set up the database from scratch.

-- =========================================================================
-- 1. Core tables
-- =========================================================================

CREATE TABLE IF NOT EXISTS users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         text UNIQUE,
  telegram_id   bigint UNIQUE,
  name          text,
  created_at    timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS budget_categories (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          text UNIQUE NOT NULL,
  label         text NOT NULL,
  budget_eur    numeric(10,2) NOT NULL DEFAULT 0,
  created_at    timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS expenses (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  date            date NOT NULL,
  description     text NOT NULL,
  amount_eur      numeric(10,2) NOT NULL,
  category_slug   text NOT NULL,
  payment_method  text,
  store           text,
  source          text DEFAULT 'telegram',
  user_id         uuid REFERENCES users(id),
  ticket_id       uuid,
  needs_review    boolean NOT NULL DEFAULT false,
  notes           text,
  bank_ref        text,
  created_at      timestamptz DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_expenses_bank_ref
  ON expenses(bank_ref) WHERE bank_ref IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_expenses_needs_review
  ON expenses(needs_review) WHERE needs_review = true;
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_slug);

CREATE TABLE IF NOT EXISTS tickets (
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

CREATE TABLE IF NOT EXISTS ticket_items (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id       uuid REFERENCES tickets(id) ON DELETE CASCADE,
  name            text NOT NULL,
  quantity        numeric(10,3) DEFAULT 1,
  unit_price      numeric(10,2),
  total_price     numeric(10,2),
  category_slug   text,
  created_at      timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recurring_expenses (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  description     text NOT NULL,
  amount_eur      numeric(10,2) NOT NULL,
  category_slug   text NOT NULL,
  store           text,
  day_of_month    int DEFAULT 1,
  active          boolean DEFAULT true,
  created_at      timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS frequent_contacts (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name            text NOT NULL UNIQUE,
  category_slug   text NOT NULL,
  store_label     text,
  created_at      timestamptz DEFAULT now()
);

-- =========================================================================
-- 2. Default budget categories
-- =========================================================================

INSERT INTO budget_categories (slug, label, budget_eur) VALUES
  ('vivienda',       'Vivienda',        0),
  ('super',          'Supermercado',     0),
  ('salud',          'Salud',            0),
  ('servicios',      'Servicios',        0),
  ('vacaciones',     'Vacaciones',       0),
  ('salidas',        'Salidas',          0),
  ('casa',           'Casa/Hogar',       0),
  ('transporte',     'Transporte',       0),
  ('ocio',           'Ocio/Kids',        0),
  ('ropa',           'Ropa',             0),
  ('educacion',      'Educacion',        0),
  ('impuestos',      'Impuestos',        0),
  ('deportes',       'Deportes',         0),
  ('coche',          'Coche',            0),
  ('sin_clasificar', 'Sin clasificar',   0),
  ('otros',          'Otros',            0)
ON CONFLICT (slug) DO NOTHING;

-- =========================================================================
-- 3. Supabase Storage
-- =========================================================================
-- Create a public bucket called "tickets" from the Supabase dashboard:
--   Storage > New Bucket > Name: "tickets" > Public: ON

-- =========================================================================
-- 4. Supabase Auth
-- =========================================================================
-- From Authentication > Settings:
--   - Enable "Magic Link" sign-in
--   - Set Site URL to your webapp URL (e.g., https://your-app.vercel.app)
--   - Add allowed redirect URLs

-- =========================================================================
-- 5. RLS (Row Level Security) — optional
-- =========================================================================
-- By default, the webapp uses the anon key with no RLS.
-- For production, enable RLS and add policies. Example:
--
-- ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can read own expenses"
--   ON expenses FOR SELECT
--   USING (auth.uid() = user_id);
