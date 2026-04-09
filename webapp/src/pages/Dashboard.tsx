import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Expense, BudgetCategory } from '../lib/supabase'
import { useMonth } from '../context/MonthContext'
import CategoryGauge from '../components/CategoryGauge'
import ExpenseList from '../components/ExpenseList'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer,
} from 'recharts'

const CATEGORY_COLORS: Record<string, string> = {
  vivienda: '#6366f1',   // indigo
  super: '#10b981',      // emerald
  salud: '#f43f5e',      // rose
  servicios: '#f59e0b',  // amber
  vacaciones: '#06b6d4', // cyan
  salidas: '#ec4899',    // pink
  casa: '#8b5cf6',       // violet
  transporte: '#3b82f6', // blue
  ocio: '#14b8a6',       // teal
  ropa: '#d946ef',       // fuchsia
  educacion: '#f97316',  // orange
  otros: '#64748b',      // slate
}

export default function Dashboard() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [budgets, setBudgets] = useState<BudgetCategory[]>([])
  const [loading, setLoading] = useState(true)
  const { monthStart, monthEnd, isCurrentMonth, prevMonth, nextMonth, year, month, setYear, setMonth } = useMonth()

  const MONTHS = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ]
  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth()
  const years = Array.from({ length: currentYear - 2022 }, (_, i) => currentYear - i)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      supabase
        .from('expenses')
        .select('*')
        .gte('date', monthStart)
        .lte('date', monthEnd)
        .order('created_at', { ascending: false }),
      supabase
        .from('budget_categories')
        .select('*'),
    ]).then(([expRes, budRes]) => {
      setExpenses(expRes.data || [])
      setBudgets(budRes.data || [])
      setLoading(false)
    })
  }, [monthStart, monthEnd])

  if (loading) {
    return <p className="text-slate-500 text-center py-12">Cargando dashboard...</p>
  }

  // Compute spent per category
  const spentByCategory: Record<string, number> = {}
  let totalSpent = 0
  for (const exp of expenses) {
    const slug = exp.category_slug || 'otros'
    spentByCategory[slug] = (spentByCategory[slug] || 0) + exp.amount_eur
    totalSpent += exp.amount_eur
  }

  const totalBudget = budgets.reduce((sum, b) => sum + b.budget_eur, 0)
  const totalPct = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0

  // Projection (only for current month)
  const now = new Date()
  const dayOfMonth = now.getDate()
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const projectedTotal = isCurrentMonth && dayOfMonth > 0
    ? (totalSpent / dayOfMonth) * daysInMonth
    : null

  const totalBarColor =
    totalPct >= 90 ? 'bg-red-500' :
    totalPct >= 70 ? 'bg-amber-500' :
    'bg-emerald-500'

  // Pie chart data
  const pieData = Object.entries(spentByCategory)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([slug, amount]) => ({
      name: slug,
      value: Math.round(amount * 100) / 100,
    }))

  // Bar chart: daily spending
  const dailySpend: Record<number, number> = {}
  for (const exp of expenses) {
    const day = parseInt(exp.date.split('-')[2], 10)
    dailySpend[day] = (dailySpend[day] || 0) + exp.amount_eur
  }
  const barData = Object.entries(dailySpend)
    .map(([day, amount]) => ({ day: parseInt(day, 10), amount: Math.round(amount * 100) / 100 }))
    .sort((a, b) => a.day - b.day)

  return (
    <div className="space-y-6">
      {/* Global gauge with month selector */}
      <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <button
              onClick={prevMonth}
              className="text-slate-400 hover:text-white text-lg font-bold px-1 transition-colors"
            >
              &lt;
            </button>
            <select
              value={month}
              onChange={e => {
                const m = parseInt(e.target.value, 10)
                if (year === currentYear && m > currentMonth) return
                setMonth(m)
              }}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-sm font-bold text-white"
            >
              {MONTHS.map((name, i) => (
                <option key={i} value={i} disabled={year === currentYear && i > currentMonth}>
                  {name}
                </option>
              ))}
            </select>
            <select
              value={year}
              onChange={e => {
                const y = parseInt(e.target.value, 10)
                setYear(y)
                if (y === currentYear && month > currentMonth) setMonth(currentMonth)
              }}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-sm font-bold text-white"
            >
              {years.map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <button
              onClick={nextMonth}
              disabled={isCurrentMonth}
              className="text-slate-400 hover:text-white text-lg font-bold px-1 transition-colors disabled:opacity-20 disabled:cursor-not-allowed"
            >
              &gt;
            </button>
          </div>
          {projectedTotal !== null && (
            <span className="text-sm text-slate-400">
              Proyeccion: &euro;{projectedTotal.toFixed(0)}
            </span>
          )}
        </div>
        <div className="flex items-end gap-2 mb-3">
          <span className="text-3xl font-bold text-white">&euro;{totalSpent.toFixed(0)}</span>
          <span className="text-slate-500 text-sm pb-1">/ &euro;{totalBudget.toFixed(0)}</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${totalBarColor}`}
            style={{ width: `${Math.min(totalPct, 100)}%` }}
          />
        </div>
      </div>

      {/* Charts row */}
      {pieData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Pie chart */}
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Distribucion por categoria</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] || '#64748b'} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => [`€${Number(value).toFixed(0)}`, '']}
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                  itemStyle={{ color: '#e2e8f0' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-2 mt-2">
              {pieData.map((entry) => (
                <div key={entry.name} className="flex items-center gap-1.5 text-xs text-slate-400">
                  <div
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: CATEGORY_COLORS[entry.name] || '#64748b' }}
                  />
                  <span>{entry.name}</span>
                  <span className="text-slate-500">&euro;{entry.value.toFixed(0)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bar chart */}
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Gasto diario</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={barData}>
                <XAxis
                  dataKey="day"
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={{ stroke: '#334155' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `€${v}`}
                />
                <Tooltip
                  formatter={(value) => [`€${Number(value).toFixed(2)}`, 'Gasto']}
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                  itemStyle={{ color: '#e2e8f0' }}
                  labelFormatter={(day) => `Dia ${day}`}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Bar dataKey="amount" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

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
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Ultimos movimientos</h3>
        <ExpenseList expenses={expenses.slice(0, 10)} />
      </div>
    </div>
  )
}
