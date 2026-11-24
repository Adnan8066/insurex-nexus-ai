import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle, Clock, ShieldCheck } from 'lucide-react'
import { addYears, format, parseISO, subDays } from 'date-fns'
import { policyService, vehicleService } from '../../services'
import { formatApiError } from '../../services/api'
import { useAuth } from '../../context/useAuth'
import { policyTiers } from '../../data/policyTiers'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { Input, Select } from '../../components/forms/FormFields'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { Alert } from '../../components/ui/Alert'
import { LoadingState } from '../../components/ui/LoadingSpinner'

const FREQUENCY_OPTIONS = [
  { value: 'annual', label: 'Annual' },
  { value: 'semi_annual', label: 'Every 6 months' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'monthly', label: 'Monthly' },
]
// Add-ons that have a price in the premium rules (settings.POLICY_RATING_TABLES.addons).
const ADDON_OPTIONS = [
  { code: 'zero_depreciation', label: 'Zero depreciation' },
  { code: 'engine_protect', label: 'Engine protection' },
  { code: 'roadside_assistance', label: 'Roadside assistance' },
  { code: 'consumables', label: 'Consumables' },
  { code: 'key_protect', label: 'Key protect' },
]
const NCB_OPTIONS = [0, 1, 2, 3, 4, 5].map((years) => ({
  value: String(years),
  label: years === 0 ? 'No claim-free years' : `${years} claim-free year${years > 1 ? 's' : ''}`,
}))
const tierOptions = policyTiers.map((tier) => ({ value: tier.id, label: `${tier.name} (${tier.category})` }))
const today = () => format(new Date(), 'yyyy-MM-dd')
const oneYearFrom = (start) => format(subDays(addYears(parseISO(start), 1), 1), 'yyyy-MM-dd')

// Customer-facing request: the premium is calculated on the server from the vehicle
// record and the choices below. The quote is saved for staff review and only becomes
// a policy when an employee or admin issues it.
export function RequestPolicy() {
  const { id } = useParams()
  const { user } = useAuth()
  const [vehicle, setVehicle] = useState(null)
  const [pendingRequest, setPendingRequest] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [form, setForm] = useState({ tierId: policyTiers[0].id, ncbYears: '0', startDate: today(), paymentFrequency: 'annual' })
  const [addOns, setAddOns] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [vehicleRes, applicationsRes] = await Promise.all([
          vehicleService.getVehicle(id),
          policyService.getPolicyApplications({ status: 'quoted' }),
        ])
        if (cancelled) return
        const applications = Array.isArray(applicationsRes) ? applicationsRes : applicationsRes.results || []
        setVehicle(vehicleRes)
        setPendingRequest(applications.find((item) => String(item.policy_terms?.vehicle) === String(vehicleRes.id)) || null)
      } catch (err) {
        if (!cancelled) setLoadError(formatApiError(err, 'Could not load this vehicle.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [id])

  const tier = policyTiers.find((item) => item.id === form.tierId) || policyTiers[0]
  const includesOwnDamage = tier.type !== 'auto_liability'
  const vehicleName = vehicle ? `${vehicle.year} ${vehicle.make} ${vehicle.model}` : ''
  const missingVehicleDetails = vehicle
    ? [
        !vehicle.ex_showroom_price && 'ex-showroom price',
        !vehicle.engine_cc && 'engine capacity (cc)',
        !vehicle.registration_city && 'registration city',
      ].filter(Boolean)
    : []

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setError('')
  }

  const toggleAddOn = (code) => {
    setAddOns((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]))
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (missingVehicleDetails.length) {
      setError(`Add the ${missingVehicleDetails.join(', ')} to this vehicle before requesting a policy.`)
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const exShowroom = Number(vehicle.ex_showroom_price)
      const result = await policyService.createPolicyQuote({
        customer: Number(user.id),
        policy_type: tier.type,
        applicant_details: { name: user.name || '', email: user.email || '' },
        asset_details: { vehicle_id: vehicle.id, vehicle_description: `${vehicleName} (${vehicle.license_plate})` },
        risk_factors: {},
        // The server recalculates the insured value (IDV) and deductible from the plan and vehicle.
        asset_value: exShowroom,
        coverage_limit: exShowroom,
        deductible: tier.deductible,
        risk_score: 0,
        policy_terms: {
          start_date: form.startDate,
          end_date: oneYearFrom(form.startDate),
          payment_frequency: form.paymentFrequency,
          auto_renew: true,
          vehicle: vehicle.id,
          ncb_years: Number(form.ncbYears),
          add_ons: includesOwnDamage ? addOns : [],
          coverage: {
            policy_plan: {
              id: tier.id,
              name: tier.name,
              category: tier.category,
              coverage_sections: tier.coverageSections,
              mandatory_covers: tier.mandatoryCovers,
              addons: tier.addons,
              estimate_source: 'Estimate from the premium rules; not an insurer quote',
            },
          },
        },
      })
      setSubmitted(result)
    } catch (err) {
      setError(formatApiError(err, 'Could not send your policy request.'))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="page mx-auto max-w-3xl"><LoadingState label="Loading vehicle…" /></div>
  }
  if (loadError || !vehicle) {
    return (
      <div className="page mx-auto max-w-3xl">
        <EmptyState title="Vehicle not available" description={loadError || 'This vehicle could not be found.'} />
      </div>
    )
  }

  const backLink = (
    <Link to={`/vehicles/${vehicle.id}`} className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900">
      <ArrowLeft className="h-4 w-4" /> Back to vehicle
    </Link>
  )

  if (vehicle.policy) {
    return (
      <div className="page mx-auto max-w-3xl space-y-6">
        {backLink}
        <EmptyState title="This vehicle is already insured" description={`${vehicleName} is covered by policy ${vehicle.policy_number || ''}.`} />
      </div>
    )
  }

  const request = submitted || pendingRequest
  if (request) {
    const breakdown = request.rating_breakdown || {}
    const lines = breakdown.lines || []
    return (
      <div className="page mx-auto max-w-3xl space-y-6">
        {backLink}
        <Card>
          <CardContent className="space-y-5 p-6">
            <div className="flex items-start gap-3">
              {submitted ? <CheckCircle className="mt-0.5 h-6 w-6 text-green-600" /> : <Clock className="mt-0.5 h-6 w-6 text-amber-500" />}
              <div>
                <h1 className="text-xl font-bold text-gray-900">{submitted ? 'Policy request sent' : 'Policy request waiting for review'}</h1>
                <p className="mt-1 text-sm text-gray-600">
                  Our team will review your request for the {vehicleName}. You will get a notification when your policy is issued.
                </p>
              </div>
            </div>
            <div className="rounded-xl bg-gray-50 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm text-gray-500">Quoted annual premium (incl. GST)</p>
                {breakdown.tariff_source === 'INDICATIVE_DEMO_TARIFF' && (
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">Indicative / Demo Tariff</span>
                )}
              </div>
              <p className="text-3xl font-bold text-gray-900">{formatCurrency(Number(request.quoted_premium))}</p>
              <dl className="mt-4 divide-y divide-gray-200 text-sm">
                {lines.map((line) => (
                  <div key={line.label} className="flex justify-between gap-4 py-2">
                    <dt className="text-gray-600">{line.label}</dt>
                    <dd className="font-medium text-gray-900">{formatCurrency(Number(line.amount))}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div><dt className="text-gray-500">Plan</dt><dd className="font-medium">{request.policy_terms?.coverage?.policy_plan?.name || request.policy_type}</dd></div>
              <div><dt className="text-gray-500">Insured value (IDV)</dt><dd className="font-medium">{formatCurrency(Number(request.coverage_limit))}</dd></div>
              {breakdown.depreciation_percent && (
                <div><dt className="text-gray-500">Depreciation for age</dt><dd className="font-medium">{Number(breakdown.depreciation_percent).toFixed(0)}% ({breakdown.vehicle_age_years} yr)</dd></div>
              )}
              {breakdown.zone && (
                <div><dt className="text-gray-500">Zone</dt><dd className="font-medium">{breakdown.zone === 'A' ? 'Zone A (metro)' : 'Zone B'}</dd></div>
              )}
              <div><dt className="text-gray-500">Deductible</dt><dd className="font-medium">{formatCurrency(Number(request.deductible))}</dd></div>
              <div><dt className="text-gray-500">Cover period</dt><dd className="font-medium">{formatDate(request.policy_terms?.start_date)} – {formatDate(request.policy_terms?.end_date)}</dd></div>
              <div><dt className="text-gray-500">Requested</dt><dd className="font-medium">{formatDate(request.created_at)}</dd></div>
            </dl>
            <p className="text-xs text-gray-500">This is an estimate from the premium rules. The final premium is confirmed when the policy is issued.</p>
            <div className="flex flex-wrap gap-3">
              <Button asChild variant="primary"><Link to={`/vehicles/${vehicle.id}`}>Back to vehicle</Link></Button>
              <Button asChild variant="outline"><Link to="/my-policy-requests">Track my requests</Link></Button>
              <Button asChild variant="outline"><Link to="/dashboard">Go to dashboard</Link></Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="page mx-auto max-w-3xl space-y-6">
      {backLink}
      <div className="page-header">
        <h1 className="page-title">Insure your vehicle</h1>
        <p className="page-subtitle">Choose a plan for your {vehicleName} ({vehicle.license_plate}). Our team reviews every request before the policy is issued.</p>
      </div>

      {missingVehicleDetails.length > 0 && (
        <Alert>
          This vehicle is missing {missingVehicleDetails.join(', ')}. Add it on the vehicle record before requesting a policy.
        </Alert>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <Card>
          <CardHeader title="Plan and cover" />
          <CardContent className="space-y-5 p-6">
            <Select label="Plan" name="tierId" value={form.tierId} onChange={handleChange} options={tierOptions} />
            <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4 text-sm text-blue-900">
              <p className="flex items-center gap-2 font-semibold"><ShieldCheck className="h-4 w-4" /> What this plan covers</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {[...tier.coverageSections, ...tier.mandatoryCovers].map((item) => <li key={item}>{item}</li>)}
              </ul>
              <p className="mt-2">Deductible: {formatCurrency(tier.deductible)}</p>
            </div>

            {includesOwnDamage && (
              <fieldset className="space-y-2">
                <legend className="input-label">Add-ons (optional)</legend>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {ADDON_OPTIONS.map((option) => (
                    <label key={option.code} className="flex items-center gap-2 text-sm text-gray-700">
                      <input type="checkbox" checked={addOns.includes(option.code)} onChange={() => toggleAddOn(option.code)} />
                      {option.label}
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {includesOwnDamage && (
                <Select
                  label="No-claim bonus (claim-free years)"
                  name="ncbYears"
                  value={form.ncbYears}
                  onChange={handleChange}
                  options={NCB_OPTIONS}
                  hint="Years in a row with no claim on your previous policy. It discounts the own-damage part only."
                />
              )}
              <Input label="Cover starts on" name="startDate" type="date" min={today()} value={form.startDate} onChange={handleChange} required />
              <Select label="Pay premium" name="paymentFrequency" value={form.paymentFrequency} onChange={handleChange} options={FREQUENCY_OPTIONS} />
              <div className="input-group">
                <span className="input-label">Cover ends on</span>
                <p className="py-2 text-sm text-gray-700">{form.startDate ? formatDate(oneYearFrom(form.startDate)) : '—'}</p>
              </div>
            </div>
            {error && <Alert>{error}</Alert>}
            <div className="flex justify-end">
              <Button type="submit" variant="primary" loading={submitting} disabled={missingVehicleDetails.length > 0}>
                Get quote and send request
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  )
}

export default RequestPolicy
