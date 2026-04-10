import { CATEGORY_MAP } from '../lib/categories'

type Props = {
  slug: string
  spent: number
  budget: number
}

export default function CategoryGauge({ slug, spent, budget }: Props) {
  const pct = budget > 0 ? Math.min((spent / budget) * 100, 100) : 0
  const meta = CATEGORY_MAP[slug]
  const cat = meta ? { icon: meta.icon, label: meta.label } : { icon: '📦', label: slug }

  const barColor =
    pct >= 90 ? 'bg-brand-red' :
    pct >= 70 ? 'bg-brand-orange' :
    'bg-brand-green'

  const textColor =
    pct >= 90 ? 'text-brand-red' :
    pct >= 70 ? 'text-brand-orange' :
    'text-brand-green'

  return (
    <div className="bg-navy-light rounded-xl p-4 border border-navy-lighter">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-slate-200">
          {cat.icon} {cat.label}
        </span>
        <span className={`text-sm font-bold ${textColor}`}>
          {pct.toFixed(0)}%
        </span>
      </div>
      <div className="w-full bg-navy rounded-full h-2.5 mb-2">
        <div
          className={`h-2.5 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-500">
        <span>&euro;{spent.toFixed(0)}</span>
        <span>&euro;{budget.toFixed(0)}</span>
      </div>
    </div>
  )
}
