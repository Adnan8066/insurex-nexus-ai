import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Shield, Mail, Lock, ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/forms/FormFields'
import { clsx } from 'clsx'

export function ForgotPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { forgotPassword, resetPassword } = useAuth()
  const isReset = searchParams.has('token')
  const token = searchParams.get('token')

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [errors, setErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [step, setStep] = useState('email')

  const validateEmail = () => {
    const newErrors = {}
    if (!formData.email) newErrors.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) newErrors.email = 'Invalid email format'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const validatePassword = () => {
    const newErrors = {}
    if (!formData.password) newErrors.password = 'Password is required'
    else if (formData.password.length < 8) newErrors.password = 'Password must be at least 8 characters'
    if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'Passwords do not match'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (isReset) {
      if (!validatePassword()) return
      setLoading(true)
      setError('')
      const result = await resetPassword(token, formData.password)
      if (result.success) {
        setSuccess(true)
        setTimeout(() => navigate('/login'), 3000)
      } else {
        setError(result.error)
      }
      setLoading(false)
    } else {
      if (step === 'email') {
        if (!validateEmail()) return
        setLoading(true)
        setError('')
        const result = await forgotPassword(formData.email)
        if (result.success) {
          setStep('sent')
        } else {
          setError(result.error)
        }
        setLoading(false)
      }
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  if (isReset && success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full text-center">
          <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Password Reset Complete</h1>
          <p className="text-gray-600 mb-8">Your password has been successfully reset. Redirecting to login...</p>
          <Button onClick={() => navigate('/login')} variant="secondary">
            Go to Login
          </Button>
        </div>
      </div>
    )
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
          <Link to="/login" className="inline-flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-6">
            <ArrowLeft className="w-4 h-4" />
            Back to login
          </Link>
          {isReset ? (
            <>
              <h1 className="text-3xl font-bold text-gray-900">Reset your password</h1>
              <p className="mt-2 text-gray-600">Enter your new password below</p>
            </>
          ) : step === 'sent' ? (
            <>
              <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-6">
                <Mail className="w-8 h-8 text-primary" />
              </div>
              <h1 className="text-3xl font-bold text-gray-900">Check your email</h1>
              <p className="mt-2 text-gray-600">
                We've sent a password reset link to <strong>{formData.email}</strong>
              </p>
              <p className="mt-2 text-sm text-gray-500">The link will expire in 1 hour</p>
            </>
          ) : (
            <>
              <h1 className="text-3xl font-bold text-gray-900">Forgot password?</h1>
              <p className="mt-2 text-gray-600">Enter your email and we'll send you a reset link</p>
            </>
          )}
        </div>

        {step !== 'sent' && (
          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {isReset ? (
              <div className="space-y-4">
                <Input
                  label="New password"
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  error={errors.password}
                  placeholder="••••••••"
                  autoComplete="new-password"
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
                  hint="At least 8 characters"
                />

                <Input
                  label="Confirm new password"
                  type={showPassword ? 'text' : 'password'}
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  error={errors.confirmPassword}
                  placeholder="••••••••"
                  autoComplete="new-password"
                  required
                  leftIcon={<Lock className="w-5 h-5 text-gray-400" />}
                />
              </div>
            ) : (
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
            )}

            <Button type="submit" fullWidth loading={loading} className="py-3">
              {isReset ? 'Reset password' : step === 'email' ? 'Send reset link' : 'Resend link'}
            </Button>
          </form>
        )}

        {step === 'sent' && (
          <div className="text-center">
            <Button variant="secondary" onClick={() => setStep('email')}>
              Resend email
            </Button>
            <p className="mt-4 text-sm text-gray-600">
              Didn't receive the email?{' '}
              <button onClick={() => setStep('email')} className="font-medium text-primary hover:underline">
                Try again
              </button>
            </p>
          </div>
        )}

        {!isReset && step !== 'sent' && (
          <div className="text-center">
            <p className="text-sm text-gray-600">
              Remember your password?{' '}
              <Link to="/login" className="font-medium text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default ForgotPassword