import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Briefcase,
  ArrowLeft,
  Calendar,
  Clock,
  Car,
  FileText,
  MapPin,
  AlertTriangle,
  Shield,
  Brain,
  Download,
  Upload,
  Activity,
  ChevronRight,
  UserCheck,
  Trash2,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { claimService } from '../../services'
import { policyService } from '../../services/policyService'
import { useAuth } from '../../context/useAuth'
import { claimStatusWorkflow } from '../../data/claims'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { ConfirmDialog } from '../../components/ui/Modal'
import { Select } from '../../components/forms/FormFields'

const mapClaim = (c) => ({
  id: c.id,
  claimNumber: c.claim_number,
  customer: c.customer,
  customerName: c.customer_name,
  customerEmail: c.customer_email,
  policyId: c.policy,
  policyNumber: c.policy_number,
  vehicle: c.vehicle_info ? {
    id: c.vehicle_info.id,
    year: c.vehicle_info.year,
    make: c.vehicle_info.make,
    model: c.vehicle_info.model,
    licensePlate: c.vehicle_info.license_plate,
    vin: c.vehicle_info.vin,
  } : null,
  incidentDate: c.incident_date,
  incidentTime: c.incident_time,
  incidentType: c.incident_type,
  incidentSeverity: c.incident_severity,
  location: c.location,
  latitude: c.latitude,
  longitude: c.longitude,
  numberOfVehicles: c.number_of_vehicles,
  injuries: c.injuries,
  injuryDetails: c.injury_details,
  propertyDamage: c.property_damage,
  propertyDamageDetails: c.property_damage_details,
  witnesses: c.witnesses,
  witnessDetails: c.witness_details,
  policeReport: c.police_report,
  policeReportNumber: c.police_report_number,
  claimAmount: c.claim_amount,
  description: c.description,
  status: c.status,
  priority: c.priority,
  assignedAdjuster: c.assigned_adjuster_name,
  assignedAdjusterId: c.assigned_adjuster,
  assignedInvestigator: c.assigned_investigator_name,
  assignedInvestigatorId: c.assigned_investigator,
  aiAssessment: c.ai_assessment ? {
    ...c.ai_assessment,
    predictedRepairCost: c.ai_assessment.predicted_repair_cost,
    fraudRiskScore: c.ai_assessment.fraud_risk_score,
    totalLossProbability: c.ai_assessment.total_loss_probability,
    claimPriority: c.ai_assessment.claim_priority || c.ai_assessment.priority,
    aiRecommendation: c.ai_assessment.ai_recommendation,
    confidence: c.ai_assessment.confidence,
    factors: c.ai_assessment.contributing_factors || [],
  } : null,
  fraudRiskScore: c.fraud_risk_score,
  totalLossProbability: c.total_loss_probability,
  submittedAt: c.submitted_at,
  updatedAt: c.updated_at,
  closedAt: c.closed_at,
  documents: (c.documents || []).map((d) => ({
    id: d.id,
    name: d.original_name,
    type: d.document_type,
    description: d.description,
    file: d.file,
    uploadedAt: d.uploaded_at,
    uploadedByName: d.uploaded_by_name,
    verified: d.verified,
  })),
  timeline: (c.timeline || []).map((t) => ({
    id: t.id,
    status: t.status,
    title: t.title,
    description: t.description,
    user: t.user_name || t.user,
    timestamp: t.timestamp,
    isSystem: t.is_system,
  })),
  notes: c.notes || [],
})

const claimStatusOptions = [
  { value: 'submitted', label: 'Submitted' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'ai_assessment', label: 'AI Assessment' },
  { value: 'investigation', label: 'Investigation' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'repair_settlement', label: 'Repair/Settlement' },
  { value: 'closed', label: 'Closed' },
]

export function ClaimDetails() {
  const { id } = useParams()
  const { user } = useAuth()
  const canViewAI = ['admin', 'employee', 'investigator'].includes(user?.role)
  const canManageAssignments = ['admin', 'employee'].includes(user?.role)
  const [claim, setClaim] = useState(null)
  const lifecycleStatus = (claim?.status || '').replace(/_/g, '-')
  const [statusDraft, setStatusDraft] = useState('')
  const [savingStatus, setSavingStatus] = useState(false)
  const [documentFile, setDocumentFile] = useState(null)
  const [documentType, setDocumentType] = useState('photos')
  const [uploadingDocument, setUploadingDocument] = useState(false)
  const [documentError, setDocumentError] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('overview')
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [assignmentOptions, setAssignmentOptions] = useState({ agents: [], investigators: [] })
  const [assignmentForm, setAssignmentForm] = useState({ adjuster: '', investigator: '' })
  const [savingAssignment, setSavingAssignment] = useState(false)

  const refreshClaim = async () => {
    const result = mapClaim(await claimService.getClaim(id))
    setClaim(result)
    setStatusDraft(result.status)
    setAssignmentForm({
      adjuster: String(result.assignedAdjusterId || ''),
      investigator: String(result.assignedInvestigatorId || ''),
    })
  }

  useEffect(() => {
    if (!canManageAssignments) return
    let active = true
    policyService.getPolicyFormOptions().then((options) => {
      if (active) setAssignmentOptions(options)
    }).catch(() => {})
    return () => { active = false }
  }, [canManageAssignments])

  useEffect(() => {
    let cancelled = false
    const fetchClaim = async () => {
      setLoading(true)
      setError('')
      try {
        const res = mapClaim(await claimService.getClaim(id))
        if (!cancelled) {
          setClaim(res)
          setStatusDraft(res.status)
          setAssignmentForm({ adjuster: String(res.assignedAdjusterId || ''), investigator: String(res.assignedInvestigatorId || '') })
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || 'Failed to load claim')
          setClaim(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchClaim()
    return () => { cancelled = true }
  }, [id])

  const saveAssignment = async (kind) => {
    setSavingAssignment(true)
    setError('')
    try {
      if (kind === 'adjuster') await claimService.assignAdjuster(id, Number(assignmentForm.adjuster))
      if (kind === 'investigator') await claimService.assignInvestigator(id, Number(assignmentForm.investigator))
      await refreshClaim()
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Unable to update claim assignment.')
    } finally {
      setSavingAssignment(false)
    }
  }

  const saveStatus = async () => {
    if (!claim || !statusDraft || statusDraft === claim.status) return
    setSavingStatus(true)
    setError('')
    try {
      const updated = mapClaim(await claimService.updateClaimStatus(claim.id, statusDraft))
      setClaim(updated)
      setStatusDraft(updated.status)
    } catch (err) {
      const message = err.response?.data?.detail || err.response?.data?.error?.details || err.response?.data?.error
      setError(typeof message === 'string' ? message : 'Unable to update claim status.')
    } finally {
      setSavingStatus(false)
    }
  }

  const uploadDocument = async () => {
    if (!documentFile || !claim) return
    if (documentFile.size > 25 * 1024 * 1024) {
      setDocumentError('Choose a file that is 25 MB or smaller.')
      return
    }

    setUploadingDocument(true)
    setDocumentError('')
    try {
      const formData = new FormData()
      formData.append('file', documentFile)
      formData.append('document_type', documentType)
      formData.append('original_name', documentFile.name)
      formData.append('description', '')
      await claimService.uploadClaimDocument(claim.id, formData)
      await refreshClaim()
      setDocumentFile(null)
      const input = document.getElementById('claim-detail-document')
      if (input) input.value = ''
    } catch (err) {
      const detail = err.response?.data?.detail || err.response?.data
      const message = typeof detail === 'string'
        ? detail
        : Object.entries(detail || {}).map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(', ') : value}`).join('; ')
      setDocumentError(message || 'The document could not be uploaded. Please try again.')
    } finally {
      setUploadingDocument(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await claimService.deleteClaim(claim.id)
      window.location.href = '/claims'
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete claim')
      setDeleteOpen(false)
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="page animate-pulse space-y-6">
        <div className="h-6 bg-gray-200 rounded w-36"></div>
        <div className="h-10 bg-gray-200 rounded w-64"></div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-96 bg-gray-200 rounded-xl"></div>
          <div className="h-96 bg-gray-200 rounded-xl"></div>
        </div>
      </div>
    )
  }

  if (!claim) {
    return (
      <div className="page">
        <div className="page-header">
          <Link to="/claims" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4">
            <ArrowLeft className="w-4 h-4" />
            Back to Claims
          </Link>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}
        <EmptyState
          icon={<Briefcase className="w-12 h-12" />}
          title="Claim Not Found"
          description={`No claim with identifier "${id}" exists in the records.`}
          action={<Button asChild><Link to="/claims">Browse Claims</Link></Button>}
        />
      </div>
    )
  }

  const tabs = [
    { id: 'overview', label: 'Claim Overview', icon: Briefcase },
    { id: 'incident', label: 'Incident & Damage Details', icon: AlertTriangle },
    ...(canViewAI ? [{ id: 'ai', label: 'AI Risk & Assessment', icon: Brain }] : []),
    { id: 'documents', label: `Documents (${claim.documents?.length || 0})`, icon: FileText },
    { id: 'timeline', label: 'Activity Timeline', icon: Activity },
  ]

  const severityLabel = (claim.incidentSeverity || '').replace(/_/g, ' ')

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/claims" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to claims list
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="page-title">{claim.claimNumber}</h1>
            <StatusBadge status={!canViewAI && claim.status === 'ai_assessment' ? 'under_review' : claim.status} />
            {canViewAI && claim.aiAssessment?.claimPriority && (
              <Badge variant={claim.aiAssessment.claimPriority === 'high' || claim.aiAssessment.claimPriority === 'critical' ? 'danger' : claim.aiAssessment.claimPriority === 'medium' ? 'warning' : 'success'}>
                {claim.aiAssessment.claimPriority.charAt(0).toUpperCase() + claim.aiAssessment.claimPriority.slice(1)} Priority
              </Badge>
            )}
          </div>
          <p className="page-subtitle">
            Customer: <strong className="text-gray-800">{claim.customerName}</strong> • Policy: <Link to={`/policies/${claim.policyId}`} className="text-primary underline">{claim.policyNumber}</Link>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button asChild variant="outline"><Link to={`/claims/${claim.id}/tracking`}><Activity className="w-4 h-4 mr-2" />Live Workflow Tracking</Link></Button>
          {canViewAI && <Button asChild variant="primary"><Link to={`/ai-assessment?claim=${claim.id}`}><Brain className="w-4 h-4 mr-2" />AI Assessment Center</Link></Button>}
          <Button variant="ghost" onClick={() => setDeleteOpen(true)} className="text-red-600 hover:text-red-700">
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {canManageAssignments && (
        <div className="mb-6 flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:flex-row sm:items-end">
          <Select
            label="Claim status"
            name="claimStatus"
            value={statusDraft}
            onChange={(event) => setStatusDraft(event.target.value)}
            options={claimStatusOptions}
          />
          <Button variant="primary" onClick={saveStatus} loading={savingStatus} disabled={savingStatus || statusDraft === claim.status}>
            Update Status
          </Button>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-2 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary font-semibold'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {activeTab === 'overview' && (
            <>
              {/* Core Claim Information */}
              <Card>
                <CardHeader title="Claim Information" subtitle="Key details submitted for this incident" />
                <CardContent className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-6 text-sm">
                    <div>
                      <span className="text-gray-500 block text-xs uppercase font-medium">Claim ID</span>
                      <span className="font-mono font-semibold text-gray-900">{claim.claimNumber}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-xs uppercase font-medium">Policy ID</span>
                      <Link to={`/policies/${claim.policyId}`} className="font-mono font-medium text-primary hover:underline">
                        {claim.policyNumber}
                      </Link>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-xs uppercase font-medium">Customer Name</span>
                      <span className="font-medium text-gray-900">{claim.customerName}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-xs uppercase font-medium">Claim Amount</span>
                      <span className="text-xl font-bold text-gray-900">{formatCurrency(claim.claimAmount)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-xs uppercase font-medium">Incident Date & Time</span>
                      <span className="text-gray-900">{formatDate(claim.incidentDate)} at {claim.incidentTime || '12:00'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block text-xs uppercase font-medium">Submission Timestamp</span>
                      <span className="text-gray-900">{formatDate(claim.submittedAt)} ({formatRelativeTime(claim.submittedAt)})</span>
                    </div>
                    <div className="md:col-span-2">
                      <span className="text-gray-500 block text-xs uppercase font-medium">Incident Location</span>
                      <span className="text-gray-900 flex items-center gap-1.5 mt-0.5">
                        <MapPin className="w-4 h-4 text-red-500" />
                        {claim.location}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Insured Vehicle Card */}
              <Card>
                <CardHeader title="Vehicle Involved" subtitle="Insured automobile recorded in policy" />
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="w-14 h-14 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                      <Car className="w-7 h-7" />
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 flex-1 text-sm">
                      <div>
                        <span className="text-gray-500 block text-xs">Vehicle</span>
                        <span className="font-semibold text-gray-900">
                          {claim.vehicle ? `${claim.vehicle.year} ${claim.vehicle.make} ${claim.vehicle.model}` : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 block text-xs">License Plate</span>
                        <span className="font-mono font-medium text-gray-900">{claim.vehicle?.licensePlate || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block text-xs">Number of Vehicles</span>
                        <span className="font-medium text-gray-900">{claim.numberOfVehicles} vehicle(s)</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block text-xs">Incident Type</span>
                        <span className="font-medium text-gray-900 capitalize">{claim.incidentType?.replace(/_/g, ' ')}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Status & Assignment */}
              <Card>
                <CardHeader title="Processing & Personnel" />
                <CardContent className="p-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-500 block text-xs">Assigned Adjuster</span>
                      <span className="font-medium text-gray-900 flex items-center gap-1.5 mt-1">
                        <UserCheck className="w-4 h-4 text-blue-600" />
                        {claim.assignedAdjuster || 'Unassigned'}
                      </span>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-500 block text-xs">Investigator</span>
                      <span className="font-medium text-gray-900 flex items-center gap-1.5 mt-1">
                        <Shield className="w-4 h-4 text-amber-600" />
                        {claim.assignedInvestigator || 'None Required'}
                      </span>
                    </div>
                  </div>
                  {canManageAssignments && (
                    <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4 border-t pt-5">
                      {[
                        { key: 'adjuster', label: 'Assign Adjuster', options: assignmentOptions.agents || [] },
                        { key: 'investigator', label: 'Assign Investigator', options: assignmentOptions.investigators || [] },
                      ].map(({ key, label, options }) => (
                        <div key={key} className="space-y-2">
                          <Select label={label} value={assignmentForm[key]} onChange={(event) => setAssignmentForm((current) => ({ ...current, [key]: event.target.value }))} options={options.map((item) => ({ value: String(item.id), label: item.name || item.email }))} placeholder={`Select ${label.toLowerCase()}`} />
                          <Button size="sm" disabled={!assignmentForm[key] || savingAssignment} onClick={() => saveAssignment(key)}>Save</Button>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}

          {activeTab === 'incident' && (
            <Card>
              <CardHeader title="Full Incident & Damage Report" />
              <CardContent className="p-6 space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  <div className="p-4 rounded-xl border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-gray-900">Injuries Involved</span>
                      {claim.injuries ? (
                        <Badge variant="danger">Injuries Reported</Badge>
                      ) : (
                        <Badge variant="success">No Injuries</Badge>
                      )}
                    </div>
                    <p className="text-gray-600">{claim.injuryDetails || 'No passenger or third-party injuries sustained.'}</p>
                  </div>

                  <div className="p-4 rounded-xl border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-gray-900">Property Damage</span>
                      {claim.propertyDamage ? (
                        <Badge variant="warning">Property Damaged</Badge>
                      ) : (
                        <Badge variant="neutral">None Reported</Badge>
                      )}
                    </div>
                    <p className="text-gray-600">{claim.propertyDamageDetails || 'No auxiliary property damage noted.'}</p>
                  </div>

                  <div className="p-4 rounded-xl border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-gray-900">Police Report</span>
                      {claim.policeReport ? (
                        <Badge variant="success">Report Filed</Badge>
                      ) : (
                        <Badge variant="neutral">Not Filed</Badge>
                      )}
                    </div>
                    <p className="text-gray-600">
                      {claim.policeReport ? `Report #: ${claim.policeReportNumber || 'PD-VERIFIED'}` : 'Customer indicated police was not called to scene.'}
                    </p>
                  </div>

                  <div className="p-4 rounded-xl border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-gray-900">Witnesses</span>
                      {claim.witnesses ? (
                        <Badge variant="info">Witnesses Present</Badge>
                      ) : (
                        <Badge variant="neutral">No Witnesses</Badge>
                      )}
                    </div>
                    <p className="text-gray-600">{claim.witnessDetails || 'No independent eyewitnesses recorded.'}</p>
                  </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-xl">
                  <h4 className="font-semibold text-gray-900 mb-1">Incident Summary & Narrative</h4>
                  <p className="text-sm text-gray-700 leading-relaxed">
                    Vehicle was operating under normal conditions near {claim.location} when incident occurred. Impact resulted in {severityLabel.toLowerCase()} damage requiring professional assessment and repair authorization.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {canViewAI && activeTab === 'ai' && (
            <Card>
              <CardHeader
                title="AI Assessment Summary"
                subtitle="Machine Learning preliminary insights"
                action={
                  <Button asChild variant="outline" size="sm"><Link to={`/ai-assessment?claim=${claim.id}`}>Full AI Center</Link></Button>
                }
              />
              <CardContent className="p-6">
                {claim.aiAssessment ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                      <div className="p-4 bg-blue-50/70 border border-blue-100 rounded-xl">
                        <span className="text-xs font-semibold text-blue-700 uppercase">Predicted Cost</span>
                        <div className="text-2xl font-bold text-blue-900 mt-1">{formatCurrency(claim.aiAssessment.predictedRepairCost)}</div>
                      </div>
                      <div className="p-4 bg-amber-50/70 border border-amber-100 rounded-xl">
                        <span className="text-xs font-semibold text-amber-700 uppercase">Fraud Risk Score</span>
                        <div className="text-2xl font-bold text-amber-800 mt-1">{claim.aiAssessment.fraudRiskScore}%</div>
                      </div>
                      <div className="p-4 bg-purple-50/70 border border-purple-100 rounded-xl">
                        <span className="text-xs font-semibold text-purple-700 uppercase">Total Loss Prob.</span>
                        <div className="text-2xl font-bold text-purple-900 mt-1">{claim.aiAssessment.totalLossProbability}%</div>
                      </div>
                      <div className="p-4 bg-emerald-50/70 border border-emerald-100 rounded-xl">
                        <span className="text-xs font-semibold text-emerald-700 uppercase">AI Confidence</span>
                        <div className="text-2xl font-bold text-emerald-800 mt-1">{claim.aiAssessment.confidence == null ? 'N/A' : `${claim.aiAssessment.confidence}%`}</div>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                      <span className="text-xs font-bold text-gray-500 uppercase tracking-wider block mb-1">Recommendation</span>
                      <p className="font-semibold text-gray-900 text-base">{claim.aiAssessment.aiRecommendation}</p>
                    </div>

                    {claim.aiAssessment.factors && claim.aiAssessment.factors.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-gray-900 text-sm mb-3">Assessment Contributing Factors</h4>
                        <div className="space-y-2">
                          {claim.aiAssessment.factors.map((f, i) => (
                            <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-gray-100 bg-white">
                              <span className="text-sm font-medium text-gray-800">{f.factor}</span>
                              <Badge variant={f.impact === 'positive' ? 'success' : f.impact === 'negative' ? 'danger' : 'neutral'}>
                                {f.impact} {(f.weight * 100).toFixed(0)}%
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <EmptyState
                    icon={<Brain className="w-12 h-12" />}
                    title="No AI assessment generated"
                    description="AI models have not yet evaluated this claim."
                  />
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'documents' && (
            <Card>
              <CardHeader title="Attached Documents & Evidence" />
              <CardContent className="p-6">
                <div className="mb-6 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4">
                  <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[1fr_1fr_auto]">
                    <Select
                      label="Document type"
                      name="claimDocumentType"
                      value={documentType}
                      onChange={(event) => setDocumentType(event.target.value)}
                      options={[
                        { value: 'photos', label: 'Damage photos' },
                        { value: 'estimate', label: 'Repair estimate' },
                        { value: 'police_report', label: 'Police report' },
                        { value: 'medical', label: 'Medical records' },
                        { value: 'other', label: 'Other document' },
                      ]}
                    />
                    <div>
                      <label htmlFor="claim-detail-document" className="mb-1 block text-sm font-medium text-gray-700">Choose a file</label>
                      <input
                        id="claim-detail-document"
                        type="file"
                        accept="image/png,image/jpeg,application/pdf"
                        className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:font-medium file:text-blue-700 hover:file:bg-blue-100"
                        onChange={(event) => {
                          setDocumentFile(event.target.files?.[0] || null)
                          setDocumentError('')
                        }}
                      />
                      <p className="mt-1 text-xs text-gray-500">PNG, JPG, or PDF up to 25 MB</p>
                    </div>
                    <Button
                      variant="primary"
                      onClick={uploadDocument}
                      loading={uploadingDocument}
                      disabled={!documentFile || uploadingDocument}
                      leftIcon={<Upload className="h-4 w-4" />}
                    >
                      Upload
                    </Button>
                  </div>
                  {documentFile && <p className="mt-2 text-sm text-gray-600">Selected: {documentFile.name}</p>}
                  {documentError && <p className="mt-2 text-sm text-red-600" role="alert">{documentError}</p>}
                </div>
                {claim.documents && claim.documents.length > 0 ? (
                  <div className="space-y-3">
                    {claim.documents.map((doc) => (
                      <div key={doc.id} className="flex items-center justify-between p-3 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 transition">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                            <FileText className="w-5 h-5" />
                          </div>
                          <div>
                            <p className="font-semibold text-gray-900 text-sm">{doc.name}</p>
                            <p className="text-xs text-gray-500">{doc.type?.replace(/_/g, ' ')} • Uploaded {formatDate(doc.uploadedAt)}</p>
                          </div>
                        </div>
                        <Button variant="outline" size="sm" asChild>
                          <a href={doc.file} target="_blank" rel="noreferrer">
                            <Download className="w-4 h-4 mr-1.5" />
                            Download
                          </a>
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<FileText className="w-12 h-12" />}
                    title="No documents attached"
                    description="No files or photos have been uploaded for this claim yet."
                  />
                )}
              </CardContent>
            </Card>
          )}

          {activeTab === 'timeline' && (
            <Card>
              <CardHeader title="Activity & Status History" />
              <CardContent className="p-6">
                {claim.timeline && claim.timeline.length > 0 ? (
                  <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-200">
                    {claim.timeline.map((item) => (
                      <div key={item.id} className="relative flex items-start gap-4">
                        <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-primary border-4 border-white flex items-center justify-center"></div>
                        <div className="flex-1 bg-gray-50 p-3.5 rounded-xl border border-gray-100">
                          <div className="flex items-center justify-between">
                            <h4 className="font-semibold text-gray-900 text-sm">{item.title}</h4>
                            <span className="text-xs text-gray-400 font-mono">{formatDate(item.timestamp)}</span>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                          <span className="text-xs text-gray-400 mt-1 block">By: {item.user}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<Activity className="w-12 h-12" />}
                    title="No activity yet"
                    description="No timeline events recorded for this claim."
                  />
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Sidebar Details */}
        <div className="space-y-6">
          {/* Workflow Status Tracker */}
          <Card>
            <CardHeader title="Claim Lifecycle Stage" />
            <CardContent className="p-6">
              <div className="space-y-2">
                {claimStatusWorkflow.map((step) => {
                  const isCurrent = step.id === lifecycleStatus
                  return (
                    <div
                      key={step.id}
                      className={clsx(
                        'flex items-center justify-between p-2.5 rounded-lg text-sm transition',
                        isCurrent ? 'bg-primary text-white font-semibold shadow-sm' : 'bg-gray-50 text-gray-600'
                      )}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className={clsx(
                          'w-6 h-6 rounded-full text-xs flex items-center justify-center font-bold',
                          isCurrent ? 'bg-white text-primary' : 'bg-gray-200 text-gray-700'
                        )}>
                          {step.order}
                        </span>
                        <span>{step.label}</span>
                      </div>
                      {isCurrent && <span className="text-xs bg-white/20 px-2 py-0.5 rounded">Active</span>}
                    </div>
                  )
                })}
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200">
                <Button asChild variant="outline" className="w-full"><Link to={`/claims/${claim.id}/tracking`}>View Live Tracking Details</Link></Button>
              </div>
            </CardContent>
          </Card>

          {/* Settlement / Financial Card */}
          <Card>
            <CardHeader title="Settlement Status" />
            <CardContent className="p-6 space-y-3 text-sm">
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-500">Claim Amount</span>
                <span className="font-semibold text-gray-900">{formatCurrency(claim.claimAmount)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-500">Policy Deductible</span>
                <span className="font-medium text-gray-900">₹500</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-500">Estimated Payout</span>
                <span className="font-bold text-emerald-600">{formatCurrency(Math.max(0, claim.claimAmount - 500))}</span>
              </div>
              <div className="pt-2">
                <Button asChild variant="secondary" className="w-full text-xs"><Link to="/settlements">Open Settlement Dashboard</Link></Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        isOpen={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onConfirm={handleDelete}
        title="Delete Claim"
        message={`Are you sure you want to delete claim ${claim.claimNumber}? This action cannot be undone.`}
        confirmText="Delete"
        loading={deleting}
      />
    </div>
  )
}

export default ClaimDetails
