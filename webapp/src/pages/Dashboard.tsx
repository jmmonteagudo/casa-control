import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Expense, BudgetCategory } from '../lib/supabase'
import CategoryGauge from '../components/CategoryGauge'
import ExpenseList from '../components/ExpenseList'

export default function Dashboard() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [budgets, setBudgets] = useState<BudgetCategory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const now = new Date()
    const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`

    Promise.all([
      supabase
        .from('expenses')
        .select('*')
        .gte('date', monthStart)
        .order('created_at', { ascending: false }),
      supabase
        .from('budget_categories')
        .select('*'),
    ]).then(([expRes, budRes]) => {
      setExpenses(expRes.data || [])
      setBudgets(budRes.data || [])
      setLoading(false)
    })
  }, [])

  if (loading) {
    return <p className="text-slate-500 text-center py-12">Cargando dashboard...</p>
  }

  // Compute spent per category
  const spentByCategory: Record<string, number> = {}
  let totalSpent = 0
  for (const exp of expenses) {
    const slug = exp.category_slug || 'super'
    spentByCategory[slug] = (spentByCategory[slug] || 0) + exp.amount_eur
    totalSpent += exp.amount_eur
  }

  const totalBudget = budgets.reduce((sum, b) => sum + b.budget_eur, 0)
  const totalPct = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0

  // Projection
  const now = new Date()
  const dayOfMonth = now.getDate()
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const projectedTotal = dayOfMonth > 0 ? (totalSpent / dayOfMonth) * daysInMonth : 0

  const totalBarColor =
    totalPct >= 90 ? 'bg-red-500' :
    totalPct >= 70 ? 'bg-amber-500' :
    'bg-emerald-500'

  return (
    <div className="space-y-6">
      {/* Global gauge */}
      <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-bold text-white">
            {now.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
          </h2>
          <span className="text-sm text-slate-400">
            Proyección: €{projectedTotal.toFixed(0)}
          </span>
        </div>
        <div className="flex items-end gap-2 mb-3">
          <span className="text-3xl font-bold text-white">€{totalSpent.toFixed(0)}</span>
          <span className="text-slate-500 text-sm pb-1">/ €{totalBudget.toFixed(0)}</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${totalBarColor}`}
            style={{ width: `${Math.min(totalPct, 100)}%` }}
          />
        </div>
      </div>

      {/* Category gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {budgets
          .sort((a, b) => (spentByCategory[b.slug] || 0) - (spentByCategory[a.slug] || 0))
          .map(b => (
            <CategoryGauge
              key={b.slug}
              slug={b.slug}
              spent={spentByCategory[b.slug] || 0}
              budget={b.budget_eur}
            />
          ))
        }
      </div>

      {/* Recent expenses */}
      <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Últimos movimientos</h3>
        <ExpenseList expenses={expenses.slice(0, 10)} />
      </div>
    </div>
  )
}
