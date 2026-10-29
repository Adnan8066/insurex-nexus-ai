import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Car, Save } from 'lucide-react'
import { format } from 'date-fns'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Input, Select } from '../../components/forms/FormFields'
import { policyService, vehicleService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { formatApiError } from '../../services/api'
import { VEHICLE_STATUSES } from '../../constants/domain'

// 17 characters; letters and digits except I, O and Q (same rule as the backend).
const VIN_PATTERN = /^[A-HJ-NPR-Z0-9]{17}$/

// Backend field name -> form field name, so server errors show next to the right input.
const FIELD_MAP = {
  customer: 'customer',
  policy: 'policy',
  make: 'make',
  model: 'model',
  year: 'year',
  vin: 'vin',
  color: 'color',
  license_plate: 'licensePlate',
  license_state: 'licenseState',
  registration_expiry: 'registrationExpiry',
  purchase_date: 'purchaseDate',
  purchase_price: 'purchasePrice',
  current_mileage: 'currentMileage',
  fuel_type: 'fuelType',
  transmission: 'transmission',
  status: 'status',
}

const firstMessage = (value) => {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(firstMessage).find(Boolean) || ''
  return ''
}

function serverFieldErrors(err) {
  const data = err?.response?.data
  if (!data || typeof data !== 'object') return {}
  const source = data.error && typeof data.error === 'object' && data.error.details && typeof data.error.details === 'object'
    ? data.error.details
    : data
  return Object.entries(source).reduce((acc, [field, value]) => {
    const key = FIELD_MAP[field]
    const message = firstMessage(value)
    if (key && message) acc[key] = message
    return acc
  }, {})
}

const todayLocal = () => format(new Date(), 'yyyy-MM-dd')

export function VehicleForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const { user } = useAuth()
  const isEdit = Boolean(id)
  const canAssignCustomer = ['admin', 'employee'].includes(user?.role)
  const maxYear = new Date().getFullYear() + 1
  const [customers, setCustomers] = useState([])
  const [policies, setPolicies] = useState([])
  // The vehicle's policy when the form loaded; passed to the options endpoint so it stays selectable.
  const [originalPolicy, setOriginalPolicy] = useState('')
  const [formData, setFormData] = useState({
    customer: searchParams.get('customer') || '', policy: '', make: '', model: '', year: new Date().getFullYear(),
    vin: '', licensePlate: '', licenseState: '', color: '', fuelType: 'gasoline', transmission: 'automatic',
    currentMileage: '', registrationExpiry: '', purchaseDate: '', purchasePrice: '', status: 'active',
  })
  const [loading, setLoading] = useState(false)
  const [loadingVehicle, setLoadingVehicle] = useState(isEdit)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const selectedCustomer = canAssignCustomer ? formData.customer : user?.id

  const today = todayLocal()
  const registrationExpired = Boolean(formData.registrationExpiry) && formData.registrationExpiry < today
  const showExpiredWarning = registrationExpired && formData.status === 'active'

  const customerOptions = useMemo(() => customers.map((customer) => ({
    value: String(customer.id), label: `${customer.name} (${customer.email})`,
  })), [customers])
  const policyOptions = useMemo(() => policies.map((policy) => ({
    value: String(policy.id), label: policy.label || `${policy.policy_number} (${policy.status})`,
  })), [policies])

  useEffect(() => {
    let active = true
    const loadForm = async () => {
      try {
        if (canAssignCustomer) {
          const options = await policyService.getPolicyFormOptions()
          if (active) setCustomers(options.customers || [])
        }
        if (isEdit) {
          const vehicle = await vehicleService.getVehicle(id)
          if (active) {
            setOriginalPolicy(String(vehicle.policy || ''))
            setFormData((current) => ({
              ...current,
              customer: String(vehicle.customer || ''),
              policy: String(vehicle.policy || ''),
              make: vehicle.make || '',
              model: vehicle.model || '',
              year: vehicle.year || '',
              vin: vehicle.vin || '',
              licensePlate: vehicle.license_plate || '',
              licenseState: vehicle.license_state || '',
              color: vehicle.color || '',
              fuelType: vehicle.fuel_type || 'gasoline',
              transmission: vehicle.transmission || 'automatic',
              currentMileage: vehicle.current_mileage ?? '',
              registrationExpiry: vehicle.registration_expiry || '',
              purchaseDate: vehicle.purchase_date || '',
              purchasePrice: vehicle.purchase_price || '',
              status: vehicle.status || 'active',
            }))
          }
        } else if (canAssignCustomer && active && searchParams.get('customer')) {
          setFormData((current) => ({ ...current, customer: searchParams.get('customer') }))
        } else if (!canAssignCustomer && active) {
          setFormData((current) => ({ ...current, customer: String(user?.id || '') }))
        }
      } catch (err) {
        if (!active) return
        if (isEdit && err.response?.status === 404) setNotFound(true)
        else setError(formatApiError(err, 'Unable to load vehicle form data.'))
      } finally {
        if (active) setLoadingVehicle(false)
      }
    }
    loadForm()
    return () => { active = false }
  }, [canAssignCustomer, id, isEdit, searchParams, user?.id])

  useEffect(() => {
    let active = true
    const loadPolicies = async () => {
      setPolicies([])
      if (!selectedCustomer) return
      try {
        let rows
        if (canAssignCustomer) {
          const options = await policyService.getPolicyFormOptions({
            customer: selectedCustomer,
            ...(originalPolicy ? { policy: originalPolicy } : {}),
          })
          rows = options.policies || []
        } else {
          const response = await policyService.getPolicies()
          rows = (Array.isArray(response) ? response : response.results || []).map((policy) => ({
            id: policy.id,
            label: `${policy.policy_number} — ${policy.type} (${policy.status})`,
          }))
        }
        if (active) setPolicies(rows)
      } catch (err) {
        if (active) setError(formatApiError(err, 'Unable to load policies for this customer.'))
      }
    }
    loadPolicies()
    return () => { active = false }
  }, [canAssignCustomer, originalPolicy, selectedCustomer])

  const handleChange = (event) => {
    const { name } = event.target
    let { value } = event.target
    if (name === 'vin' || name === 'licenseState') value = value.toUpperCase().replace(/\s/g, '')
    setFormData((current) => ({
      ...current,
      [name]: value,
      ...(name === 'customer' ? { policy: '' } : {}),
    }))
    if (fieldErrors[name]) setFieldErrors((current) => ({ ...current, [name]: '' }))
  }

  const validate = () => {
    const errors = {}
    if (!isEdit && !VIN_PATTERN.test(formData.vin)) {
      errors.vin = 'VIN must be 17 letters and digits (the letters I, O and Q are not used).'
    }
    const year = Number(formData.year)
    if (!Number.isInteger(year) || year < 1900 || year > maxYear) {
      errors.year = `Enter a year between 1900 and ${maxYear}.`
    }
    if (!/^[A-Z]{2}$/.test(formData.licenseState || '')) {
      errors.licenseState = 'Enter the 2-letter state code, e.g. MH or KA.'
    }
    if (formData.purchaseDate && formData.purchaseDate > today) {
      errors.purchaseDate = 'Purchase date cannot be in the future.'
    }
    if (formData.currentMileage !== '' && Number(formData.currentMileage) < 0) {
      errors.currentMileage = 'Odometer reading cannot be negative.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    if (!validate()) {
      setError('Please fix the highlighted fields.')
      return
    }
    setLoading(true)
    try {
      const payload = {
        ...(canAssignCustomer && !isEdit ? { customer: Number(formData.customer) } : {}),
        policy: formData.policy ? Number(formData.policy) : null,
        make: formData.make,
        model: formData.model,
        year: Number(formData.year),
        // The backend ignores VIN changes on update, so only send it when creating.
        ...(isEdit ? {} : { vin: formData.vin }),
        color: formData.color,
        license_plate: formData.licensePlate,
        license_state: formData.licenseState,
        registration_expiry: formData.registrationExpiry || null,
        purchase_date: formData.purchaseDate || null,
        purchase_price: formData.purchasePrice || null,
        current_mileage: Number(formData.currentMileage) || 0,
        fuel_type: formData.fuelType,
        transmission: formData.transmission,
        status: formData.status,
      }
      if (isEdit) await vehicleService.updateVehicle(id, payload)
      else await vehicleService.createVehicle(payload)
      if (!isEdit && searchParams.get('returnTo') === 'policy' && formData.customer) {
        navigate(`/policies/new?customer=${encodeURIComponent(formData.customer)}`)
      } else {
        navigate(isEdit ? `/vehicles/${id}` : '/vehicles')
      }
    } catch (err) {
      const errors = serverFieldErrors(err)
      setFieldErrors(errors)
      setError(Object.keys(errors).length
        ? 'Please fix the highlighted fields.'
        : formatApiError(err, 'Failed to save vehicle. Check the entered details and try again.'))
    } finally {
      setLoading(false)
    }
  }

  if (notFound) {
    return (
      <div className="page max-w-3xl">
        <Link to="/vehicles" className="mb-4 inline-flex items-center gap-2 text-gray-500 hover:text-gray-700"><ArrowLeft className="h-4 w-4" />Back to Vehicles</Link>
        <Card>
          <EmptyState
            icon={<Car className="w-12 h-12" />}
            title="Vehicle not found"
            description="This vehicle does not exist or you do not have access to it."
            action={<Button asChild variant="outline"><Link to="/vehicles">Back to Vehicles</Link></Button>}
          />
        </Card>
      </div>
    )
  }

  if (loadingVehicle) {
    return <div className="page max-w-3xl p-8 text-center text-gray-500" role="status">Loading vehicle…</div>
  }

  return (
    <div className="page max-w-3xl">
      <div className="page-header">
        <div>
          <Link to={isEdit ? `/vehicles/${id}` : '/vehicles'} className="mb-2 inline-flex items-center gap-2 text-gray-500 hover:text-gray-700"><ArrowLeft className="h-4 w-4" />{isEdit ? 'Back to Vehicle' : 'Back to Vehicles'}</Link>
          <h1 className="page-title">{isEdit ? 'Edit Vehicle' : 'Add Vehicle'}</h1>
          <p className="page-subtitle">A policy is optional and can be added later.</p>
        </div>
      </div>
      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        <section className="card">
          <div className="card-header"><h2 className="card-title">Vehicle Information</h2></div>
          <div className="card-content grid grid-cols-1 gap-4 md:grid-cols-2">
            {canAssignCustomer && <Select label="Customer" name="customer" value={formData.customer} onChange={handleChange} options={customerOptions} placeholder="Select customer" required disabled={isEdit} error={fieldErrors.customer} />}
            <Select label="Insuring Policy (optional)" name="policy" value={formData.policy} onChange={handleChange} options={policyOptions} placeholder="No policy" allowEmpty error={fieldErrors.policy} />
            <Input label="Make" name="make" value={formData.make} onChange={handleChange} required error={fieldErrors.make} />
            <Input label="Model" name="model" value={formData.model} onChange={handleChange} required error={fieldErrors.model} />
            <Input label="Year" name="year" type="number" min="1900" max={maxYear} value={formData.year} onChange={handleChange} required error={fieldErrors.year} />
            <Input
              label="VIN"
              name="vin"
              value={formData.vin}
              onChange={handleChange}
              required
              maxLength={17}
              disabled={isEdit}
              autoCapitalize="characters"
              spellCheck={false}
              className="font-mono"
              error={fieldErrors.vin}
              hint={isEdit ? 'The VIN cannot be changed after the vehicle is added.' : `17 characters (${formData.vin.length}/17). Letters I, O and Q are not used.`}
            />
            <Input label="License Plate" name="licensePlate" value={formData.licensePlate} onChange={handleChange} required error={fieldErrors.licensePlate} />
            <Input label="State Code" name="licenseState" value={formData.licenseState} onChange={handleChange} required maxLength={2} placeholder="e.g. MH" hint="2-letter registration state code" error={fieldErrors.licenseState} />
            <Input label="Color" name="color" value={formData.color} onChange={handleChange} required error={fieldErrors.color} />
            <Select label="Fuel Type" name="fuelType" value={formData.fuelType} onChange={handleChange} error={fieldErrors.fuelType} options={[
              { value: 'gasoline', label: 'Petrol' }, { value: 'diesel', label: 'Diesel' },
              { value: 'hybrid', label: 'Hybrid' }, { value: 'electric', label: 'Electric' }, { value: 'plugin_hybrid', label: 'Plug-in Hybrid' },
            ]} />
            <Select label="Transmission" name="transmission" value={formData.transmission} onChange={handleChange} error={fieldErrors.transmission} options={[
              { value: 'automatic', label: 'Automatic' }, { value: 'manual', label: 'Manual' },
              { value: 'cvt', label: 'CVT' }, { value: 'semi_automatic', label: 'Semi-Automatic' },
            ]} />
            <Input label="Odometer (km)" name="currentMileage" type="number" min="0" value={formData.currentMileage} onChange={handleChange} error={fieldErrors.currentMileage} />
            <Input label="Registration Expiry" name="registrationExpiry" type="date" value={formData.registrationExpiry} onChange={handleChange} error={fieldErrors.registrationExpiry} />
            <Input label="Purchase Date" name="purchaseDate" type="date" max={today} value={formData.purchaseDate} onChange={handleChange} error={fieldErrors.purchaseDate} />
            <Input label="Purchase Price" name="purchasePrice" type="number" min="0" step="0.01" value={formData.purchasePrice} onChange={handleChange} error={fieldErrors.purchasePrice} />
            <Select label="Status" name="status" value={formData.status} onChange={handleChange} options={VEHICLE_STATUSES} error={fieldErrors.status} />
          </div>
          {showExpiredWarning && (
            <div className="mx-6 mb-6 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800" role="status">
              The registration expired on {formData.registrationExpiry}. You can still save this vehicle as Active, but the registration should be renewed.
            </div>
          )}
        </section>

        <div className="flex justify-end gap-3">
          <Button asChild variant="ghost"><Link to={isEdit ? `/vehicles/${id}` : '/vehicles'}>Cancel</Link></Button>
          <Button type="submit" disabled={loading || (canAssignCustomer && !formData.customer)}><Save className="mr-2 h-4 w-4" />{loading ? 'Saving…' : 'Save Vehicle'}</Button>
        </div>
      </form>
    </div>
  )
}

export default VehicleForm
