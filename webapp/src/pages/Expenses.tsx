import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { Expense } from '../lib/supabase'
import { useMonth } from '../context/MonthContext'
import ExpenseList from '../components/ExpenseList'

const CATEGORIES = [
  { slug: '', label: 'Todas' },
  { slug: 'vivienda', label: 'Vivienda' },
  { slug: 'super', label: 'Supermercado' },
  { slug: 'salud', label: 'Salud' },
  { slug: 'servicios', label: 'Servicios' },
  { slug: 'vacaciones', label: 'Vacaciones' },
  { slug: 'salidas', label: 'Salidas' },
  { slug: 'casa', label: 'Casa/Hogar' },
  { slug: 'transporte', label: 'Transporte' },
  { slug: 'ocio', label: 'Ocio/Kids' },
  { slug: 'ropa', label: 'Ropa' },
  { slug: 'educacion', label: 'Educacion' },
  { slug: 'otros', label: 'Otros' },
]

export default function Expenses() {
  const { monthStart, monthEnd } = useMonth()
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [dateFrom, setDateFrom] = useState(monthStart)
  const [dateTo, setDateTo] = useState(monthEnd)
  const [page, setPage] = useState(0)
  const [editing, setEditing] = useState<Expense | null>(null)
  const pageSize = 20

  // Sync filters when month changes in Dashboard
  useEffect(() => {
    setDateFrom(monthStart)
    setDateTo(monthEnd)
    setPage(0)
  }, [monthStart, monthEnd])

  const fetchExpenses = async () => {
    setLoading(true)
    let query = supabase
      .from('expenses')
      .select('*')
      .order('date', { ascending: false })
      .range(page * pageSize, (page + 1) * pageSize - 1)

    if (category) query = query.eq('category_slug', category)
    if (dateFrom) query = query.gte('date', dateFrom)
    if (dateTo) query = query.lte('date', dateTo)

    const { data } = await query
    setExpenses(data || [])
    setLoading(false)
  }

  useEffect(() => {
    fetchExpenses()
  }, [category, dateFrom, dateTo, page])

  const handleSaveEdit = async () => {
    if (!editing) return
    await supabase
      .from('expenses')
      .update({
        category_slug: editing.category_slug,
        amount_eur: editing.amount_eur,
      })
      .eq('id', editing.id)
    setEditing(null)
    fetchExpenses()
  }

  const handleDelete = async (id: string) => {
    await supabase.from('expenses').delete().eq('id', id)
    setEditing(null)
    fetchExpenses()
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-white">Historial de gastos</h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={category}
          onChange={e => { setCategory(e.target.value); setPage(0) }}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
        >
          {CATEGORIES.map(c => (
            <option key={c.slug} value={c.slug}>{c.label}</option>
          ))}
        </select>
        <input
          type="date"
          value={dateFrom}
          onChange={e => { setDateFrom(e.target.value); setPage(0) }}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
        />
        <input
          type="date"
          value={dateTo}
          onChange={e => { setDateTo(e.target.value); setPage(0) }}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
        />
      </div>

      {/* Edit modal */}
      {editing && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 space-y-3">
          <h3 className="text-sm font-semibold text-slate-300">Editar gasto</h3>
          <p className="text-sm text-slate-400">{editing.description}</p>
          <div className="flex gap-3">
            <div>
              <label className="text-xs text-slate-500">Categoria</label>
              <select
                value={editing.category_slug}
                onChange={e => setEditing({ ...editing, category_slug: e.target.value })}
                className="block bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white mt-1"
              >
                {CATEGORIES.filter(c => c.slug).map(c => (
                  <option key={c.slug} value={c.slug}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Importe</label>
              <input
                type="number"
                step="0.01"
                value={editing.amount_eur}
                onChange={e => setEditing({ ...editing, amount_eur: parseFloat(e.target.value) || 0 })}
                className="block bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white mt-1 w-28"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleSaveEdit} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg">
              Guardar
            </button>
            <button onClick={() => handleDelete(editing.id)} className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 text-sm rounded-lg">
              Eliminar
            </button>
            <button onClick={() => setEditing(null)} className="px-3 py-1.5 text-slate-400 hover:text-white text-sm">
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* List */}
      <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
        {loading ? (
          <p className="text-slate-500 text-sm text-center py-8">Cargando...</p>
        ) : (
          <ExpenseList expenses={expenses} onEdit={setEditing} />
        )}
      </div>

      {/* Pagination */}
      <div className="flex justify-between">
        <button
          onClick={() => setPage(p => Math.max(0, p - 1))}
          disabled={page === 0}
          className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-sm disabled:opacity-30"
        >
          Anterior
        </button>
        <span className="text-slate-500 text-sm self-center">Pagina {page + 1}</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={expenses.length < pageSize}
          className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-sm disabled:opacity-30"
        >
          Siguiente
        </button>
      </div>
    </div>
  )
}
