import { useState } from 'react'
import { supabase } from '../lib/supabase'

export default function Login() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const { error } = await supabase.auth.signInWithOtp({ email })
    if (error) {
      setError(error.message)
    } else {
      setSent(true)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-navy px-4">
      <div className="w-full max-w-sm bg-navy-light rounded-2xl p-8 shadow-xl border border-navy-lighter">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-brand-green rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">&euro;</span>
          </div>
          <h1 className="text-2xl font-bold text-white">CasaControl</h1>
        </div>
        <p className="text-slate-400 mb-6 text-sm">Gestion financiera familiar</p>

        {sent ? (
          <p className="text-brand-green text-sm">
            Revisa tu email — te enviamos un link para iniciar sesion.
          </p>
        ) : (
          <form onSubmit={handleLogin} className="space-y-4">
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="tu@email.com"
              required
              className="w-full px-4 py-2.5 bg-navy border border-navy-lighter rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-green"
            />
            {error && <p className="text-brand-red text-sm">{error}</p>}
            <button
              type="submit"
              className="w-full py-2.5 bg-brand-green hover:bg-brand-green/90 text-white font-medium rounded-lg transition-colors"
            >
              Iniciar sesion
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
