import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Save } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { policyService, vehicleService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { policyTiers } from '../../data/policyTiers'
import { formatCurrency } from '../../utils/helpers'

const today = () => new Date().toISOString().slice(0, 10)
const nextYear = () => new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().slice(0, 10)

export function PolicyForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const { user } = useAuth()
  const isEdit = Boolean(id)
  const canAssignCustomer = ['admin', 'employee'].includes(user?.role)
  const [customers, setCustomers] = useState([])
  const [agents, setAgents] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [quote, setQuote] = useState(null)
  const [formData, setFormData] = useState({
    customer: searchParams.get('customer') || '',
    agent: user?.role === 'employee' ? String(user.id) : '',
    vehicle: '',
    policyTierId: '',
    coverage: {},
    type: 'auto_comprehensive',
    status: 'pending',
    startDate: today(),
    endDate: nextYear(),
    premium: '',
    deductible: '500',
    assetValue: '',
    coverageLimit: '',
    riskScore: '25',
    paymentFrequency: 'annual',
    autoRenew: true,
    propertyAddress: '',
    propertyType: '',
    propertyYearBuilt: '',
    propertySquareFootage: '',
  })

  const selectedCustomer = canAssignCustomer ? formData.customer : user?.id
  const selectedTier = policyTiers.find((tier) => tier.id === formData.policyTierId)
  const selectedVehicle = vehicles.find((vehicle) => String(vehicle.id) === String(formData.vehicle))
  const isCustomPolicy = formData.policyTierId === 'custom'
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
              policyTierId: policy.coverage?.policy_plan?.id || 'custom',
              coverage: policy.coverage || {},
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
    const nextSelectedVehicle = name === 'vehicle'
      ? vehicles.find((vehicle) => String(vehicle.id) === String(value))
      : selectedVehicle
    setQuote(null)
    if (name === 'policyTierId') {
      const tier = policyTiers.find((option) => option.id === value)
      setFormData((current) => ({
        ...current,
        policyTierId: value,
        ...(tier ? {
          type: tier.type,
          premium: String(tier.basePremium),
          deductible: String(tier.deductible),
        } : {}),
      }))
      return
    }
    setFormData((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
      ...(name === 'vehicle' && nextSelectedVehicle?.purchase_price ? {
        assetValue: String(nextSelectedVehicle.purchase_price),
        coverageLimit: String(nextSelectedVehicle.purchase_price),
      } : {}),
      ...(name === 'customer' && !isEdit ? { vehicle: '' } : {}),
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const coverage = selectedTier ? {
        ...formData.coverage,
        policy_plan: {
          id: selectedTier.id,
          name: selectedTier.name,
          category: selectedTier.category,
          coverage_sections: selectedTier.coverageSections,
          mandatory_covers: selectedTier.mandatoryCovers,
          addons: selectedTier.addons,
          base_premium_estimate_inr: selectedTier.basePremium,
          estimate_source: 'User-provided draft; not an insurer quote',
        },
      } : Object.fromEntries(Object.entries(formData.coverage || {}).filter(([key]) => key !== 'policy_plan'))

      if (!isEdit) {
        if (quote) {
          await policyService.bindPolicyQuote(quote.id)
          navigate('/policies')
          return
        }
        const selectedCustomerRecord = customers.find((customer) => String(customer.id) === String(formData.customer))
        const quoteResult = await policyService.createPolicyQuote({
          customer: canAssignCustomer ? Number(formData.customer) : Number(user.id),
          policy_type: formData.type,
          applicant_details: selectedCustomerRecord ? { name: selectedCustomerRecord.name, email: selectedCustomerRecord.email } : { name: user.name || '', email: user.email || '' },
          asset_details: {
            vehicle_id: formData.vehicle ? Number(formData.vehicle) : null,
            vehicle_description: selectedVehicle?.label || '',
            declared_value: Number(formData.assetValue),
          },
          risk_factors: { source: 'staff-entered demonstration score' },
          asset_value: Number(formData.assetValue),
          coverage_limit: Number(formData.coverageLimit),
          deductible: Number(formData.deductible),
          risk_score: Number(formData.riskScore),
          policy_terms: {
            agent: formData.agent ? Number(formData.agent) : null,
            start_date: formData.startDate,
            end_date: formData.endDate,
            payment_frequency: formData.paymentFrequency,
            auto_renew: formData.autoRenew,
            coverage,
            vehicle: formData.vehicle ? Number(formData.vehicle) : null,
            property_address: formData.propertyAddress,
            property_type: formData.propertyType,
            property_year_built: Number(formData.propertyYearBuilt) || null,
            property_square_footage: Number(formData.propertySquareFootage) || null,
          },
        })
        setQuote(quoteResult)
        setFormData((current) => ({ ...current, premium: quoteResult.quoted_premium }))
        return
      }
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
        coverage,
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
          <div className="card-header"><h2 className="card-title">Choose a Policy Tier</h2></div>
          <div className="card-content space-y-4">
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              These eight motor policy tiers and base premiums are the estimates you supplied. They are not verified insurer offers or quotes; confirm the wording and final premium with an insurer before issuing coverage.
            </p>
            <Select
              label="Policy tier"
              name="policyTierId"
              value={formData.policyTierId}
              onChange={handleChange}
              options={[
                ...policyTiers.map((tier) => ({
                  value: tier.id,
                  label: `${tier.id} · ${tier.name} · ${formatCurrency(tier.basePremium, 'INR', 'en-IN')}/yr (estimate)`,
                })),
                { value: 'custom', label: 'Other / custom policy' },
              ]}
              placeholder="Select a policy tier"
              required={!isEdit}
            />
            {selectedTier && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div><span className="font-medium text-gray-500">Category</span><p>{selectedTier.category}</p></div>
                  <div><span className="font-medium text-gray-500">Base premium estimate</span><p>{formatCurrency(selectedTier.basePremium, 'INR', 'en-IN')} per year</p></div>
                  <div><span className="font-medium text-gray-500">Coverage sections</span><p>{selectedTier.coverageSections.join('; ') || 'None listed'}</p></div>
                  <div><span className="font-medium text-gray-500">Mandatory covers</span><p>{selectedTier.mandatoryCovers.join('; ') || 'None listed'}</p></div>
                  <div><span className="font-medium text-gray-500">Compulsory deductible estimate</span><p>{formatCurrency(selectedTier.deductible, 'INR', 'en-IN')}</p></div>
                  <div><span className="font-medium text-gray-500">Available add-ons</span><p>{selectedTier.addons.join(', ') || 'None listed'}</p></div>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="card">
          <div className="card-header"><h2 className="card-title">Policy Details</h2></div>
          <div className="card-content grid grid-cols-1 gap-4 md:grid-cols-2">
            {canAssignCustomer && (
              <Select label="Customer" name="customer" value={formData.customer} onChange={handleChange} options={customerOptions} placeholder="Select customer" required />
            )}
            {canAssignCustomer && (
              <Select label="Assigned Agent" name="agent" value={formData.agent} onChange={handleChange} options={agentOptions} placeholder="Select agent (optional)" />
            )}
            {isCustomPolicy && <Select label="Policy Type" name="type" value={formData.type} onChange={handleChange} options={[
              { value: 'auto_comprehensive', label: 'Comprehensive Auto' },
              { value: 'auto_collision', label: 'Collision Auto' },
              { value: 'auto_liability', label: 'Liability Auto' },
              { value: 'homeowners', label: 'Homeowners' },
              { value: 'renters', label: 'Renters' },
              { value: 'umbrella', label: 'Umbrella' },
            ]} />}
            {isEdit && <Select label="Status" name="status" value={formData.status} onChange={handleChange} options={[
              { value: 'pending', label: 'Pending' }, { value: 'active', label: 'Active' },
              { value: 'suspended', label: 'Suspended' }, { value: 'expired', label: 'Expired' }, { value: 'cancelled', label: 'Cancelled' },
            ]} />}
            <Input label="Start Date" name="startDate" type="date" value={formData.startDate} onChange={handleChange} required />
            <Input label="End Date" name="endDate" type="date" value={formData.endDate} onChange={handleChange} required />
            <Input label={selectedTier ? 'Annual premium (INR estimate)' : 'Premium'} name="premium" type="number" min="0" step="0.01" value={formData.premium} onChange={handleChange} required />
            <Input label={selectedTier ? 'Compulsory deductible (INR estimate)' : 'Deductible'} name="deductible" type="number" min="0" step="0.01" value={formData.deductible} onChange={handleChange} required />
            {!isEdit && <>
              <Input label="Declared asset value (INR)" name="assetValue" type="number" min="0.01" step="0.01" value={formData.assetValue} onChange={handleChange} required />
              <Input label="Coverage limit (INR)" name="coverageLimit" type="number" min="0.01" step="0.01" value={formData.coverageLimit} onChange={handleChange} required />
              <Input label="Underwriting risk score (0–100)" name="riskScore" type="number" min="0" max="100" step="0.01" value={formData.riskScore} onChange={handleChange} required />
            </>}
            <Select label="Payment Frequency" name="paymentFrequency" value={formData.paymentFrequency} onChange={handleChange} options={[
              { value: 'annual', label: 'Annual' }, { value: 'semi_annual', label: 'Semi-Annual' },
              { value: 'quarterly', label: 'Quarterly' }, { value: 'monthly', label: 'Monthly' },
            ]} />
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" name="autoRenew" checked={formData.autoRenew} onChange={handleChange} className="h-4 w-4" /> Auto renew
            </label>
          </div>
        </section>

        {!isEdit && quote && <section className="card border border-blue-200 bg-blue-50 p-5">
          <h2 className="card-title">Quote ready for review</h2>
          <p className="mt-2 text-sm text-gray-700">Annual estimate: {formatCurrency(quote.quoted_premium, 'INR', 'en-IN')}</p>
          <p className="mt-1 text-sm text-gray-700">Base {formatCurrency(quote.rating_breakdown.base_premium, 'INR', 'en-IN')} + risk {formatCurrency(quote.rating_breakdown.risk_loading, 'INR', 'en-IN')} − deductible credit {formatCurrency(quote.rating_breakdown.deductible_credit, 'INR', 'en-IN')}.</p>
          <p className="mt-2 text-xs text-amber-800">This estimate uses demonstration rating factors, not approved insurer pricing. Review it before issuing.</p>
        </section>}

        {isAutoPolicy ? (
          <section className="card">
            <div className="card-header"><h2 className="card-title">Covered Vehicle</h2></div>
            <div className="card-content">
              <Select label="Vehicle belonging to this customer" name="vehicle" value={formData.vehicle} onChange={handleChange} options={vehicleOptions} placeholder={selectedCustomer ? 'Select an unassigned vehicle' : 'Choose a customer first'} required />
              {selectedCustomer && vehicleOptions.length === 0 && (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  <p>This customer has no unassigned vehicles. Add the vehicle first; a policy is not required to save it.</p>
                  <Link
                    className="mt-2 inline-flex font-semibold text-blue-800 underline hover:text-blue-950"
                    to={`/vehicles/new?customer=${encodeURIComponent(selectedCustomer)}&returnTo=policy`}
                  >
                    Add vehicle for this customer
                  </Link>
                </div>
              )}
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
          <Button asChild variant="ghost"><Link to="/policies">Cancel</Link></Button>
          <Button type="submit" disabled={loading || (canAssignCustomer && !formData.customer) || (isAutoPolicy && vehicleOptions.length === 0)}>
            <Save className="mr-2 h-4 w-4" /> {loading ? 'Saving…' : isEdit ? 'Update Policy' : quote ? 'Issue Active Policy' : 'Calculate Quote'}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default PolicyForm
