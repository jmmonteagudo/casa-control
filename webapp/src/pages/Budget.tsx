import { useEffect, useState, useRef } from 'react'
import { supabase } from '../lib/supabase'
import type { BudgetCategory } from '../lib/supabase'
import { useMonth } from '../context/MonthContext'

export default function Budget() {
  const [budgets, setBudgets] = useState<BudgetCategory[]>([])
  const [originalBudgets, setOriginalBudgets] = useState<Record<string, number>>({})
  const [editedValues, setEditedValues] = useState<Record<string, number>>({})
  const [spent, setSpent] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newSlug, setNewSlug] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [newBudget, setNewBudget] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const { monthStart, monthEnd, label, isCurrentMonth } = useMonth()
  const addInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      supabase.from('budget_categories').select('*'),
      supabase.from('expenses').select('category_slug, amount_eur').gte('date', monthStart).lte('date', monthEnd),
    ]).then(([budRes, expRes]) => {
      const b = budRes.data || []
      setBudgets(b)
      const orig: Record<string, number> = {}
      for (const cat of b) orig[cat.id] = cat.budget_eur
      setOriginalBudgets(orig)
      setEditedValues({})
      const s: Record<string, number> = {}
      for (const row of expRes.data || []) {
        const slug = row.category_slug || 'otros'
        s[slug] = (s[slug] || 0) + row.amount_eur
      }
      setSpent(s)
      setLoading(false)
    })
  }, [monthStart, monthEnd])

  const hasChanges = Object.keys(editedValues).some(
    id => editedValues[id] !== originalBudgets[id]
  )

  const handleChange = (id: string, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num) || num < 0) return
    setEditedValues(prev => ({ ...prev, [id]: num }))
    setBudgets(prev => prev.map(b => b.id === id ? { ...b, budget_eur: num } : b))
  }

  const handleSaveAll = async () => {
    setSaving(true)
    const updates = Object.entries(editedValues)
      .filter(([id, val]) => val !== originalBudgets[id])
    await Promise.all(
      updates.map(([id, val]) =>
        supabase.from('budget_categories').update({ budget_eur: val }).eq('id', id)
      )
    )
    const newOrig = { ...originalBudgets }
    for (const [id, val] of updates) newOrig[id] = val
    setOriginalBudgets(newOrig)
    setEditedValues({})
    setSaving(false)
  }

  const handleAddCategory = async () => {
    const slug = newSlug.trim().toLowerCase().replace(/[^a-z0-9]/g, '_')
    const catLabel = newLabel.trim()
    const budget = parseFloat(newBudget) || 0
    if (!slug || !catLabel) return

    const { data, error } = await supabase
      .from('budget_categories')
      .insert({ slug, label: catLabel, budget_eur: budget })
      .select()
      .single()

    if (error) {
      alert(error.message)
      return
    }
    setBudgets(prev => [...prev, data])
    setOriginalBudgets(prev => ({ ...prev, [data.id]: data.budget_eur }))
    setNewSlug('')
    setNewLabel('')
    setNewBudget('')
    setShowAddForm(false)
  }

  if (loading) {
    return <p className="text-slate-500 text-center py-12">Cargando presupuestos...</p>
  }

  const ICONS: Record<string, string> = {
    vivienda: '🏡', super: '🛒', salud: '🏥', servicios: '💡',
    vacaciones: '✈️', salidas: '🍽️', casa: '🏠', transporte: '🚗',
    ocio: '🎈', ropa: '👗', educacion: '📚', otros: '📦',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white capitalize">Presupuestos — {label}</h2>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <button
              onClick={handleSaveAll}
              disabled={saving}
              className="px-4 py-1.5 bg-brand-green hover:bg-brand-green/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {saving ? 'Guardando...' : 'Guardar cambios'}
            </button>
          )}
          <button
            onClick={() => { setShowAddForm(v => !v); setTimeout(() => addInputRef.current?.focus(), 50) }}
            className="px-3 py-1.5 bg-navy hover:bg-navy-lighter text-slate-300 text-sm rounded-lg transition-colors"
          >
            + Categoria
          </button>
        </div>
      </div>

      {/* Add category form */}
      {showAddForm && (
        <div className="bg-navy-light border border-navy-lighter rounded-xl p-4 flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-xs text-slate-500 block mb-1">Nombre</label>
            <input
              ref={addInputRef}
              type="text"
              value={newLabel}
              onChange={e => {
                setNewLabel(e.target.value)
                if (!newSlug || newSlug === newLabel.trim().toLowerCase().replace(/[^a-z0-9]/g, '_'))
                  setNewSlug(e.target.value.trim().toLowerCase().replace(/[^a-z0-9áéíóúñ]/g, '_').replace(/[áéíóúñ]/g, c => ({á:'a',é:'e',í:'i',ó:'o',ú:'u',ñ:'n'}[c] || c)))
              }}
              placeholder="Ej: Mascotas"
              className="bg-navy border border-navy-lighter rounded-lg px-3 py-1.5 text-sm text-white w-36"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Slug</label>
            <input
              type="text"
              value={newSlug}
              onChange={e => setNewSlug(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
              placeholder="mascotas"
              className="bg-navy border border-navy-lighter rounded-lg px-3 py-1.5 text-sm text-white w-28"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Presupuesto</label>
            <input
              type="number"
              value={newBudget}
              onChange={e => setNewBudget(e.target.value)}
              placeholder="0"
              className="bg-navy border border-navy-lighter rounded-lg px-3 py-1.5 text-sm text-white w-24 text-right"
            />
          </div>
          <button
            onClick={handleAddCategory}
            className="px-4 py-1.5 bg-brand-green hover:bg-brand-green/90 text-white text-sm rounded-lg"
          >
            Agregar
          </button>
          <button
            onClick={() => setShowAddForm(false)}
            className="px-3 py-1.5 text-slate-400 hover:text-white text-sm"
          >
            Cancelar
          </button>
        </div>
      )}

      <div className="bg-navy-light rounded-xl border border-navy-lighter overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-navy-lighter text-left">
              <th className="px-4 py-3 text-xs text-slate-500 font-medium">Categoria</th>
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
                  pct >= 90 ? 'bg-brand-red' :
                  pct >= 70 ? 'bg-brand-orange' :
                  'bg-brand-green'
                const isEdited = editedValues[b.id] !== undefined && editedValues[b.id] !== originalBudgets[b.id]

                return (
                  <tr key={b.id} className={`hover:bg-navy/30 ${isEdited ? 'bg-navy/20' : ''}`}>
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-200">
                        {ICONS[b.slug] || '📦'} {b.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm font-medium text-white">&euro;{s.toFixed(0)}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <input
                        type="number"
                        value={editedValues[b.id] !== undefined ? editedValues[b.id] : b.budget_eur}
                        onChange={e => handleChange(b.id, e.target.value)}
                        disabled={!isCurrentMonth}
                        className={`w-20 bg-navy border rounded px-2 py-1 text-sm text-white text-right disabled:opacity-50 disabled:cursor-not-allowed ${isEdited ? 'border-brand-green' : 'border-navy-lighter'}`}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-navy rounded-full h-2">
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
      {!isCurrentMonth && (
        <p className="text-xs text-slate-500 text-center">Los presupuestos solo se pueden editar en el mes actual</p>
      )}
    </div>
  )
}
