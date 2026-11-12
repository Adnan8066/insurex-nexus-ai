import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Mail, Car, Smartphone } from 'lucide-react'
import { useAuth } from '../../context/useAuth'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/forms/FormFields'
import { AuthLayout } from '../../components/auth/BrandArtwork'
import { Alert } from '../../components/ui/Alert'
import { DemoLogins } from '../../components/auth/DemoLogins'
import { demoForm } from '../../components/auth/demoAccounts'

const emptyForm = { email: '', license_plate: '', mobile_number: '' }

export function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { customerLogin } = useAuth()
  const [formData, setFormData] = useState(() => ({ ...emptyForm, ...demoForm(location.state?.demoAccount) }))
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const validate = () => {
    const newErrors = {}
    if (!formData.email) newErrors.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) newErrors.email = 'Invalid email format'
    if (!formData.license_plate.trim()) newErrors.license_plate = 'Vehicle registration number is required'
    const digits = formData.mobile_number.replace(/\D/g, '')
    if (!digits) newErrors.mobile_number = 'Mobile number is required'
    else if (digits.length !== 10 && !(digits.length === 12 && digits.startsWith('91'))) {
      newErrors.mobile_number = 'Enter a 10-digit mobile number'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    setError('')

    const result = await customerLogin(formData)
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
          <h1 className="text-3xl font-bold text-gray-900">Customer sign in</h1>
          <p className="mt-2 text-gray-600">Sign in with your email, vehicle number and mobile number</p>
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
              label="Vehicle registration number"
              name="license_plate"
              value={formData.license_plate}
              onChange={handleChange}
              error={errors.license_plate}
              placeholder="KL 01 Z 7315"
              autoComplete="off"
              required
              leftIcon={<Car className="w-5 h-5 text-gray-400" />}
            />

            <Input
              label="Mobile number"
              type="tel"
              name="mobile_number"
              value={formData.mobile_number}
              onChange={handleChange}
              error={errors.mobile_number}
              placeholder="+91 98120 34567"
              autoComplete="tel"
              required
              leftIcon={<Smartphone className="w-5 h-5 text-gray-400" />}
            />
          </div>

          <Button type="submit" fullWidth loading={loading} className="py-3">
            Sign in
          </Button>

          <Button type="button" variant="outline" fullWidth className="py-3" onClick={() => navigate('/staff-login')}>
            Staff login
          </Button>

          <DemoLogins
            page="/login"
            onFill={(form) => {
              setFormData({ ...emptyForm, ...form })
              setErrors({})
            }}
          />
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
