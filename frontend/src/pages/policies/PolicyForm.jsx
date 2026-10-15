import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Save } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { policyService, vehicleService } from '../../services'
import { useAuth } from '../../context/useAuth'

const today = () => new Date().toISOString().slice(0, 10)
const nextYear = () => new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().slice(0, 10)

export function PolicyForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { user } = useAuth()
  const isEdit = Boolean(id)
  const canAssignCustomer = ['admin', 'employee'].includes(user?.role)
  const [customers, setCustomers] = useState([])
  const [agents, setAgents] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    customer: '',
    agent: user?.role === 'employee' ? String(user.id) : '',
    vehicle: '',
    type: 'auto_comprehensive',
    status: 'pending',
    startDate: today(),
    endDate: nextYear(),
    premium: '',
    deductible: '500',
    paymentFrequency: 'annual',
    autoRenew: true,
    propertyAddress: '',
    propertyType: '',
    propertyYearBuilt: '',
    propertySquareFootage: '',
  })

  const selectedCustomer = canAssignCustomer ? formData.customer : user?.id
  const isAutoPolicy = formData.type.startsWith('auto_')
  const customerOptions = useMemo(
    () => customers.map((customer) => ({ value: String(customer.id), label: `${customer.name} (${customer.email})` })),
    [customers],
  )
  const agentOptions = useMemo(
    () => agents.map((agent) => ({ value: String(agent.id), label: `${agent.name} (${agent.email})` })),
    [agents],
  )
  const vehicleOptions = useMemo(
    () => vehicles.map((vehicle) => ({ value: String(vehicle.id), label: vehicle.label || `${vehicle.year} ${vehicle.make} ${vehicle.model} (${vehicle.license_plate})` })),
    [vehicles],
  )

  useEffect(() => {
    let active = true
    const loadForm = async () => {
      try {
        if (canAssignCustomer) {
          const options = await policyService.getPolicyFormOptions()
          if (active) {
            setCustomers(options.customers || [])
            setAgents(options.agents || [])
          }
        }
        if (isEdit) {
          const policy = await policyService.getPolicy(id)
          if (active) {
            setFormData((current) => ({
              ...current,
              customer: String(policy.customer || ''),
              agent: String(policy.agent || ''),
              vehicle: String(policy.vehicle || ''),
              type: policy.type,
              status: policy.status,
              startDate: policy.start_date,
              endDate: policy.end_date,
              premium: policy.premium,
              deductible: policy.deductible,
              paymentFrequency: policy.payment_frequency,
              autoRenew: policy.auto_renew,
              propertyAddress: policy.property_address || '',
              propertyType: policy.property_type || '',
              propertyYearBuilt: policy.property_year_built || '',
              propertySquareFootage: policy.property_square_footage || '',
            }))
          }
        }
      } catch (err) {
        if (active) setError(err.response?.data?.detail || 'Unable to load the policy form data.')
      }
    }
    loadForm()
    return () => { active = false }
  }, [canAssignCustomer, id, isEdit])

  useEffect(() => {
    let active = true
    const loadVehicles = async () => {
      setVehicles([])
      if (!selectedCustomer) return
      try {
        let rows
        if (canAssignCustomer) {
          const options = await policyService.getPolicyFormOptions({ customer: selectedCustomer, ...(isEdit ? { policy: id } : {}) })
          rows = options.vehicles || []
        } else {
          const response = await vehicleService.getVehicles()
          rows = (Array.isArray(response) ? response : response.results || []).map((vehicle) => ({
            id: vehicle.id,
            label: `${vehicle.year} ${vehicle.make} ${vehicle.model} (${vehicle.license_plate})`,
          }))
        }
        if (active) setVehicles(rows)
      } catch (err) {
        if (active) setError(err.response?.data?.detail || 'Unable to load vehicles for this customer.')
      }
    }
    loadVehicles()
    return () => { active = false }
  }, [canAssignCustomer, id, isEdit, selectedCustomer])

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target
    setFormData((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
      ...(name === 'customer' && !isEdit ? { vehicle: '' } : {}),
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = {
        ...(canAssignCustomer ? { customer: Number(formData.customer) } : { customer: user.id }),
        agent: formData.agent ? Number(formData.agent) : null,
        vehicle: formData.vehicle ? Number(formData.vehicle) : null,
        type: formData.type,
        status: formData.status,
        start_date: formData.startDate,
        end_date: formData.endDate,
        premium: Number(formData.premium),
        deductible: Number(formData.deductible),
        payment_frequency: formData.paymentFrequency,
        auto_renew: formData.autoRenew,
        property_address: formData.propertyAddress,
        property_type: formData.propertyType,
        property_year_built: Number(formData.propertyYearBuilt) || null,
        property_square_footage: Number(formData.propertySquareFootage) || null,
      }
      if (isEdit) await policyService.updatePolicy(id, payload)
      else await policyService.createPolicy(payload)
      navigate('/policies')
    } catch (err) {
      const details = err.response?.data?.error?.details || err.response?.data
      setError(typeof details === 'object'
        ? Object.entries(details).filter(([field]) => field !== 'detail').map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`).join('; ') || err.response?.data?.detail || 'Failed to save policy.'
        : details?.detail || 'Failed to save policy.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page max-w-3xl">
      <div className="page-header">
        <div>
          <Link to="/policies" className="mb-2 inline-flex items-center gap-2 text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-4 w-4" /> Back to Policies
          </Link>
          <h1 className="page-title">{isEdit ? 'Edit Policy' : 'Create Policy'}</h1>
          <p className="page-subtitle">The policy, customer, assigned agent, and covered vehicle are saved as linked records.</p>
        </div>
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="card">
          <div className="card-header"><h2 className="card-title">Policy Details</h2></div>
          <div className="card-content grid grid-cols-1 gap-4 md:grid-cols-2">
            {canAssignCustomer && (
              <Select label="Customer" name="customer" value={formData.customer} onChange={handleChange} options={customerOptions} placeholder="Select customer" required />
            )}
            {canAssignCustomer && (
              <Select label="Assigned Agent" name="agent" value={formData.agent} onChange={handleChange} options={agentOptions} placeholder="Select agent (optional)" />
            )}
            <Select label="Policy Type" name="type" value={formData.type} onChange={handleChange} options={[
              { value: 'auto_comprehensive', label: 'Comprehensive Auto' },
              { value: 'auto_collision', label: 'Collision Auto' },
              { value: 'auto_liability', label: 'Liability Auto' },
              { value: 'homeowners', label: 'Homeowners' },
              { value: 'renters', label: 'Renters' },
              { value: 'umbrella', label: 'Umbrella' },
            ]} />
            <Select label="Status" name="status" value={formData.status} onChange={handleChange} options={[
              { value: 'pending', label: 'Pending' }, { value: 'active', label: 'Active' },
              { value: 'suspended', label: 'Suspended' }, { value: 'expired', label: 'Expired' }, { value: 'cancelled', label: 'Cancelled' },
            ]} />
            <Input label="Start Date" name="startDate" type="date" value={formData.startDate} onChange={handleChange} required />
            <Input label="End Date" name="endDate" type="date" value={formData.endDate} onChange={handleChange} required />
            <Input label="Premium" name="premium" type="number" min="0" step="0.01" value={formData.premium} onChange={handleChange} required />
            <Input label="Deductible" name="deductible" type="number" min="0" step="0.01" value={formData.deductible} onChange={handleChange} required />
            <Select label="Payment Frequency" name="paymentFrequency" value={formData.paymentFrequency} onChange={handleChange} options={[
              { value: 'annual', label: 'Annual' }, { value: 'semi_annual', label: 'Semi-Annual' },
              { value: 'quarterly', label: 'Quarterly' }, { value: 'monthly', label: 'Monthly' },
            ]} />
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" name="autoRenew" checked={formData.autoRenew} onChange={handleChange} className="h-4 w-4" /> Auto renew
            </label>
          </div>
        </section>

        {isAutoPolicy ? (
          <section className="card">
            <div className="card-header"><h2 className="card-title">Covered Vehicle</h2></div>
            <div className="card-content">
              <Select label="Vehicle belonging to this customer" name="vehicle" value={formData.vehicle} onChange={handleChange} options={vehicleOptions} placeholder={selectedCustomer ? 'Select an unassigned vehicle' : 'Choose a customer first'} required />
              {selectedCustomer && vehicleOptions.length === 0 && <p className="mt-2 text-sm text-amber-700">This customer has no unassigned vehicles. Add a vehicle to the customer before issuing an auto policy.</p>}
            </div>
          </section>
        ) : ['homeowners', 'renters'].includes(formData.type) ? (
          <section className="card">
            <div className="card-header"><h2 className="card-title">Insured Property</h2></div>
            <div className="card-content grid grid-cols-1 gap-4 md:grid-cols-2">
              <Input label="Property Address" name="propertyAddress" value={formData.propertyAddress} onChange={handleChange} />
              <Input label="Property Type" name="propertyType" value={formData.propertyType} onChange={handleChange} placeholder="Single-family home, apartment…" />
              <Input label="Year Built" name="propertyYearBuilt" type="number" value={formData.propertyYearBuilt} onChange={handleChange} />
              <Input label="Square Footage" name="propertySquareFootage" type="number" value={formData.propertySquareFootage} onChange={handleChange} />
            </div>
          </section>
        ) : null}

        <div className="flex justify-end gap-3">
          <Link to="/policies"><Button type="button" variant="ghost">Cancel</Button></Link>
          <Button type="submit" disabled={loading || (canAssignCustomer && !formData.customer) || (isAutoPolicy && vehicleOptions.length === 0)}>
            <Save className="mr-2 h-4 w-4" /> {loading ? 'Saving…' : isEdit ? 'Update Policy' : 'Create Policy'}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default PolicyForm
