import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { BudgetCategory } from '../lib/supabase'

export default function Budget() {
  const [budgets, setBudgets] = useState<BudgetCategory[]>([])
  const [spent, setSpent] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [editSlug, setEditSlug] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  useEffect(() => {
    const now = new Date()
    const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`

    Promise.all([
      supabase.from('budget_categories').select('*'),
      supabase.from('expenses').select('category_slug, amount_eur').gte('date', monthStart),
    ]).then(([budRes, expRes]) => {
      setBudgets(budRes.data || [])
      const s: Record<string, number> = {}
      for (const row of expRes.data || []) {
        const slug = row.category_slug || 'super'
        s[slug] = (s[slug] || 0) + row.amount_eur
      }
      setSpent(s)
      setLoading(false)
    })
  }, [])

  const handleSave = async (id: string) => {
    const val = parseFloat(editValue)
    if (isNaN(val) || val < 0) return
    await supabase.from('budget_categories').update({ budget_eur: val }).eq('id', id)
    setBudgets(prev => prev.map(b => b.id === id ? { ...b, budget_eur: val } : b))
    setEditSlug(null)
  }

  if (loading) {
    return <p className="text-slate-500 text-center py-12">Cargando presupuestos...</p>
  }

  const ICONS: Record<string, string> = {
    vivienda: '🏡', super: '🛒', salud: '🏥', servicios: '💡',
    vacaciones: '✈️', salidas: '🍽️', casa: '🏠', transporte: '🚗',
    ocio: '🎈', ropa: '👗', educacion: '📚',
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-white">Presupuestos mensuales</h2>
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800 text-left">
              <th className="px-4 py-3 text-xs text-slate-500 font-medium">Categoría</th>
              <th className="px-4 py-3 text-xs text-slate-500 font-medium text-right">Gastado</th>
              <th className="px-4 py-3 text-xs text-slate-500 font-medium text-right">Presupuesto</th>
              <th className="px-4 py-3 text-xs text-slate-500 font-medium">Progreso</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {budgets
              .sort((a, b) => a.slug.localeCompare(b.slug))
              .map(b => {
                const s = spent[b.slug] || 0
                const pct = b.budget_eur > 0 ? Math.min((s / b.budget_eur) * 100, 100) : 0
                const barColor =
                  pct >= 90 ? 'bg-red-500' :
                  pct >= 70 ? 'bg-amber-500' :
                  'bg-emerald-500'

                return (
                  <tr key={b.id} className="hover:bg-slate-800/30">
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-200">
                        {ICONS[b.slug] || '📦'} {b.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm font-medium text-white">€{s.toFixed(0)}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {editSlug === b.slug ? (
                        <div className="flex items-center justify-end gap-1">
                          <input
                            type="number"
                            value={editValue}
                            onChange={e => setEditValue(e.target.value)}
                            className="w-20 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-white text-right"
                            autoFocus
                            onKeyDown={e => e.key === 'Enter' && handleSave(b.id)}
                          />
                          <button
                            onClick={() => handleSave(b.id)}
                            className="text-xs text-blue-400 hover:text-blue-300"
                          >
                            OK
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => { setEditSlug(b.slug); setEditValue(String(b.budget_eur)) }}
                          className="text-sm text-slate-400 hover:text-white"
                        >
                          €{b.budget_eur.toFixed(0)}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-800 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${barColor}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-500 w-10 text-right">{pct.toFixed(0)}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
