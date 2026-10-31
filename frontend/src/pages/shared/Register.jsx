import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { authAPI } from '../../api'

export default function Register() {
  const [params] = useSearchParams()
  const role = params.get('role') === 'seller' ? 'seller' : 'customer'
  const [form, setForm] = useState({
    name: '', address: '', city: '', mobile: '', email: '', username: '', password: '', confirm: '',
  })
  const [showPwd, setShowPwd] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      const { confirm, ...data } = form
      await authAPI.register({ ...data, role, location: form.city })
      setSuccess(role === 'seller'
        ? 'Registered! Your seller account needs admin approval before you can log in.'
        : 'Account created! You can now log in.')
      setTimeout(() => navigate(`/login?role=${role}`), 1800)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map(d => d.msg).join(', ') : detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const row = (label, name, props = {}) => (
    <div className="form-row">
      <label>{label}</label>
      <input name={name} className="form-input" value={form[name]} onChange={handleChange} required {...props} />
    </div>
  )

  return (
    <div className="hero-bg min-h-[40rem] pt-14 pb-16 px-4">
      <form onSubmit={handleSubmit} className="form-card">
        <h1>{role === 'seller' ? 'Seller Registration' : 'Customer Registration'}</h1>
        {error && <div className="bg-red-50 text-red-600 p-2 mb-3 text-xs">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 p-2 mb-3 text-xs">{success}</div>}
        {row('Name', 'name', { minLength: 2 })}
        {row('Address', 'address')}
        {row('City', 'city')}
        {row('Mobile No.', 'mobile', { pattern: '\\d{10}', placeholder: '10 digits' })}
        {row('E-mail', 'email', { type: 'email' })}
        {row('Username', 'username', { pattern: '[a-zA-Z0-9_]{3,30}', title: 'Letters, numbers and underscore (3-30)' })}
        {row('Password', 'password', { type: showPwd ? 'text' : 'password', minLength: 6 })}
        <div className="form-row">
          <label>Confirm Password</label>
          <div className="relative">
            <input name="confirm" type={showPwd ? 'text' : 'password'} className="form-input pr-8" value={form.confirm} onChange={handleChange} required />
            <button type="button" onClick={() => setShowPwd(v => !v)} className="absolute right-2 top-1.5 text-xs text-gray-500" aria-label="Show password">{showPwd ? '🙈' : '👁'}</button>
          </div>
        </div>
        <div className="form-row">
          <span />
          <button type="submit" disabled={loading} className="btn-form">{loading ? 'Creating...' : 'Register'}</button>
        </div>
        <p className="text-xs text-gray-500 text-center">
          Already registered? <Link to={`/login?role=${role}`} className="text-brand-600 hover:underline">Login</Link>
          <span className="mx-2 text-gray-300">|</span>
          {role === 'seller'
            ? <Link to="/register" className="text-brand-600 hover:underline">Register as customer</Link>
            : <Link to="/register?role=seller" className="text-brand-600 hover:underline">Register as seller</Link>}
        </p>
      </form>
    </div>
  )
}
