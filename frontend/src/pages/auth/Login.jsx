import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Shield, Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/forms/FormFields'
import { clsx } from 'clsx'

export function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [formData, setFormData] = useState({ email: '', password: '' })
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
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <Link to="/" className="inline-flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center">
              <Shield className="w-7 h-7 text-white" />
            </div>
            <span className="text-2xl font-bold text-gray-900">InsureX Nexus AI</span>
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Welcome back</h1>
          <p className="mt-2 text-gray-600">Sign in to your account to continue</p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
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

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2">
              <input type="checkbox" className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary focus:ring-2" />
              <span className="text-sm text-gray-600">Remember me</span>
            </label>
            <Link to="/forgot-password" className="text-sm font-medium text-primary hover:underline">
              Forgot password?
            </Link>
          </div>

          <Button type="submit" fullWidth loading={loading} className="py-3">
            Sign in
          </Button>
        </form>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Don't have an account?{' '}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Sign up
            </Link>
          </p>
        </div>

        <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4 text-sm text-gray-700">
          <p className="font-semibold text-gray-900 mb-2 flex items-center justify-between">
            <span>Quick Demo Role Sign-In:</span>
            <span className="text-xs font-normal text-blue-600">Click to test role</span>
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => {
                setFormData({ email: 'customer@demo.com', password: 'demo123' })
                login({ email: 'customer@demo.com', password: 'demo123' }).then((res) => res.success && navigate('/dashboard'))
              }}
              className="p-2 text-xs font-medium bg-white rounded-lg border border-gray-200 hover:border-blue-500 hover:text-blue-600 shadow-sm transition text-left"
            >
              <div className="font-semibold">Customer</div>
              <div className="text-[10px] text-gray-500">John Anderson</div>
            </button>
            <button
              type="button"
              onClick={() => {
                setFormData({ email: 'employee@demo.com', password: 'demo123' })
                login({ email: 'employee@demo.com', password: 'demo123' }).then((res) => res.success && navigate('/dashboard'))
              }}
              className="p-2 text-xs font-medium bg-white rounded-lg border border-gray-200 hover:border-blue-500 hover:text-blue-600 shadow-sm transition text-left"
            >
              <div className="font-semibold">Employee</div>
              <div className="text-[10px] text-gray-500">Sarah Mitchell</div>
            </button>
            <button
              type="button"
              onClick={() => {
                setFormData({ email: 'investigator@demo.com', password: 'demo123' })
                login({ email: 'investigator@demo.com', password: 'demo123' }).then((res) => res.success && navigate('/investigators'))
              }}
              className="p-2 text-xs font-medium bg-white rounded-lg border border-gray-200 hover:border-blue-500 hover:text-blue-600 shadow-sm transition text-left"
            >
              <div className="font-semibold">Investigator</div>
              <div className="text-[10px] text-gray-500">Emily Rodriguez</div>
            </button>
            <button
              type="button"
              onClick={() => {
                setFormData({ email: 'repair@demo.com', password: 'demo123' })
                login({ email: 'repair@demo.com', password: 'demo123' }).then((res) => res.success && navigate('/repair-shops'))
              }}
              className="p-2 text-xs font-medium bg-white rounded-lg border border-gray-200 hover:border-blue-500 hover:text-blue-600 shadow-sm transition text-left"
            >
              <div className="font-semibold">Repair Shop</div>
              <div className="text-[10px] text-gray-500">Lisa Thompson</div>
            </button>
            <button
              type="button"
              onClick={() => {
                setFormData({ email: 'admin@demo.com', password: 'demo123' })
                login({ email: 'admin@demo.com', password: 'demo123' }).then((res) => res.success && navigate('/analytics'))
              }}
              className="p-2 text-xs font-medium bg-white rounded-lg border border-gray-200 hover:border-blue-500 hover:text-blue-600 shadow-sm transition text-left col-span-2 sm:col-span-1"
            >
              <div className="font-semibold">Administrator</div>
              <div className="text-[10px] text-gray-500">James Wilson</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login