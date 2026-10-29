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

const FREQUENCY_OPTIONS = [
  { value: 'annual', label: 'Annual' },
  { value: 'semi_annual', label: 'Every 6 months' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'monthly', label: 'Monthly' },
]
const tierOptions = policyTiers.map((tier) => ({ value: tier.id, label: `${tier.name} (${tier.category})` }))
const today = () => format(new Date(), 'yyyy-MM-dd')
const oneYearFrom = (start) => format(subDays(addYears(parseISO(start), 1), 1), 'yyyy-MM-dd')

// Customer-facing request: the quote is saved for staff review and only becomes a
// policy when an employee or admin issues it from the Policy requests page.
export function RequestPolicy() {
  const { id } = useParams()
  const { user } = useAuth()
  const [vehicle, setVehicle] = useState(null)
  const [pendingRequest, setPendingRequest] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [form, setForm] = useState({ tierId: policyTiers[0].id, declaredValue: '', startDate: today(), paymentFrequency: 'annual' })
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
        setForm((current) => ({ ...current, declaredValue: vehicleRes.purchase_price ? String(Math.round(Number(vehicleRes.purchase_price))) : '' }))
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
  const declaredValue = Number(form.declaredValue)
  const vehicleName = vehicle ? `${vehicle.year} ${vehicle.make} ${vehicle.model}` : ''

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!(declaredValue > 0)) {
      setError('Enter the current value of your vehicle.')
      return
    }
    if (tier.deductible >= declaredValue) {
      setError('The vehicle value must be higher than the plan deductible.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const result = await policyService.createPolicyQuote({
        customer: Number(user.id),
        policy_type: tier.type,
        applicant_details: { name: user.name || '', email: user.email || '' },
        asset_details: { vehicle_id: vehicle.id, vehicle_description: `${vehicleName} (${vehicle.license_plate})`, declared_value: declaredValue },
        risk_factors: {},
        asset_value: declaredValue,
        coverage_limit: declaredValue,
        deductible: tier.deductible,
        risk_score: 0, // replaced server-side with the default score for customer requests
        policy_terms: {
          start_date: form.startDate,
          end_date: oneYearFrom(form.startDate),
          payment_frequency: form.paymentFrequency,
          auto_renew: true,
          vehicle: vehicle.id,
          coverage: {
            policy_plan: {
              id: tier.id,
              name: tier.name,
              category: tier.category,
              coverage_sections: tier.coverageSections,
              mandatory_covers: tier.mandatoryCovers,
              addons: tier.addons,
              base_premium_estimate_inr: tier.basePremium,
              estimate_source: 'User-provided draft; not an insurer quote',
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
    return <div className="page mx-auto max-w-3xl p-8 text-center text-sm text-gray-500">Loading vehicle…</div>
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
              <p className="text-sm text-gray-500">Quoted annual premium</p>
              <p className="text-3xl font-bold text-gray-900">{formatCurrency(Number(request.quoted_premium))}</p>
              <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
                <div><dt className="text-gray-500">Base premium</dt><dd className="font-medium">{formatCurrency(Number(breakdown.base_premium || 0))}</dd></div>
                <div><dt className="text-gray-500">Risk loading</dt><dd className="font-medium">{formatCurrency(Number(breakdown.risk_loading || 0))}</dd></div>
                <div><dt className="text-gray-500">Deductible credit</dt><dd className="font-medium">− {formatCurrency(Number(breakdown.deductible_credit || 0))}</dd></div>
              </dl>
            </div>
            <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div><dt className="text-gray-500">Plan</dt><dd className="font-medium">{request.policy_terms?.coverage?.policy_plan?.name || request.policy_type}</dd></div>
              <div><dt className="text-gray-500">Vehicle value covered</dt><dd className="font-medium">{formatCurrency(Number(request.coverage_limit))}</dd></div>
              <div><dt className="text-gray-500">Cover period</dt><dd className="font-medium">{formatDate(request.policy_terms?.start_date)} – {formatDate(request.policy_terms?.end_date)}</dd></div>
              <div><dt className="text-gray-500">Requested</dt><dd className="font-medium">{formatDate(request.created_at)}</dd></div>
            </dl>
            <p className="text-xs text-gray-500">This is an estimate from demonstration rating factors. The final premium is confirmed when the policy is issued.</p>
            <div className="flex flex-wrap gap-3">
              <Button asChild variant="primary"><Link to={`/vehicles/${vehicle.id}`}>Back to vehicle</Link></Button>
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
              {tier.addons.length > 0 && <p className="mt-2 text-blue-800">Add-ons: {tier.addons.join(', ')}</p>}
              <p className="mt-2">Deductible: {formatCurrency(tier.deductible)}</p>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input
                label="Current vehicle value (₹)"
                name="declaredValue"
                type="number"
                min="1"
                value={form.declaredValue}
                onChange={handleChange}
                hint="The amount your vehicle is insured for."
                required
              />
              <Input label="Cover starts on" name="startDate" type="date" min={today()} value={form.startDate} onChange={handleChange} required />
              <Select label="Pay premium" name="paymentFrequency" value={form.paymentFrequency} onChange={handleChange} options={FREQUENCY_OPTIONS} />
              <div className="input-group">
                <span className="input-label">Cover ends on</span>
                <p className="py-2 text-sm text-gray-700">{form.startDate ? formatDate(oneYearFrom(form.startDate)) : '—'}</p>
              </div>
            </div>
            {error && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
            <div className="flex justify-end">
              <Button type="submit" variant="primary" loading={submitting}>Get quote and send request</Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  )
}

export default RequestPolicy
