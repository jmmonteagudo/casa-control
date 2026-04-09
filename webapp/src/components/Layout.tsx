import { NavLink, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/gastos', label: 'Movimientos' },
  { to: '/presupuesto', label: 'Presupuesto' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()

  const handleLogout = async () => {
    await supabase.auth.signOut()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-navy">
      <nav className="bg-navy-light border-b border-navy-lighter">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-14">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-brand-green rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">&euro;</span>
              </div>
              <span className="text-white font-bold text-lg">CasaControl</span>
            </div>
            <div className="flex gap-1">
              {navItems.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-navy-lighter text-white'
                        : 'text-slate-400 hover:text-white hover:bg-navy-lighter/50'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="text-slate-500 hover:text-slate-300 text-sm transition-colors"
          >
            Salir
          </button>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  )
}
