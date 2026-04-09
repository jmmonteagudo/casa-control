import { createContext, useContext, useState, useMemo } from 'react'

type MonthState = {
  year: number
  month: number // 0-indexed (0=Jan, 11=Dec)
  monthStart: string // YYYY-MM-01
  monthEnd: string   // YYYY-MM-DD (last day)
  isCurrentMonth: boolean
  prevMonth: () => void
  nextMonth: () => void
  label: string // "diciembre 2023"
}

const MonthContext = createContext<MonthState | null>(null)

export function MonthProvider({ children }: { children: React.ReactNode }) {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())

  const value = useMemo(() => {
    const monthStart = `${year}-${String(month + 1).padStart(2, '0')}-01`
    const lastDay = new Date(year, month + 1, 0).getDate()
    const monthEnd = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
    const isCurrentMonth = year === now.getFullYear() && month === now.getMonth()
    const label = new Date(year, month).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })

    const prevMonth = () => {
      if (month === 0) {
        setYear(y => y - 1)
        setMonth(11)
      } else {
        setMonth(m => m - 1)
      }
    }

    const nextMonth = () => {
      if (isCurrentMonth) return
      if (month === 11) {
        setYear(y => y + 1)
        setMonth(0)
      } else {
        setMonth(m => m + 1)
      }
    }

    return { year, month, monthStart, monthEnd, isCurrentMonth, prevMonth, nextMonth, label }
  }, [year, month])

  return <MonthContext.Provider value={value}>{children}</MonthContext.Provider>
}

export function useMonth() {
  const ctx = useContext(MonthContext)
  if (!ctx) throw new Error('useMonth must be used within MonthProvider')
  return ctx
}
