import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../context/useAuth'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/forms/FormFields'
import { AuthLayout } from '../../components/auth/BrandArtwork'
import { Alert } from '../../components/ui/Alert'

const emptyForm = { email: '', password: '' }

export function StaffLogin() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [formData, setFormData] = useState(emptyForm)
  const [errors, setErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const validate = () => {
    const newErrors = {}
    if (!formData.email) newErrors.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) newErrors.email = 'Invalid email format'
    if (!formData.password) newErrors.password = 'Password is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    setError('')

    const result = await login(formData)
    if (result.success) {
      navigate('/dashboard')
    } else {
      setError(result.error)
    }
    setLoading(false)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  return (
    <AuthLayout mode="login">
      <div className="w-full max-w-md space-y-7 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/5 sm:p-9">
        <div className="text-center">
          <Link to="/" className="inline-flex items-center gap-3 mb-8">
            <img src="/insurex-nexus-ai-logo.jpg" alt="InsureX Nexus AI logo" className="w-12 h-12 rounded-xl object-cover" />
            <span className="text-2xl font-bold text-gray-900">InsureX Nexus AI</span>
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Staff sign in</h1>
          <p className="mt-2 text-gray-600">Employees, investigators and administrators</p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <Alert>{error}</Alert>
          )}

          <div className="space-y-4">
            <Input
              label="Email address"
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              error={errors.email}
              placeholder="you@example.com"
              autoComplete="email"
              required
              leftIcon={<Mail className="w-5 h-5 text-gray-400" />}
            />

            <Input
              label="Password"
              type={showPassword ? 'text' : 'password'}
              name="password"
              value={formData.password}
              onChange={handleChange}
              error={errors.password}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              leftIcon={<Lock className="w-5 h-5 text-gray-400" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-gray-400 hover:text-gray-600"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              }
            />
          </div>

          <div className="flex items-center justify-end">
            <Link to="/forgot-password" className="text-sm font-medium text-primary hover:underline">
              Forgot password?
            </Link>
          </div>

          <Button type="submit" fullWidth loading={loading} className="py-3">
            Sign in
          </Button>

          <Button type="button" variant="outline" fullWidth className="py-3" onClick={() => navigate('/login')}>
            Customer login
          </Button>
        </form>
      </div>
    </AuthLayout>
  )
}

export default StaffLogin
