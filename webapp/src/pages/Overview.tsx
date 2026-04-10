import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { CATEGORIES, CATEGORY_COLORS } from '../lib/categories'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, AreaChart, Area,
} from 'recharts'

type MonthData = {
  month: string
  total: number
  [category: string]: number | string
}

export default function Overview() {
  const [data, setData] = useState<MonthData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase
      .from('expenses')
      .select('date, amount_eur, category_slug')
      .order('date')
      .then(({ data: rows }) => {
        if (!rows) { setLoading(false); return }

        const byMonth: Record<string, Record<string, number>> = {}
        for (const row of rows) {
          const m = row.date.slice(0, 7)
          if (!byMonth[m]) byMonth[m] = {}
          const cat = row.category_slug || 'otros'
          byMonth[m][cat] = (byMonth[m][cat] || 0) + row.amount_eur
        }

        const months = Object.keys(byMonth).sort()
        const result: MonthData[] = months.map(m => {
          const cats = byMonth[m]
          const total = Object.values(cats).reduce((s, v) => s + v, 0)
          return { month: m, total: Math.round(total), ...cats }
        })

        setData(result)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return <p className="text-slate-500 text-center py-12">Cargando resumen...</p>
  }

  if (data.length === 0) {
    return <p className="text-slate-500 text-center py-12">No hay datos.</p>
  }

  const allTimeTotal = data.reduce((s, d) => s + d.total, 0)
  const monthlyAvg = allTimeTotal / data.length
  const currentMonth = new Date().toISOString().slice(0, 7)
  const currentMonthData = data.find(d => d.month === currentMonth)
  const currentVsAvg = currentMonthData
    ? ((currentMonthData.total - monthlyAvg) / monthlyAvg) * 100
    : null
  const maxMonth = data.reduce((max, d) => d.total > max.total ? d : max, data[0])

  // Category totals all-time
  const catTotals: Record<string, number> = {}
  for (const d of data) {
    for (const cat of CATEGORIES) {
      const val = d[cat.slug]
      if (typeof val === 'number') {
        catTotals[cat.slug] = (catTotals[cat.slug] || 0) + val
      }
    }
  }
  const topCategories = Object.entries(catTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)

  // Top 5 categories for stacked area
  const top5Cats = Object.entries(catTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([slug]) => slug)

  // Annual comparison
  const yearTotals: Record<number, number> = {}
  for (const d of data) {
    const y = parseInt(d.month.slice(0, 4))
    yearTotals[y] = (yearTotals[y] || 0) + d.total
  }
  const years = Object.keys(yearTotals).map(Number).sort()

  const formatMonth = (m: string) => {
    const [, mm] = m.split('-')
    const names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    return names[parseInt(mm) - 1] || mm
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-bold text-white">Resumen general</h2>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
          <p className="text-xs text-slate-500">Total gastado</p>
          <p className="text-xl font-bold text-white">&euro;{allTimeTotal.toFixed(0)}</p>
          <p className="text-xs text-slate-500">{data.length} meses</p>
        </div>
        <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
          <p className="text-xs text-slate-500">Media mensual</p>
          <p className="text-xl font-bold text-white">&euro;{monthlyAvg.toFixed(0)}</p>
        </div>
        <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
          <p className="text-xs text-slate-500">Mes actual vs media</p>
          {currentVsAvg !== null ? (
            <p className={`text-xl font-bold ${currentVsAvg > 0 ? 'text-brand-red' : 'text-brand-green'}`}>
              {currentVsAvg > 0 ? '+' : ''}{currentVsAvg.toFixed(0)}%
            </p>
          ) : (
            <p className="text-xl font-bold text-slate-500">-</p>
          )}
        </div>
        <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
          <p className="text-xs text-slate-500">Mes mas caro</p>
          <p className="text-xl font-bold text-white">&euro;{maxMonth.total.toFixed(0)}</p>
          <p className="text-xs text-slate-500">{maxMonth.month}</p>
        </div>
      </div>

      {/* Annual comparison */}
      {years.length > 1 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {years.map((y, i) => {
            const prev = i > 0 ? yearTotals[years[i - 1]] : null
            const pctChange = prev ? ((yearTotals[y] - prev) / prev) * 100 : null
            return (
              <div key={y} className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
                <p className="text-xs text-slate-500">{y}</p>
                <p className="text-xl font-bold text-white">&euro;{yearTotals[y].toFixed(0)}</p>
                {pctChange !== null && (
                  <p className={`text-xs ${pctChange > 0 ? 'text-brand-red' : 'text-brand-green'}`}>
                    {pctChange > 0 ? '+' : ''}{pctChange.toFixed(0)}% vs {years[i - 1]}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Monthly trend bar chart */}
      <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Gasto mensual</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2f45" />
            <XAxis
              dataKey="month"
              tickFormatter={formatMonth}
              tick={{ fill: '#64748b', fontSize: 10 }}
              axisLine={{ stroke: '#2a2f45' }}
              tickLine={false}
              interval={Math.max(0, Math.floor(data.length / 12) - 1)}
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip
              formatter={(value) => [`\u20AC${Number(value).toFixed(0)}`, 'Total']}
              labelFormatter={(label) => label}
              contentStyle={{ backgroundColor: '#1e2336', border: '1px solid #2a2f45', borderRadius: '8px' }}
              itemStyle={{ color: '#e2e8f0' }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <ReferenceLine y={monthlyAvg} stroke="#F8AD55" strokeDasharray="5 5" label="" />
            <Bar
              dataKey="total"
              radius={[3, 3, 0, 0]}
              fill="#3BB2AC"
            />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-slate-500 mt-1">Linea: media mensual (&euro;{monthlyAvg.toFixed(0)})</p>
      </div>

      {/* Stacked area by top 5 categories */}
      <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Composicion por categoria (top 5)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2f45" />
            <XAxis
              dataKey="month"
              tickFormatter={formatMonth}
              tick={{ fill: '#64748b', fontSize: 10 }}
              axisLine={{ stroke: '#2a2f45' }}
              tickLine={false}
              interval={Math.max(0, Math.floor(data.length / 12) - 1)}
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip
              formatter={(value) => [`\u20AC${Number(value).toFixed(0)}`, '']}
              contentStyle={{ backgroundColor: '#1e2336', border: '1px solid #2a2f45', borderRadius: '8px' }}
              itemStyle={{ color: '#e2e8f0' }}
              labelStyle={{ color: '#94a3b8' }}
            />
            {top5Cats.map(slug => (
              <Area
                key={slug}
                type="monotone"
                dataKey={slug}
                stackId="1"
                fill={CATEGORY_COLORS[slug] || '#64748b'}
                stroke={CATEGORY_COLORS[slug] || '#64748b'}
                fillOpacity={0.6}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
        <div className="flex flex-wrap gap-3 mt-2">
          {top5Cats.map(slug => {
            const cat = CATEGORIES.find(c => c.slug === slug)
            return (
              <div key={slug} className="flex items-center gap-1.5 text-xs text-slate-400">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[slug] }} />
                <span>{cat?.icon} {cat?.label || slug}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Top categories all-time */}
      <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Top categorias (historico)</h3>
        <div className="space-y-2">
          {topCategories.map(([slug, total]) => {
            const cat = CATEGORIES.find(c => c.slug === slug)
            const pct = (total / allTimeTotal) * 100
            return (
              <div key={slug} className="flex items-center gap-3">
                <span className="text-sm w-32 truncate text-slate-300">
                  {cat?.icon || '📦'} {cat?.label || slug}
                </span>
                <div className="flex-1 bg-navy rounded-full h-2.5">
                  <div
                    className="h-2.5 rounded-full"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: CATEGORY_COLORS[slug] || '#64748b',
                    }}
                  />
                </div>
                <span className="text-xs text-slate-400 w-20 text-right">
                  &euro;{total.toFixed(0)} ({pct.toFixed(0)}%)
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
