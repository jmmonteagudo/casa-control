import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import type { Expense } from '../lib/supabase'
import { useMonth } from '../context/MonthContext'
import ExpenseList from '../components/ExpenseList'
import { CATEGORIES, CATEGORY_COLORS } from '../lib/categories'

const FILTER_CATEGORIES = [
  { slug: '', label: 'Todas' },
  ...CATEGORIES.map(c => ({ slug: c.slug, label: c.label })),
]

export default function Expenses() {
  const { monthStart, monthEnd } = useMonth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [dateFrom, setDateFrom] = useState(monthStart)
  const [dateTo, setDateTo] = useState(monthEnd)
  const [page, setPage] = useState(0)
  const [editing, setEditing] = useState<Expense | null>(null)
  const [pendingOnly, setPendingOnly] = useState(searchParams.get('pending') === 'true')
  const [pendingCount, setPendingCount] = useState(0)
  const pageSize = 20

  // Sync filters when month changes
  useEffect(() => {
    if (!pendingOnly) {
      setDateFrom(monthStart)
      setDateTo(monthEnd)
    }
    setPage(0)
  }, [monthStart, monthEnd])

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput)
      setPage(0)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  // Load pending count
  useEffect(() => {
    supabase
      .from('expenses')
      .select('id', { count: 'exact', head: true })
      .eq('needs_review', true)
      .then(({ count }) => setPendingCount(count || 0))
  }, [expenses])

  const fetchExpenses = async () => {
    setLoading(true)
    let query = supabase
      .from('expenses')
      .select('*')
      .order('date', { ascending: false })
      .range(page * pageSize, (page + 1) * pageSize - 1)

    if (pendingOnly) {
      query = query.eq('needs_review', true)
    } else {
      if (category) query = query.eq('category_slug', category)
      if (search) {
        query = query.or(`description.ilike.%${search}%,store.ilike.%${search}%`)
      } else {
        if (dateFrom) query = query.gte('date', dateFrom)
        if (dateTo) query = query.lte('date', dateTo)
      }
    }

    const { data } = await query
    setExpenses(data || [])
    setLoading(false)
  }

  useEffect(() => {
    fetchExpenses()
  }, [category, dateFrom, dateTo, page, pendingOnly, search])

  const togglePending = () => {
    const next = !pendingOnly
    setPendingOnly(next)
    setPage(0)
    if (next) {
      setSearchParams({ pending: 'true' })
    } else {
      setSearchParams({})
    }
  }

  const handleSaveEdit = async () => {
    if (!editing) return
    await supabase
      .from('expenses')
      .update({
        description: editing.description,
        category_slug: editing.category_slug,
        amount_eur: editing.amount_eur,
        store: editing.store,
        notes: editing.notes,
        needs_review: false,
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
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">Movimientos</h2>
        {pendingCount > 0 && (
          <button
            onClick={togglePending}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              pendingOnly
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : 'bg-navy hover:bg-navy-lighter text-amber-400'
            }`}
          >
            Sin clasificar ({pendingCount})
          </button>
        )}
      </div>

      {/* Filters */}
      {!pendingOnly && (
        <div className="flex flex-wrap gap-3">
          <input
            type="text"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            placeholder="Buscar..."
            className="bg-navy border border-navy-lighter rounded-lg px-3 py-2 text-sm text-white w-40 placeholder:text-slate-600"
          />
          <select
            value={category}
            onChange={e => { setCategory(e.target.value); setPage(0) }}
            className="bg-navy border border-navy-lighter rounded-lg px-3 py-2 text-sm text-white"
          >
            {FILTER_CATEGORIES.map(c => (
              <option key={c.slug} value={c.slug}>{c.label}</option>
            ))}
          </select>
          <input
            type="date"
            value={dateFrom}
            onChange={e => { setDateFrom(e.target.value); setPage(0) }}
            className="bg-navy border border-navy-lighter rounded-lg px-3 py-2 text-sm text-white"
          />
          <input
            type="date"
            value={dateTo}
            onChange={e => { setDateTo(e.target.value); setPage(0) }}
            className="bg-navy border border-navy-lighter rounded-lg px-3 py-2 text-sm text-white"
          />
        </div>
      )}

      {/* Edit modal */}
      {editing && (
        <div className="bg-navy-light border border-navy-lighter rounded-xl p-4 space-y-4">
          <h3 className="text-sm font-semibold text-slate-300">Editar gasto</h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-500">Descripcion</label>
              <input
                type="text"
                value={editing.description}
                onChange={e => setEditing({ ...editing, description: e.target.value })}
                className="block w-full bg-navy border border-navy-lighter rounded-lg px-3 py-2 text-sm text-white mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500">Tienda</label>
              <input
                type="text"
                value={editing.store || ''}
                onChange={e => setEditing({ ...editing, store: e.target.value || null })}
                className="block w-full bg-navy border border-navy-lighter rounded-lg px-3 py-2 text-sm text-white mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500">Importe</label>
              <input
                type="number"
                step="0.01"
                value={editing.amount_eur}
                onChange={e => setEditing({ ...editing, amount_eur: parseFloat(e.target.value) || 0 })}
                className="block bg-navy border border-navy-lighter rounded-lg px-3 py-2 text-sm text-white mt-1 w-28"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500">Notas</label>
              <input
                type="text"
                value={editing.notes || ''}
                onChange={e => setEditing({ ...editing, notes: e.target.value || null })}
                placeholder="Nota opcional..."
                className="block w-full bg-navy border border-navy-lighter rounded-lg px-3 py-2 text-sm text-white mt-1"
              />
            </div>
          </div>

          {/* Category pills */}
          <div>
            <label className="text-xs text-slate-500 block mb-2">Categoria</label>
            <div className="flex flex-wrap gap-1.5">
              {CATEGORIES.map(c => (
                <button
                  key={c.slug}
                  onClick={() => setEditing({ ...editing, category_slug: c.slug })}
                  className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
                    editing.category_slug === c.slug
                      ? 'text-white font-medium ring-1 ring-white/30'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  style={{
                    backgroundColor: editing.category_slug === c.slug
                      ? CATEGORY_COLORS[c.slug] || '#64748b'
                      : `${CATEGORY_COLORS[c.slug] || '#64748b'}20`,
                  }}
                >
                  {c.icon} {c.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <button onClick={handleSaveEdit} className="px-3 py-1.5 bg-brand-green hover:bg-brand-green/90 text-white text-sm rounded-lg">
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
      <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
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
          className="px-3 py-1.5 bg-navy text-slate-300 rounded-lg text-sm disabled:opacity-30"
        >
          Anterior
        </button>
        <span className="text-slate-500 text-sm self-center">Pagina {page + 1}</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={expenses.length < pageSize}
          className="px-3 py-1.5 bg-navy text-slate-300 rounded-lg text-sm disabled:opacity-30"
        >
          Siguiente
        </button>
      </div>
    </div>
  )
}
