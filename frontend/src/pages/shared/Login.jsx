import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { TrendingUp, Brain, ShieldCheck } from 'lucide-react'
import { authAPI } from '../../api'
import { useAuth } from '../../context/AuthContext'

const DEMO = {
  admin: { username: 'admin', password: 'admin123' },
  customer: { username: 'claire_gute_cg12520', password: 'customer123' },
  seller: { username: 'furniture_seller', password: 'seller123' },
}
const TITLES = { admin: 'E-Commerce Admin Login', seller: 'Seller Login', customer: 'Customer Login' }
const WELCOME = {
  admin: 'Approve sellers, manage the platform and train the models.',
  seller: 'Manage products and orders and see ARIMA stock forecasts.',
  customer: 'Shop your favourite products and get next-basket picks.',
}

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const wanted = params.get('role')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authAPI.login(username, password, wanted)
      const { access_token, role, name } = res.data
      const userData = { username, role, name, token: access_token }
      login(access_token, userData)
      const dest = role === 'admin' ? '/admin' : role === 'seller' ? '/seller' : '/shop'
      navigate(dest)
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="hero-bg min-h-[34rem] pt-14 pb-16 px-4">
      <div className="max-w-4xl mx-auto grid md:grid-cols-2 shadow-2xl bg-white overflow-hidden">
        {/* Left layer: brand and illustration */}
        <div className="relative hidden md:flex flex-col justify-between bg-gradient-to-br from-brand-400 to-brand-500 p-8">
          <div>
            <h2 className="text-2xl font-bold text-ink leading-tight">Predict demand.<br />Recommend the next basket.</h2>
            <p className="text-sm text-ink/70 mt-2">{WELCOME[wanted] || 'One platform for admins, sellers and customers.'}</p>
          </div>
          <img src="/login-art.svg" alt="" className="w-full max-w-xs mx-auto my-4 drop-shadow-lg" />
          <ul className="text-xs text-ink/80 space-y-1.5">
            <li className="flex items-center gap-2"><TrendingUp size={14} /> ARIMA 30-day sales forecasts and stock alerts</li>
            <li className="flex items-center gap-2"><Brain size={14} /> Decision Tree next-basket recommendations</li>
            <li className="flex items-center gap-2"><ShieldCheck size={14} /> Role-based, token-secured access</li>
          </ul>
        </div>

        {/* Right layer: login */}
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 flex flex-col justify-center">
          <h1 className="text-xl font-semibold mb-1">{TITLES[wanted] || 'Login'}</h1>
          <p className="text-xs text-gray-500 mb-5">Sign in to continue to Next Basket</p>
          {error && <div className="bg-red-50 text-red-600 p-2 mb-3 text-xs">{error}</div>}
          <label className="text-xs text-gray-600 mb-1">Username</label>
          <input className="form-input mb-3" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
          <label className="text-xs text-gray-600 mb-1">Password</label>
          <div className="relative mb-4">
            <input type={showPwd ? 'text' : 'password'} className="form-input pr-8" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
            <button type="button" onClick={() => setShowPwd(v => !v)} className="absolute right-2 top-1.5 text-xs text-gray-500" aria-label="Show password">{showPwd ? '🙈' : '👁'}</button>
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full text-sm">{loading ? 'Signing in...' : 'Login'}</button>
          {wanted !== 'admin' && (
            <p className="text-xs text-gray-500 text-center mt-3">
              New here? <Link to={`/register${wanted === 'seller' ? '?role=seller' : ''}`} className="text-brand-600 hover:underline">Register</Link>
            </p>
          )}

          <div className="mt-4 border-t border-gray-200 pt-3">
            <p className="text-xs font-semibold text-ink mb-2">
              {wanted ? `${wanted[0].toUpperCase()}${wanted.slice(1)} demo account` : 'Demo users (click to fill)'}
            </p>
            <table className="w-full text-xs">
              <thead><tr className="text-left text-gray-500"><th className="font-normal">Role</th><th className="font-normal">User ID</th><th className="font-normal">Password</th></tr></thead>
              <tbody>
                {Object.entries(DEMO).filter(([r]) => (
                  !wanted || r === wanted
                )).map(([r, d]) => (
                  <tr
                    key={r}
                    className="cursor-pointer hover:bg-brand-50"
                    role="button"
                    tabIndex={0}
                    onClick={() => { setUsername(d.username); setPassword(d.password) }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        setUsername(d.username)
                        setPassword(d.password)
                      }
                    }}
                  >
                    <td className="py-1 capitalize">{r}</td>
                    <td className="font-mono">{d.username}</td>
                    <td className="font-mono">{d.password}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {wanted === 'admin' && (
              <p className="text-[11px] text-gray-500 mt-1">
                Admin login works only if this account exists in the connected database with this password.
              </p>
            )}
            {wanted !== 'admin' && (
              <p className="text-[11px] text-gray-400 mt-2">
                Demo accounts are available only when the sample dataset has been seeded in the connected database.
              </p>
            )}
            {!wanted && <p className="text-[11px] text-gray-400 mt-2">Use the Customer, Seller or Admin links above for a role-specific login.</p>}
          </div>
        </form>
      </div>
    </div>
  )
}
