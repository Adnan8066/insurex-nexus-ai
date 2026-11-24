import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail, Lock, KeyRound } from 'lucide-react'
import { useAuth } from '../../context/useAuth'
import { authService } from '../../services'
import { formatApiError } from '../../services/api'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/forms/FormFields'
import { AuthLayout } from '../../components/auth/BrandArtwork'
import { Alert } from '../../components/ui/Alert'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const emptyForm = { email: '', password: '', code: '' }

// Customers sign in with a one-time code sent to their email. Password sign-in stays
// available for customers who prefer it.
export function Login() {
  const navigate = useNavigate()
  const { customerLogin, customerCodeLogin } = useAuth()
  const [method, setMethod] = useState('code') // 'code' | 'password'
  const [codeSent, setCodeSent] = useState(false)
  const [formData, setFormData] = useState(emptyForm)
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const validate = (fields) => {
    const newErrors = {}
    if (fields.includes('email')) {
      if (!formData.email) newErrors.email = 'Email is required'
      else if (!EMAIL_PATTERN.test(formData.email)) newErrors.email = 'Invalid email format'
    }
    if (fields.includes('password') && !formData.password) newErrors.password = 'Password is required'
    if (fields.includes('code') && !/^\d{6}$/.test(formData.code.trim())) newErrors.code = 'Enter the 6-digit code'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const sendCode = async () => {
    if (!validate(['email'])) return
    setLoading(true)
    setError('')
    try {
      const email = formData.email.trim()
      const data = await authService.requestCustomerCode(email)
      setCodeSent(true)
      setNotice(`If ${email} has a customer account, we've sent a 6-digit code. It expires in ${data?.expires_in_minutes ?? 10} minutes.`)
    } catch (err) {
      setError(formatApiError(err, 'We could not send the code. Please try again.'))
    }
    setLoading(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (method === 'code' && !codeSent) {
      await sendCode()
      return
    }
    if (!validate(method === 'code' ? ['email', 'code'] : ['email', 'password'])) return

    setLoading(true)
    setError('')
    const result = method === 'code'
      ? await customerCodeLogin({ email: formData.email.trim(), code: formData.code.trim() })
      : await customerLogin({ email: formData.email, password: formData.password })
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

  const switchMethod = () => {
    setMethod((prev) => (prev === 'code' ? 'password' : 'code'))
    setCodeSent(false)
    setError('')
    setNotice('')
    setErrors({})
    setFormData((prev) => ({ ...prev, password: '', code: '' }))
  }

  const changeEmail = () => {
    setCodeSent(false)
    setNotice('')
    setError('')
    setFormData((prev) => ({ ...prev, code: '' }))
  }

  const submitLabel = method === 'password' ? 'Sign in' : codeSent ? 'Verify code and sign in' : 'Email me a sign-in code'

  return (
    <AuthLayout mode="login">
      <div className="w-full max-w-md space-y-7 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/5 sm:p-9">
        <div className="text-center">
          <Link to="/" className="inline-flex items-center gap-3 mb-8">
            <img src="/insurex-nexus-ai-logo.jpg" alt="InsureX Nexus AI logo" className="w-12 h-12 rounded-xl object-cover" />
            <span className="text-2xl font-bold text-gray-900">InsureX Nexus AI</span>
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Customer sign in</h1>
          <p className="mt-2 text-gray-600">
            {method === 'code' ? "We'll email you a one-time sign-in code" : 'Sign in with your email and password'}
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit} noValidate>
          {error && <Alert>{error}</Alert>}
          {notice && !error && (
            <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              {notice}
            </p>
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
              disabled={method === 'code' && codeSent}
              leftIcon={<Mail className="w-5 h-5 text-gray-400" />}
            />

            {method === 'code' && codeSent && (
              <Input
                label="Sign-in code"
                name="code"
                value={formData.code}
                onChange={handleChange}
                error={errors.code}
                placeholder="123456"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                required
                autoFocus
                leftIcon={<KeyRound className="w-5 h-5 text-gray-400" />}
              />
            )}

            {method === 'password' && (
              <Input
                label="Password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                error={errors.password}
                autoComplete="current-password"
                required
                leftIcon={<Lock className="w-5 h-5 text-gray-400" />}
              />
            )}
          </div>

          <Button type="submit" fullWidth loading={loading} className="py-3">
            {submitLabel}
          </Button>

          {method === 'code' && codeSent && (
            <div className="flex justify-between text-sm">
              <button type="button" className="font-medium text-primary hover:underline" onClick={changeEmail}>
                Use a different email
              </button>
              <button type="button" className="font-medium text-primary hover:underline disabled:opacity-50" disabled={loading} onClick={sendCode}>
                Send a new code
              </button>
            </div>
          )}

          <button type="button" className="block w-full text-center text-sm font-medium text-primary hover:underline" onClick={switchMethod}>
            {method === 'code' ? 'Sign in with a password instead' : 'Sign in with an email code instead'}
          </button>

          <Button type="button" variant="outline" fullWidth className="py-3" onClick={() => navigate('/staff-login')}>
            Staff login
          </Button>
        </form>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </AuthLayout>
  )
}

export default Login
