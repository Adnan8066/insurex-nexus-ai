import { useState } from 'react'
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
import { mockPolicies } from '../../data/policies'
import { mockVehicles } from '../../data/vehicles'
import { mockClaims } from '../../data/claims'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/forms/FormFields'

export function SubmitClaim() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const preselectedPolicy = searchParams.get('policy')
  const preselectedVehicle = searchParams.get('vehicle')

  const [currentStep, setCurrentStep] = useState(1)
  const [submitting, setSubmitting] = useState(false)
  const [successClaimId, setSuccessClaimId] = useState(null)

  const [formData, setFormData] = useState({
    policyId: preselectedPolicy || 'POL-2024-005678',
    vehicleId: preselectedVehicle || '1',
    incidentDate: new Date().toISOString().split('T')[0],
    incidentTime: '14:30',
    incidentType: 'Collision',
    incidentSeverity: 'Moderate',
    location: '',
    numberOfVehicles: 2,
    injuries: false,
    injuryDetails: '',
    propertyDamage: false,
    propertyDamageDetails: '',
    witnesses: false,
    witnessDetails: '',
    policeReport: true,
    policeReportNumber: '',
    claimAmount: '',
    description: '',
  })

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setSubmitting(true)

    setTimeout(() => {
      const generatedId = `CLM-2024-${Math.floor(100000 + Math.random() * 900000)}`
      const selectedPolicy = mockPolicies.find((p) => p.id === formData.policyId) || mockPolicies[0]
      const selectedVehicle = mockVehicles.find((v) => v.id.toString() === formData.vehicleId.toString()) || mockVehicles[0]

      const newClaim = {
        id: generatedId,
        claimNumber: generatedId,
        customerId: 1,
        customerName: 'John Anderson',
        policyId: selectedPolicy.id,
        policyNumber: selectedPolicy.policyNumber,
        vehicleId: selectedVehicle.id,
        vehicle: {
          make: selectedVehicle.make,
          model: selectedVehicle.model,
          year: selectedVehicle.year,
          licensePlate: selectedVehicle.licensePlate,
        },
        incidentDate: formData.incidentDate,
        incidentTime: formData.incidentTime,
        incidentType: formData.incidentType,
        incidentSeverity: formData.incidentSeverity,
        location: formData.location || 'Springfield, IL',
        numberOfVehicles: parseInt(formData.numberOfVehicles) || 1,
        injuries: formData.injuries,
        injuryDetails: formData.injuryDetails,
        propertyDamage: formData.propertyDamage,
        propertyDamageDetails: formData.propertyDamageDetails,
        witnesses: formData.witnesses,
        witnessDetails: formData.witnessDetails,
        policeReport: formData.policeReport,
        policeReportNumber: formData.policeReportNumber || 'PD-PENDING',
        claimAmount: parseFloat(formData.claimAmount) || 5000,
        status: 'submitted',
        submittedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        assignedAdjuster: 'Sarah Mitchell',
        assignedInvestigator: null,
        assignedRepairShop: null,
        documents: [],
        timeline: [
          {
            id: 1,
            status: 'submitted',
            title: 'Claim Submitted',
            description: 'New claim registered via portal',
            timestamp: new Date().toISOString(),
            user: 'John Anderson',
          },
        ],
        aiAssessment: {
          predictedRepairCost: parseFloat(formData.claimAmount) * 0.95 || 4750,
          fraudRiskScore: 18,
          totalLossProbability: formData.incidentSeverity === 'Major' ? 65 : 4,
          claimPriority: formData.incidentSeverity === 'Major' ? 'High' : 'Medium',
          aiRecommendation: 'Standard processing initiated',
          confidence: 89,
          factors: [{ factor: 'Initial intake complete', impact: 'positive', weight: 0.3 }],
        },
      }

      mockClaims.unshift(newClaim)
      setSubmitting(false)
      setSuccessClaimId(generatedId)
    }, 800)
  }

  if (successClaimId) {
    return (
      <div className="page max-w-2xl mx-auto py-12 text-center">
        <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle2 className="w-9 h-9" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Claim Successfully Filed</h1>
        <p className="text-gray-600 mb-4">
          Your claim reference is <span className="font-mono font-bold text-gray-900">{successClaimId}</span>. It has entered the automated intake queue.
        </p>
        <div className="flex justify-center gap-3">
          <Button variant="secondary" onClick={() => navigate('/claims')}>
            View All Claims
          </Button>
          <Button variant="primary" onClick={() => navigate(`/claims/${successClaimId}`)}>
            View Claim Details
          </Button>
          <Button variant="outline" onClick={() => navigate(`/claims/${successClaimId}/tracking`)}>
            Track Workflow
          </Button>
        </div>
      </div>
    )
  }

  const steps = [
    { number: 1, label: 'Policy & Vehicle' },
    { number: 2, label: 'Incident Details' },
    { number: 3, label: 'Injuries & Reports' },
    { number: 4, label: 'Amount & Evidence' },
  ]

  return (
    <div className="page max-w-4xl mx-auto">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/claims" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to claims
          </Link>
          <h1 className="page-title">Submit Insurance Claim</h1>
          <p className="page-subtitle">Complete the guided intake form to begin claim processing and AI assessment</p>
        </div>
      </div>

      {/* Stepper Header */}
      <div className="mb-8">
        <div className="grid grid-cols-4 gap-2">
          {steps.map((s) => (
            <div
              key={s.number}
              className={clsx(
                'border-t-4 pt-2 text-xs font-semibold uppercase transition-colors',
                currentStep >= s.number ? 'border-primary text-primary' : 'border-gray-200 text-gray-400'
              )}
            >
              Step {s.number}: {s.label}
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardContent className="p-6 md:p-8 space-y-6">
            {/* Step 1: Policy & Vehicle */}
            {currentStep === 1 && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900 border-b pb-2">Step 1: Select Policy & Vehicle</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Select
                    label="Associated Policy"
                    name="policyId"
                    value={formData.policyId}
                    onChange={handleChange}
                    options={mockPolicies.map((p) => ({ value: p.id, label: `${p.policyNumber} - ${p.type}` }))}
                    required
                  />
                  <Select
                    label="Insured Vehicle"
                    name="vehicleId"
                    value={formData.vehicleId}
                    onChange={handleChange}
                    options={mockVehicles.map((v) => ({
                      value: v.id.toString(),
                      label: `${v.year} ${v.make} ${v.model} (${v.licensePlate})`,
                    }))}
                    required
                  />
                </div>
                <div className="p-4 bg-blue-50/60 rounded-xl text-sm text-blue-800 flex items-start gap-3">
                  <Shield className="w-5 h-5 flex-shrink-0 text-primary mt-0.5" />
                  <div>
                    <span className="font-semibold block">Coverage Verification</span>
                    Selected policy covers Collision, Comprehensive up to \$50,000 with a \$500 deductible.
                  </div>
                </div>
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
                    options={[
                      { value: 'Collision', label: 'Collision (Vehicle vs Vehicle/Object)' },
                      { value: 'Comprehensive', label: 'Comprehensive (Hail, Weather, Animal)' },
                      { value: 'Theft', label: 'Theft / Stolen Vehicle' },
                      { value: 'Vandalism', label: 'Vandalism / Criminal Damage' },
                    ]}
                    required
                  />
                  <Select
                    label="Incident Severity"
                    name="incidentSeverity"
                    value={formData.incidentSeverity}
                    onChange={handleChange}
                    options={[
                      { value: 'Minor', label: 'Minor (Scratches, Dents, Operable)' },
                      { value: 'Moderate', label: 'Moderate (Body Damage, Radiator/Bumper)' },
                      { value: 'Major', label: 'Major (Structural, Airbags Deployed, Inoperable)' },
                    ]}
                    required
                  />
                  <Input
                    label="Incident Location (Address / Crossroads)"
                    name="location"
                    placeholder="e.g. I-95 & Exit 42, Springfield, IL"
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
                    label="Estimated Repair or Claim Amount ($)"
                    type="number"
                    min="1"
                    name="claimAmount"
                    placeholder="e.g. 7500"
                    value={formData.claimAmount}
                    onChange={handleChange}
                    required
                  />
                  <div className="p-3 bg-gray-50 rounded-xl text-xs text-gray-600 flex items-center">
                    Note: Our ML Damage Assessment model will cross-verify this estimate against damage photos and OEM parts catalogs.
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

                <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-primary transition">
                  <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="font-medium text-gray-800 text-sm">Upload Photos & Estimates (Simulated)</p>
                  <p className="text-xs text-gray-500 mt-1">PNG, JPG, PDF up to 25MB (Damage photos, police report, repair quotes)</p>
                </div>
              </div>
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
                <Button variant="primary" type="button" onClick={() => setCurrentStep((prev) => prev + 1)}>
                  Next Step
                  <ArrowRight className="w-4 h-4 ml-1.5" />
                </Button>
              ) : (
                <Button variant="primary" type="submit" loading={submitting}>
                  Submit Insurance Claim
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
