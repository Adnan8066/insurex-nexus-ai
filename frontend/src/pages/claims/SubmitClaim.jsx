import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  FileText,
  Car,
  Calendar,
  DollarSign,
  AlertTriangle,
  Upload,
  CheckCircle2,
  ArrowLeft,
  ArrowRight,
  Shield,
  MapPin,
  Clock,
} from 'lucide-react'
import { clsx } from 'clsx'
import { claimService } from '../../services/claimService'
import { policyService } from '../../services/policyService'
import { vehicleService } from '../../services/vehicleService'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/forms/FormFields'
import { INCIDENT_SEVERITIES, INCIDENT_TYPES, POLICY_TYPES, labelFor } from '../../constants/domain'
import { formatCurrency, formatDate } from '../../utils/helpers'

const incidentTypeOptions = INCIDENT_TYPES.map(({ value, label, hint }) => ({ value, label: `${label} - ${hint}` }))
const severityOptions = INCIDENT_SEVERITIES.map(({ value, label, hint }) => ({ value, label: `${label} - ${hint}` }))

// Local dates/times (toISOString would give the UTC date, which is yesterday early in the morning in India).
const pad = (n) => String(n).padStart(2, '0')
const localToday = () => {
  const now = new Date()
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
const localNowTime = () => {
  const now = new Date()
  return `${pad(now.getHours())}:${pad(now.getMinutes())}`
}

const FIELD_LABELS = {
  policy: 'Policy',
  vehicle: 'Vehicle',
  incident_date: 'Incident date',
  incident_time: 'Incident time',
  incident_type: 'Incident type',
  incident_severity: 'Severity',
  location: 'Location',
  number_of_vehicles: 'Vehicles involved',
  claim_amount: 'Claim amount',
  description: 'Description',
}

// Turn a DRF error response into one readable sentence.
function describeSubmitError(err) {
  if (!err.response) return 'Could not reach the claims service. Check your connection and try again.'
  const data = err.response.data
  if (typeof data?.detail === 'string' && data.detail) return data.detail
  const fieldErrors = data?.error?.details || data?.errors || data
  if (fieldErrors && typeof fieldErrors === 'object') {
    const messages = Object.entries(fieldErrors)
      .filter(([field]) => !['success', 'error', 'detail', 'status_code'].includes(field))
      .flatMap(([field, msgs]) => (Array.isArray(msgs) ? msgs : [msgs])
        .filter((msg) => typeof msg === 'string')
        .map((msg) => `${FIELD_LABELS[field] || field.replace(/_/g, ' ')}: ${msg}`))
    if (messages.length) return messages.join(' ')
  }
  if (typeof data?.error?.message === 'string') return data.error.message
  return 'We could not submit your claim. Please check the details and try again.'
}

export function SubmitClaim() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const canSelectCustomer = ['admin', 'employee'].includes(user?.role)
  const [searchParams] = useSearchParams()
  const preselectedPolicy = searchParams.get('policy')
  const preselectedVehicle = searchParams.get('vehicle')

  const steps = [
    { number: 1, label: 'Policy & vehicle' },
    { number: 2, label: 'What happened' },
    { number: 3, label: 'Injuries & reports' },
    { number: 4, label: 'Amount, photos & review' },
  ]
  const [currentStep, setCurrentStep] = useState(1)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [uploadWarning, setUploadWarning] = useState('')
  const [attachments, setAttachments] = useState([])
  const [attachmentType, setAttachmentType] = useState('photos')
  const [attachmentError, setAttachmentError] = useState('')
  const [successClaim, setSuccessClaim] = useState(null)
  const [policies, setPolicies] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [customers, setCustomers] = useState([])

  const [formData, setFormData] = useState({
    policyId: preselectedPolicy || '',
    vehicleId: preselectedVehicle || '',
    customerId: canSelectCustomer ? '' : String(user?.id || ''),
    incidentDate: localToday(),
    incidentTime: localNowTime(),
    incidentType: 'collision',
    incidentSeverity: 'moderate',
    location: '',
    numberOfVehicles: 1,
    injuries: false,
    injuryDetails: '',
    propertyDamage: false,
    propertyDamageDetails: '',
    witnesses: false,
    witnessDetails: '',
    policeReport: false,
    policeReportNumber: '',
    claimAmount: '',
    description: '',
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [polRes, vehRes, formOptions] = await Promise.all([
          policyService.getPolicies(),
          vehicleService.getVehicles(),
          canSelectCustomer ? policyService.getPolicyFormOptions() : Promise.resolve({ customers: [] }),
        ])
        const pols = Array.isArray(polRes) ? polRes : (polRes.results || [])
        const vehs = Array.isArray(vehRes) ? vehRes : (vehRes.results || [])
        setPolicies(pols)
        setVehicles(vehs)
        setCustomers(formOptions.customers || [])
        const requestedPolicy = preselectedPolicy && pols.some((policy) => String(policy.id) === String(preselectedPolicy))
          ? String(preselectedPolicy)
          : ''
        const requestedPolicyData = pols.find((policy) => String(policy.id) === requestedPolicy)
        const requestedVehicle = preselectedVehicle && vehs.find((vehicle) => String(vehicle.id) === String(preselectedVehicle))
        const initialCustomer = canSelectCustomer
          ? String(requestedPolicyData?.customer || requestedVehicle?.customer || '')
          : String(user?.id || '')
        const initialPolicies = pols.filter((policy) => String(policy.customer) === initialCustomer)
        const initialVehicles = vehs.filter((vehicle) => String(vehicle.customer) === initialCustomer)
        const defaultVehicle = (requestedVehicle && String(requestedVehicle.customer) === initialCustomer && (!requestedPolicy || !requestedVehicle.policy || String(requestedVehicle.policy) === requestedPolicy)
          ? requestedVehicle
          : null)
          || initialVehicles.find((vehicle) => !requestedPolicy || !vehicle.policy || String(vehicle.policy) === requestedPolicy)
        const selectedPolicy = requestedPolicy
          || (defaultVehicle?.policy ? String(defaultVehicle.policy) : String(initialPolicies[0]?.id || ''))
        setFormData((prev) => ({
          ...prev,
          customerId: initialCustomer,
          policyId: requestedPolicy || selectedPolicy || prev.policyId,
          vehicleId: defaultVehicle ? String(defaultVehicle.id) : '',
        }))
      } catch (err) {
        setError('Failed to load your policies and vehicles. Please add a policy and vehicle first.')
      }
    }
    fetchData()
  }, [preselectedPolicy, preselectedVehicle, canSelectCustomer, user?.id])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setError('')
    if (name === 'vehicleId') {
      const selectedVehicle = customerVehicles.find((vehicle) => String(vehicle.id) === String(value))
      setFormData((prev) => ({
        ...prev,
        vehicleId: value,
        ...(selectedVehicle?.policy ? { policyId: String(selectedVehicle.policy) } : {}),
      }))
      return
    }
    if (name === 'customerId') {
      const customerPolicies = policies.filter((policy) => String(policy.customer) === String(value))
      const customerVehicles = vehicles.filter((vehicle) => String(vehicle.customer) === String(value))
      const firstPolicy = customerPolicies[0]
      const firstVehicle = customerVehicles.find((vehicle) => !firstPolicy || !vehicle.policy || String(vehicle.policy) === String(firstPolicy.id))
      setFormData((prev) => ({
        ...prev,
        customerId: value,
        policyId: firstPolicy ? String(firstPolicy.id) : '',
        vehicleId: firstVehicle ? String(firstVehicle.id) : '',
      }))
      return
    }
    if (name === 'policyId') {
      const selectedVehicle = customerVehicles.find((vehicle) => String(vehicle.id) === String(formData.vehicleId))
      const selectedPolicyId = value
      const compatibleVehicle = selectedVehicle?.policy && String(selectedVehicle.policy) !== selectedPolicyId
        ? customerVehicles.find((vehicle) => !vehicle.policy || String(vehicle.policy) === selectedPolicyId)
        : selectedVehicle
      setFormData((prev) => ({
        ...prev,
        policyId: value,
        ...(compatibleVehicle ? { vehicleId: String(compatibleVehicle.id) } : { vehicleId: '' }),
      }))
      return
    }
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const buildPayload = () => ({
    policy: Number(formData.policyId),
    vehicle: Number(formData.vehicleId),
    incident_date: formData.incidentDate,
    incident_time: formData.incidentTime,
    incident_type: formData.incidentType,
    incident_severity: formData.incidentSeverity,
    location: formData.location,
    number_of_vehicles: Number(formData.numberOfVehicles) || 1,
    injuries: formData.injuries,
    injury_details: formData.injuryDetails,
    property_damage: formData.propertyDamage,
    property_damage_details: formData.propertyDamageDetails,
    witnesses: formData.witnesses,
    witness_details: formData.witnessDetails,
    police_report: formData.policeReport,
    police_report_number: formData.policeReportNumber,
    claim_amount: Number(formData.claimAmount),
    estimated_repair_cost: Number(formData.claimAmount),
    description: formData.description,
  })

  const validateCurrentStep = () => {
    let message = ''
    if (currentStep === 1) {
      if (policies.length === 0) {
        message = 'You need a policy on your account before you can submit a claim. Contact your insurer if you believe a policy is missing.'
      } else if (!formData.policyId) {
        message = 'Select the policy covering this incident.'
      } else if (!formData.vehicleId) {
        message = 'Select an insured vehicle, or add it to your account first.'
      }
    } else if (currentStep === 2) {
      if (!formData.incidentDate || !formData.incidentTime || !formData.location.trim()) {
        message = 'Enter the incident date, time, and location to continue.'
      } else if (formData.incidentDate > localToday()) {
        message = 'The incident date cannot be in the future.'
      } else if (Number(formData.numberOfVehicles) < 1) {
        message = 'Enter at least one vehicle involved in the incident.'
      }
    } else if (currentStep === 4) {
      if (!(Number(formData.claimAmount) > 0) || !formData.description.trim()) {
        message = 'Enter a claim amount greater than zero and describe what happened.'
      }
    }

    setError(message)
    return !message
  }

  const handleNextStep = () => {
    if (!validateCurrentStep()) return
    setCurrentStep((step) => step + 1)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    // Pressing Enter on an earlier step moves forward instead of submitting an unfinished claim.
    if (currentStep < steps.length) {
      handleNextStep()
      return
    }
    if (!validateCurrentStep()) return
    setSubmitting(true)
    setError('')

    try {
      const payload = buildPayload()
      const response = await claimService.createClaim(payload)
      if (attachments.length > 0) {
        const uploads = await Promise.allSettled(attachments.map(({ file, documentType }) => {
          const uploadData = new FormData()
          uploadData.append('file', file)
          uploadData.append('document_type', documentType)
          uploadData.append('original_name', file.name)
          uploadData.append('description', '')
          return claimService.uploadClaimDocument(response.id, uploadData)
        }))
        const failedFiles = uploads.flatMap((upload, index) => upload.status === 'rejected' ? [attachments[index].file.name] : [])
        if (failedFiles.length > 0) {
          setUploadWarning(`Your claim was submitted, but these files could not be uploaded: ${failedFiles.join(', ')}. Open the claim to retry.`)
        }
      }
      setSuccessClaim(response)
    } catch (err) {
      setError(describeSubmitError(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (successClaim) {
    return (
      <div className="page max-w-2xl mx-auto py-12 text-center">
        <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle2 className="w-9 h-9" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Your claim has been submitted</h1>
        <p className="text-gray-600 mb-2">
          Your claim number is <span className="font-mono font-bold text-gray-900">{successClaim.claim_number || successClaim.id}</span>. Keep it for your records.
        </p>
        <p className="text-gray-600 mb-4">A claims specialist will review it, and you&apos;ll get a notification each time it moves forward.</p>
        {uploadWarning && <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800" role="alert">{uploadWarning}</p>}
        <div className="flex flex-wrap justify-center gap-3">
          <Button variant="primary" onClick={() => navigate(`/claims/${successClaim.id}/tracking`)}>
            Track this claim
          </Button>
          <Button variant="secondary" onClick={() => navigate(`/claims/${successClaim.id}`)}>
            View claim details
          </Button>
          <Button variant="ghost" onClick={() => navigate('/claims')}>
            All my claims
          </Button>
        </div>
      </div>
    )
  }

  const customerPolicies = canSelectCustomer
    ? policies.filter((policy) => String(policy.customer) === String(formData.customerId))
    : policies
  const customerVehicles = canSelectCustomer
    ? vehicles.filter((vehicle) => String(vehicle.customer) === String(formData.customerId))
    : vehicles
  const selectedPolicy = policies.find((policy) => String(policy.id) === String(formData.policyId))
  const selectedVehicle = vehicles.find((vehicle) => String(vehicle.id) === String(formData.vehicleId))

  return (
    <div className="page max-w-4xl mx-auto">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/claims" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to claims
          </Link>
          <h1 className="page-title">File a claim</h1>
          <p className="page-subtitle">Four short steps. It takes about 5 minutes, and you can add more documents later.</p>
        </div>
      </div>

      {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</div>}

      {/* Stepper Header */}
      <div className="mb-8">
        <p className="mb-2 text-sm font-semibold text-primary sm:hidden">
          Step {currentStep} of {steps.length}: {steps[currentStep - 1].label}
        </p>
        <ol className="grid grid-cols-4 gap-2" aria-label="Claim form steps">
          {steps.map((s) => (
            <li
              key={s.number}
              aria-current={currentStep === s.number ? 'step' : undefined}
              className={clsx(
                'border-t-4 pt-2 text-xs font-semibold transition-colors',
                currentStep >= s.number ? 'border-primary text-primary' : 'border-gray-200 text-gray-400'
              )}
            >
              <span className="hidden sm:inline">{s.number}. {s.label}</span>
              <span className="sr-only sm:hidden">Step {s.number}: {s.label}</span>
            </li>
          ))}
        </ol>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardContent className="p-6 md:p-8 space-y-6">
            {/* Step 1: Policy & Vehicle */}
            {currentStep === 1 && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900 border-b pb-2">Step 1: Select Policy & Vehicle</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {canSelectCustomer && <Select
                    label="Customer who owns this claim"
                    name="customerId"
                    value={formData.customerId}
                    onChange={handleChange}
                    options={customers.map((customer) => ({ value: String(customer.id), label: `${customer.name} (${customer.email})` }))}
                    placeholder="Select a customer"
                    required
                  />}
                  <Select
                    label="Associated Policy"
                    name="policyId"
                    value={formData.policyId}
                    onChange={handleChange}
                    options={customerPolicies.map((p) => ({
                      value: String(p.id),
                      label: `${p.policy_number} - ${labelFor(POLICY_TYPES, p.type)}`,
                    }))}
                    placeholder="Select a policy"
                    required
                  />
                  <Select
                    label="Insured Vehicle"
                    name="vehicleId"
                    value={formData.vehicleId}
                    onChange={handleChange}
                    options={customerVehicles.map((v) => ({
                      value: String(v.id),
                      label: `${v.year} ${v.make} ${v.model} (${v.license_plate})`,
                    }))}
                    placeholder="Select a vehicle"
                    required
                  />
                </div>
                {vehicles.length === 0 && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                    <p className="font-medium">No vehicle is linked to your account yet.</p>
                    <Link to="/vehicles/new" className="mt-2 inline-flex font-semibold text-primary hover:underline">Add a vehicle</Link>
                  </div>
                )}
                {policies.length === 0 && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                    <p>A policy is required to submit a claim.</p>
                    {user?.role === 'customer' && vehicles.length > 0 && (
                      <Link to={`/vehicles/${formData.vehicleId || vehicles[0].id}/insure`} className="mt-2 inline-flex font-semibold text-primary hover:underline">Insure your vehicle</Link>
                    )}
                  </div>
                )}
                {selectedPolicy && (
                  <div className={clsx(
                    'p-4 rounded-xl text-sm flex items-start gap-3',
                    selectedPolicy.status === 'active' ? 'bg-blue-50/60 text-blue-900' : 'bg-amber-50 text-amber-900'
                  )}
                  >
                    <Shield className="w-5 h-5 flex-shrink-0 text-primary mt-0.5" aria-hidden="true" />
                    <div>
                      <span className="font-semibold block">
                        {selectedPolicy.policy_number} · {labelFor(POLICY_TYPES, selectedPolicy.type)}
                      </span>
                      Valid {formatDate(selectedPolicy.start_date)} to {formatDate(selectedPolicy.end_date)} · Deductible {formatCurrency(selectedPolicy.deductible)}
                      {selectedPolicy.status !== 'active' && (
                        <span className="mt-1 block font-medium">This policy is {selectedPolicy.status}. Claims are normally only paid on active policies.</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Incident Details */}
            {currentStep === 2 && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900 border-b pb-2">Step 2: Incident Specifics</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Incident Date"
                    type="date"
                    max={localToday()}
                    name="incidentDate"
                    value={formData.incidentDate}
                    onChange={handleChange}
                    required
                  />
                  <Input
                    label="Incident Time"
                    type="time"
                    name="incidentTime"
                    value={formData.incidentTime}
                    onChange={handleChange}
                    required
                  />
                  <Select
                    label="Incident Type"
                    name="incidentType"
                    value={formData.incidentType}
                    onChange={handleChange}
                    options={incidentTypeOptions}
                    required
                  />
                  <Select
                    label="Incident Severity"
                    name="incidentSeverity"
                    value={formData.incidentSeverity}
                    onChange={handleChange}
                    options={severityOptions}
                    required
                  />
                  <Input
                    label="Incident Location (Address / Crossroads)"
                    name="location"
                    placeholder="e.g. MG Road near Trinity Metro, Bengaluru"
                    value={formData.location}
                    onChange={handleChange}
                    required
                    className="md:col-span-2"
                  />
                  <Input
                    label="Total Vehicles Involved"
                    type="number"
                    min="1"
                    name="numberOfVehicles"
                    value={formData.numberOfVehicles}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
            )}

            {/* Step 3: Injuries & Reports */}
            {currentStep === 3 && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900 border-b pb-2">Step 3: Injuries, Damage & Reports</h2>

                {/* Injuries */}
                <div className="p-4 rounded-xl border border-gray-200 space-y-3">
                  <label className="flex items-center gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      name="injuries"
                      checked={formData.injuries}
                      onChange={handleChange}
                      className="w-4 h-4 text-primary rounded"
                    />
                    <span className="font-semibold text-gray-900 text-sm">Were there any bodily injuries?</span>
                  </label>
                  {formData.injuries && (
                    <Textarea
                      label="Injury Details"
                      name="injuryDetails"
                      placeholder="Specify injuries sustained by driver, passengers, or pedestrians..."
                      value={formData.injuryDetails}
                      onChange={handleChange}
                    />
                  )}
                </div>

                {/* Property Damage */}
                <div className="p-4 rounded-xl border border-gray-200 space-y-3">
                  <label className="flex items-center gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      name="propertyDamage"
                      checked={formData.propertyDamage}
                      onChange={handleChange}
                      className="w-4 h-4 text-primary rounded"
                    />
                    <span className="font-semibold text-gray-900 text-sm">Damage to third-party property or city infrastructure?</span>
                  </label>
                  {formData.propertyDamage && (
                    <Textarea
                      label="Property Damage Details"
                      name="propertyDamageDetails"
                      placeholder="e.g. Guardrail, fence, signs, or other vehicles..."
                      value={formData.propertyDamageDetails}
                      onChange={handleChange}
                    />
                  )}
                </div>

                {/* Police Report */}
                <div className="p-4 rounded-xl border border-gray-200 space-y-3">
                  <label className="flex items-center gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      name="policeReport"
                      checked={formData.policeReport}
                      onChange={handleChange}
                      className="w-4 h-4 text-primary rounded"
                    />
                    <span className="font-semibold text-gray-900 text-sm">Was a Police Report filed at the scene?</span>
                  </label>
                  {formData.policeReport && (
                    <Input
                      label="Police Report Number"
                      name="policeReportNumber"
                      placeholder="e.g. PD-2024-004521"
                      value={formData.policeReportNumber}
                      onChange={handleChange}
                    />
                  )}
                </div>

                {/* Witnesses */}
                <div className="p-4 rounded-xl border border-gray-200 space-y-3">
                  <label className="flex items-center gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      name="witnesses"
                      checked={formData.witnesses}
                      onChange={handleChange}
                      className="w-4 h-4 text-primary rounded"
                    />
                    <span className="font-semibold text-gray-900 text-sm">Are there eyewitness statements or dashcam records?</span>
                  </label>
                  {formData.witnesses && (
                    <Input
                      label="Witness Information / Contacts"
                      name="witnessDetails"
                      placeholder="Names and phone numbers of witnesses..."
                      value={formData.witnessDetails}
                      onChange={handleChange}
                    />
                  )}
                </div>
              </div>
            )}

            {/* Step 4: Amount & Review */}
            {currentStep === 4 && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900 border-b pb-2">Step 4: Claim Amount & Verification</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Estimated Repair or Claim Amount (₹)"
                    type="number"
                    min="1"
                    name="claimAmount"
                    placeholder="e.g. 7500"
                    value={formData.claimAmount}
                    onChange={handleChange}
                    required
                  />
                  <div className="p-3 bg-gray-50 rounded-xl text-xs text-gray-600 flex items-center">
                    Your best estimate is fine. We&apos;ll compare it with your photos and any repair quote before deciding.
                  </div>
                </div>

                <Textarea
                  label="Accident Description / Narrative"
                  name="description"
                  rows={4}
                  placeholder="Provide a clear factual account of how the accident occurred..."
                  value={formData.description}
                  onChange={handleChange}
                  required
                />

                <div className="border-2 border-dashed border-gray-300 rounded-xl p-5 hover:border-primary transition">
                  <div className="flex items-center gap-3 mb-3">
                    <Upload className="w-6 h-6 text-primary" aria-hidden="true" />
                    <div>
                      <p className="font-medium text-gray-800 text-sm">Attach supporting documents</p>
                      <p className="text-xs text-gray-500">PNG, JPG, or PDF up to 25 MB per file</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Select
                      label="Document type"
                      name="attachmentType"
                      value={attachmentType}
                      onChange={(event) => setAttachmentType(event.target.value)}
                      options={[
                        { value: 'photos', label: 'Damage photos' },
                        { value: 'estimate', label: 'Repair estimate' },
                        { value: 'police_report', label: 'Police report' },
                        { value: 'medical', label: 'Medical records' },
                        { value: 'other', label: 'Other document' },
                      ]}
                    />
                    <div>
                      <label htmlFor="claim-attachments" className="mb-1 block text-sm font-medium text-gray-700">Choose files</label>
                      <input
                        id="claim-attachments"
                        type="file"
                        accept="image/png,image/jpeg,application/pdf"
                        multiple
                        className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:font-medium file:text-blue-700 hover:file:bg-blue-100"
                        onChange={(event) => {
                          const selectedFiles = Array.from(event.target.files || [])
                          const oversized = selectedFiles.some((file) => file.size > 25 * 1024 * 1024)
                          if (oversized) {
                            setAttachmentError('Each file must be 25 MB or smaller.')
                          } else {
                            setAttachmentError('')
                            setAttachments((current) => [
                              ...current,
                              ...selectedFiles.map((file) => ({ file, documentType: attachmentType })),
                            ])
                          }
                          event.target.value = ''
                        }}
                      />
                    </div>
                  </div>
                  {attachmentError && <p className="mt-2 text-sm text-red-600" role="alert">{attachmentError}</p>}
                  {attachments.length > 0 && (
                    <ul className="mt-4 space-y-2">
                      {attachments.map(({ file, documentType }, index) => (
                        <li key={`${file.name}-${file.lastModified}-${index}`} className="flex items-center justify-between gap-3 rounded-lg bg-white px-3 py-2 text-sm">
                          <span className="min-w-0 truncate text-gray-700">{file.name} <span className="text-gray-400">({(file.size / (1024 * 1024)).toFixed(1)} MB · {documentType.replace(/_/g, ' ')})</span></span>
                          <button type="button" className="shrink-0 text-red-600 hover:text-red-700" onClick={() => setAttachments((current) => current.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove ${file.name}`}>Remove</button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}

            {currentStep === 4 && (
              <section className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm" aria-label="Review your claim">
                <h3 className="font-semibold text-gray-900">Check your details</h3>
                <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
                  <div><dt className="text-gray-500">Vehicle</dt><dd className="font-medium text-gray-900">{selectedVehicle ? `${selectedVehicle.year} ${selectedVehicle.make} ${selectedVehicle.model} (${selectedVehicle.license_plate})` : '—'}</dd></div>
                  <div><dt className="text-gray-500">Policy</dt><dd className="font-medium text-gray-900">{selectedPolicy?.policy_number || '—'}</dd></div>
                  <div><dt className="text-gray-500">When</dt><dd className="font-medium text-gray-900">{formatDate(formData.incidentDate)} at {formData.incidentTime}</dd></div>
                  <div><dt className="text-gray-500">Where</dt><dd className="font-medium text-gray-900">{formData.location || '—'}</dd></div>
                  <div><dt className="text-gray-500">What happened</dt><dd className="font-medium text-gray-900">{labelFor(INCIDENT_TYPES, formData.incidentType)} · {labelFor(INCIDENT_SEVERITIES, formData.incidentSeverity)}</dd></div>
                  <div><dt className="text-gray-500">Documents</dt><dd className="font-medium text-gray-900">{attachments.length ? `${attachments.length} file${attachments.length === 1 ? '' : 's'} attached` : 'None yet (you can add them later)'}</dd></div>
                </dl>
                <p className="mt-3 text-xs text-gray-500">Need to change something? Use Previous to go back; your answers are kept.</p>
              </section>
            )}

            {/* Stepper Navigation Buttons */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-200">
              {currentStep > 1 ? (
                <Button variant="secondary" type="button" onClick={() => setCurrentStep((prev) => prev - 1)}>
                  <ArrowLeft className="w-4 h-4 mr-1.5" />
                  Previous
                </Button>
              ) : (
                <div></div>
              )}

              {currentStep < 4 ? (
                <Button variant="primary" type="button" onClick={handleNextStep}>
                  Next
                  <ArrowRight className="w-4 h-4 ml-1.5" />
                </Button>
              ) : (
                <Button variant="primary" type="submit" loading={submitting} disabled={submitting}>
                  {submitting ? 'Submitting…' : 'Submit claim'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  )
}

export default SubmitClaim
