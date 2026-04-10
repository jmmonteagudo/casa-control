export type CategoryMeta = {
  slug: string
  label: string
  icon: string
  color: string
}

export const CATEGORIES: CategoryMeta[] = [
  { slug: 'vivienda',       label: 'Vivienda',       icon: '🏡', color: '#6366f1' },
  { slug: 'super',          label: 'Supermercado',    icon: '🛒', color: '#3BB2AC' },
  { slug: 'salud',          label: 'Salud',           icon: '🏥', color: '#E63944' },
  { slug: 'servicios',      label: 'Servicios',       icon: '💡', color: '#F8AD55' },
  { slug: 'vacaciones',     label: 'Vacaciones',      icon: '✈️', color: '#06b6d4' },
  { slug: 'salidas',        label: 'Salidas',         icon: '🍽️', color: '#ec4899' },
  { slug: 'casa',           label: 'Casa/Hogar',      icon: '🏠', color: '#8b5cf6' },
  { slug: 'transporte',     label: 'Transporte',      icon: '🚇', color: '#3b82f6' },
  { slug: 'ocio',           label: 'Ocio/Kids',       icon: '🎈', color: '#14b8a6' },
  { slug: 'ropa',           label: 'Ropa',            icon: '👗', color: '#d946ef' },
  { slug: 'educacion',      label: 'Educación',       icon: '📚', color: '#f97316' },
  { slug: 'impuestos',      label: 'Impuestos',       icon: '🏛️', color: '#78716c' },
  { slug: 'deportes',       label: 'Deportes',        icon: '🏋️', color: '#22c55e' },
  { slug: 'coche',          label: 'Coche',           icon: '🚘', color: '#eab308' },
  { slug: 'sin_clasificar', label: 'Sin clasificar',  icon: '❓', color: '#ef4444' },
  { slug: 'otros',          label: 'Otros',           icon: '📦', color: '#64748b' },
]

export const CATEGORY_MAP = Object.fromEntries(
  CATEGORIES.map(c => [c.slug, c])
) as Record<string, CategoryMeta>

export const CATEGORY_COLORS = Object.fromEntries(
  CATEGORIES.map(c => [c.slug, c.color])
) as Record<string, string>

export const CATEGORY_ICONS = Object.fromEntries(
  CATEGORIES.map(c => [c.slug, c.icon])
) as Record<string, string>

export const CATEGORY_LABELS = Object.fromEntries(
  CATEGORIES.map(c => [c.slug, c.label])
) as Record<string, string>
