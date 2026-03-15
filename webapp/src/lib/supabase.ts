import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export type Expense = {
  id: string
  date: string
  description: string
  amount_eur: number
  category_slug: string
  payment_method: string | null
  store: string | null
  source: string
  user_id: string | null
  ticket_id: string | null
  created_at: string
}

export type BudgetCategory = {
  id: string
  slug: string
  label: string
  budget_eur: number
}
