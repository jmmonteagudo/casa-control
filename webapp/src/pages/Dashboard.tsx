import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import type { Expense, BudgetCategory } from '../lib/supabase'
import { useMonth } from '../context/MonthContext'
import CategoryGauge from '../components/CategoryGauge'
import { CATEGORY_COLORS } from '../lib/categories'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function Dashboard() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [budgets, setBudgets] = useState<BudgetCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [pendingCount, setPendingCount] = useState(0)
  const navigate = useNavigate()
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
    supabase
      .from('expenses')
      .select('id', { count: 'exact', head: true })
      .eq('needs_review', true)
      .then(({ count }) => setPendingCount(count || 0))
  }, [monthStart, monthEnd])

  if (loading) {
    return <p className="text-slate-500 text-center py-12">Cargando dashboard...</p>
  }

  const spentByCategory: Record<string, number> = {}
  let totalSpent = 0
  for (const exp of expenses) {
    const slug = exp.category_slug || 'otros'
    spentByCategory[slug] = (spentByCategory[slug] || 0) + exp.amount_eur
    totalSpent += exp.amount_eur
  }

  const totalBudget = budgets.reduce((sum, b) => sum + b.budget_eur, 0)
  const totalPct = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0

  const now = new Date()
  const dayOfMonth = now.getDate()
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const projectedTotal = isCurrentMonth && dayOfMonth > 0
    ? (totalSpent / dayOfMonth) * daysInMonth
    : null

  const totalBarColor =
    totalPct >= 90 ? 'bg-brand-red' :
    totalPct >= 70 ? 'bg-brand-orange' :
    'bg-brand-green'

  const pieData = Object.entries(spentByCategory)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([slug, amount]) => ({
      name: slug,
      value: Math.round(amount * 100) / 100,
    }))

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
      {/* Pending review alert */}
      {pendingCount > 0 && (
        <button
          onClick={() => navigate('/gastos?pending=true')}
          className="w-full bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-center justify-between hover:bg-amber-500/20 transition-colors"
        >
          <span className="text-sm text-amber-300 font-medium">
            {pendingCount} {pendingCount === 1 ? 'gasto sin clasificar' : 'gastos sin clasificar'}
          </span>
          <span className="text-xs text-amber-400">Revisar &rarr;</span>
        </button>
      )}

      {/* Header with month selector and full-width progress */}
      <div className="bg-navy-light rounded-xl p-6 border border-navy-lighter">
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
              className="bg-navy border border-navy-lighter rounded-lg px-2 py-1 text-sm font-bold text-white"
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
              className="bg-navy border border-navy-lighter rounded-lg px-2 py-1 text-sm font-bold text-white"
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
        <div className="w-full bg-navy rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${totalBarColor}`}
            style={{ width: `${Math.min(totalPct, 100)}%` }}
          />
        </div>
      </div>

      {/* Charts */}
      {pieData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
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
                  contentStyle={{ backgroundColor: '#1e2336', border: '1px solid #2a2f45', borderRadius: '8px' }}
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

          <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Gasto diario</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={barData}>
                <XAxis
                  dataKey="day"
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={{ stroke: '#2a2f45' }}
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
                  contentStyle={{ backgroundColor: '#1e2336', border: '1px solid #2a2f45', borderRadius: '8px' }}
                  itemStyle={{ color: '#e2e8f0' }}
                  labelFormatter={(day) => `Dia ${day}`}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Bar dataKey="amount" fill="#3BB2AC" radius={[4, 4, 0, 0]} />
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
    </div>
  )
}
