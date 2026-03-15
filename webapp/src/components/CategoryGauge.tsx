const CATEGORY_LABELS: Record<string, { icon: string; label: string }> = {
  vivienda:   { icon: '🏡', label: 'Vivienda' },
  super:      { icon: '🛒', label: 'Supermercado' },
  salud:      { icon: '🏥', label: 'Salud' },
  servicios:  { icon: '💡', label: 'Servicios' },
  vacaciones: { icon: '✈️', label: 'Vacaciones' },
  salidas:    { icon: '🍽️', label: 'Salidas' },
  casa:       { icon: '🏠', label: 'Casa/Hogar' },
  transporte: { icon: '🚗', label: 'Transporte' },
  ocio:       { icon: '🎈', label: 'Ocio/Kids' },
  ropa:       { icon: '👗', label: 'Ropa' },
  educacion:  { icon: '📚', label: 'Educación' },
}

type Props = {
  slug: string
  spent: number
  budget: number
}

export default function CategoryGauge({ slug, spent, budget }: Props) {
  const pct = budget > 0 ? Math.min((spent / budget) * 100, 100) : 0
  const cat = CATEGORY_LABELS[slug] || { icon: '📦', label: slug }

  const barColor =
    pct >= 90 ? 'bg-red-500' :
    pct >= 70 ? 'bg-amber-500' :
    'bg-emerald-500'

  const textColor =
    pct >= 90 ? 'text-red-400' :
    pct >= 70 ? 'text-amber-400' :
    'text-emerald-400'

  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-300">
          {cat.icon} {cat.label}
        </span>
        <span className={`text-sm font-bold ${textColor}`}>
          {pct.toFixed(0)}%
        </span>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-2.5 mb-2">
        <div
          className={`h-2.5 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-500">
        <span>€{spent.toFixed(0)}</span>
        <span>€{budget.toFixed(0)}</span>
      </div>
    </div>
  )
}
