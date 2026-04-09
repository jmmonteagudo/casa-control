import type { Expense } from '../lib/supabase'

const CATEGORY_ICONS: Record<string, string> = {
  vivienda: '🏡', super: '🛒', salud: '🏥', servicios: '💡',
  vacaciones: '✈️', salidas: '🍽️', casa: '🏠', transporte: '🚗',
  ocio: '🎈', ropa: '👗', educacion: '📚', otros: '📦',
}

type Props = {
  expenses: Expense[]
  onEdit?: (expense: Expense) => void
}

export default function ExpenseList({ expenses, onEdit }: Props) {
  if (expenses.length === 0) {
    return <p className="text-slate-500 text-sm text-center py-8">No hay gastos registrados.</p>
  }

  return (
    <div className="divide-y divide-slate-800">
      {expenses.map(expense => (
        <div
          key={expense.id}
          className="flex items-center justify-between py-3 hover:bg-slate-900/50 px-2 rounded-lg cursor-pointer transition-colors"
          onClick={() => onEdit?.(expense)}
        >
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-lg flex-shrink-0">
              {CATEGORY_ICONS[expense.category_slug] || '📦'}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate">
                {expense.description}
              </p>
              <p className="text-xs text-slate-500">
                {expense.store || '—'} · {expense.date}
              </p>
            </div>
          </div>
          <span className="text-sm font-bold text-white ml-4 flex-shrink-0">
            €{expense.amount_eur.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  )
}
