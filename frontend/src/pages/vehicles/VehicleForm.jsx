import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Save } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { policyService, vehicleService } from '../../services'
import { useAuth } from '../../context/useAuth'

function formatApiError(payload) {
  if (typeof payload === 'string') return payload
  if (Array.isArray(payload)) return payload.map(formatApiError).filter(Boolean).join(', ')
  if (!payload || typeof payload !== 'object') return ''

  const message = payload.detail || payload.message
  if (message && typeof message === 'string') return message

  const errors = payload.error && typeof payload.error === 'object' ? payload.error : payload
  return Object.entries(errors)
    .filter(([key]) => key !== 'success')
    .map(([field, value]) => {
      const text = formatApiError(value)
      return text ? `${field.replaceAll('_', ' ')}: ${text}` : ''
    })
    .filter(Boolean)
    .join('; ')
}

export function VehicleForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { user } = useAuth()
  const isEdit = Boolean(id)
  const canAssignCustomer = ['admin', 'employee'].includes(user?.role)
  const [customers, setCustomers] = useState([])
  const [policies, setPolicies] = useState([])
  const [formData, setFormData] = useState({
    customer: '', policy: '', make: '', model: '', year: new Date().getFullYear(),
    vin: '', licensePlate: '', color: '', fuelType: 'gasoline', transmission: 'automatic',
    currentMileage: '', registrationExpiry: '', purchaseDate: '', purchasePrice: '', status: 'active',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const selectedCustomer = canAssignCustomer ? formData.customer : user?.id

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
          if (active) setFormData((current) => ({
            ...current,
            customer: String(vehicle.customer || ''),
            policy: String(vehicle.policy || ''),
            make: vehicle.make,
            model: vehicle.model,
            year: vehicle.year,
            vin: vehicle.vin,
            licensePlate: vehicle.license_plate,
            licenseState: vehicle.license_state,
            color: vehicle.color,
            fuelType: vehicle.fuel_type,
            transmission: vehicle.transmission,
            currentMileage: vehicle.current_mileage,
            registrationExpiry: vehicle.registration_expiry || '',
            purchaseDate: vehicle.purchase_date || '',
            purchasePrice: vehicle.purchase_price || '',
            status: vehicle.status,
          }))
        } else if (!canAssignCustomer && active) {
          setFormData((current) => ({ ...current, customer: String(user?.id || '') }))
        }
      } catch (err) {
        if (active) setError(err.response?.data?.detail || 'Unable to load vehicle form data.')
      }
    }
    loadForm()
    return () => { active = false }
  }, [canAssignCustomer, id, isEdit, user?.id])

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
            ...(formData.policy ? { policy: formData.policy } : {}),
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
        if (active) setError(err.response?.data?.detail || 'Unable to load policies for this customer.')
      }
    }
    loadPolicies()
    return () => { active = false }
  }, [canAssignCustomer, formData.policy, selectedCustomer])

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData((current) => ({
      ...current,
      [name]: value,
      ...(name === 'customer' ? { policy: '' } : {}),
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = {
        ...(canAssignCustomer ? { customer: Number(formData.customer) } : {}),
        policy: formData.policy ? Number(formData.policy) : null,
        make: formData.make,
        model: formData.model,
        year: Number(formData.year),
        vin: formData.vin,
        color: formData.color,
        license_plate: formData.licensePlate,
        license_state: formData.licenseState || 'IL',
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
      navigate('/vehicles')
    } catch (err) {
      const message = formatApiError(err.response?.data)
      setError(message || (err.response
        ? 'Failed to save vehicle. Check the entered details and try again.'
        : 'Could not reach the vehicle service. Check that the backend is running and try again.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page max-w-3xl">
      <div className="page-header">
        <div>
          <Link to="/vehicles" className="mb-2 inline-flex items-center gap-2 text-gray-500 hover:text-gray-700"><ArrowLeft className="h-4 w-4" />Back to Vehicles</Link>
          <h1 className="page-title">{isEdit ? 'Edit Vehicle' : 'Add Vehicle'}</h1>
          <p className="page-subtitle">Link the vehicle to its customer and, when available, its policy.</p>
        </div>
      </div>
      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="card">
          <div className="card-header"><h2 className="card-title">Vehicle Information</h2></div>
          <div className="card-content grid grid-cols-1 gap-4 md:grid-cols-2">
            {canAssignCustomer && <Select label="Customer" name="customer" value={formData.customer} onChange={handleChange} options={customerOptions} placeholder="Select customer" required disabled={isEdit} />}
            <Select label="Insuring Policy" name="policy" value={formData.policy} onChange={handleChange} options={policyOptions} placeholder="No policy linked yet" />
            <Input label="Make" name="make" value={formData.make} onChange={handleChange} required />
            <Input label="Model" name="model" value={formData.model} onChange={handleChange} required />
            <Input label="Year" name="year" type="number" min="1900" value={formData.year} onChange={handleChange} required />
            <Input label="VIN" name="vin" value={formData.vin} onChange={handleChange} required />
            <Input label="License Plate" name="licensePlate" value={formData.licensePlate} onChange={handleChange} required />
            <Input label="License State" name="licenseState" value={formData.licenseState || ''} onChange={handleChange} />
            <Input label="Color" name="color" value={formData.color} onChange={handleChange} required />
            <Select label="Fuel Type" name="fuelType" value={formData.fuelType} onChange={handleChange} options={[
              { value: 'gasoline', label: 'Gasoline' }, { value: 'diesel', label: 'Diesel' },
              { value: 'hybrid', label: 'Hybrid' }, { value: 'electric', label: 'Electric' }, { value: 'plugin_hybrid', label: 'Plug-in Hybrid' },
            ]} />
            <Select label="Transmission" name="transmission" value={formData.transmission} onChange={handleChange} options={[
              { value: 'automatic', label: 'Automatic' }, { value: 'manual', label: 'Manual' },
              { value: 'cvt', label: 'CVT' }, { value: 'semi_automatic', label: 'Semi-Automatic' },
            ]} />
            <Input label="Current Mileage" name="currentMileage" type="number" min="0" value={formData.currentMileage} onChange={handleChange} />
            <Input label="Registration Expiry" name="registrationExpiry" type="date" value={formData.registrationExpiry} onChange={handleChange} />
            <Input label="Purchase Date" name="purchaseDate" type="date" value={formData.purchaseDate} onChange={handleChange} />
            <Input label="Purchase Price" name="purchasePrice" type="number" min="0" step="0.01" value={formData.purchasePrice} onChange={handleChange} />
            <Select label="Status" name="status" value={formData.status} onChange={handleChange} options={[
              { value: 'active', label: 'Active' }, { value: 'inactive', label: 'Inactive' },
              { value: 'sold', label: 'Sold' }, { value: 'total_loss', label: 'Total Loss' }, { value: 'salvage', label: 'Salvage' },
            ]} />
          </div>
        </section>

        <div className="flex justify-end gap-3">
          <Button asChild variant="ghost"><Link to="/vehicles">Cancel</Link></Button>
          <Button type="submit" disabled={loading || (canAssignCustomer && !formData.customer)}><Save className="mr-2 h-4 w-4" />{loading ? 'Saving…' : 'Save Vehicle'}</Button>
        </div>
      </form>
    </div>
  )
}

export default VehicleForm
