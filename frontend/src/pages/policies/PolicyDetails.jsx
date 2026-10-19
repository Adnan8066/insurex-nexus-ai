import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  FileText,
  Shield,
  Calendar,
  Car,
  Home,
  ArrowLeft,
  Edit,
  Download,
  MoreVertical,
  CheckCircle,
  AlertTriangle,
  Clock,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { policyService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'

const mapPolicy = (p) => ({
  id: p.id,
  policyNumber: p.policy_number,
  customerName: p.customer_name,
  customerEmail: p.customer_email,
  agent: p.agent_name,
  type: p.type,
  status: p.status,
  startDate: p.start_date,
  endDate: p.end_date,
  premium: p.premium,
  deductible: p.deductible,
  paymentFrequency: p.payment_frequency,
  autoRenew: p.auto_renew,
  policyPlan: p.coverage?.policy_plan || null,
  coverage: p.coverage_details || {},
  vehicle: p.vehicle_info || (p.vehicle ? {
    id: p.vehicle.id,
    make: p.vehicle.make,
    model: p.vehicle.model,
    year: p.vehicle.year,
    licensePlate: p.vehicle.license_plate,
    vin: p.vehicle.vin,
    color: p.vehicle.color,
  } : null),
  propertyAddress: p.property_address,
  propertyType: p.property_type,
  propertyYearBuilt: p.property_year_built,
  propertySquareFootage: p.property_square_footage,
  documents: p.documents || [],
  premiumHistory: p.premium_history || [],
  createdAt: p.created_at,
  updatedAt: p.updated_at,
})

export function PolicyDetails() {
  const { id } = useParams()
  const { user } = useAuth()
  const canEditPolicy = user?.role === 'admin'
  const canFileClaim = ['customer', 'employee', 'admin'].includes(user?.role)
  const [loading, setLoading] = useState(true)
  const [policy, setPolicy] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [error, setError] = useState('')
  const [endorsements, setEndorsements] = useState([])
  const [endorsementDraft, setEndorsementDraft] = useState({ change_type: 'mid_term_adjustment', deductible: '', premium_delta: '0', asset_description: '', asset_value: '' })
  const [endorsementError, setEndorsementError] = useState('')
  const [savingEndorsement, setSavingEndorsement] = useState(false)
  const canManageEndorsements = ['employee', 'admin'].includes(user?.role)
  const [scheduleOpen, setScheduleOpen] = useState(false)

  const downloadCertificate = () => {
    const certificate = window.open('', '_blank', 'width=900,height=700')
    if (!certificate) return
    certificate.document.write(`<!doctype html><html><head><title>Policy Certificate ${policy.policyNumber || ''}</title><style>body{font:16px Arial,sans-serif;color:#172033;margin:48px}h1{color:#1e3a5f}table{border-collapse:collapse;width:100%;margin-top:24px}td{padding:12px;border:1px solid #d1d5db}small{color:#6b7280}@media print{button{display:none}}</style></head><body><h1>Insurance Certificate</h1><p>This document confirms the policy details shown below.</p><table><tr><td>Policy number</td><td>${policy.policyNumber || '—'}</td></tr><tr><td>Policy holder</td><td>${policy.customerName || '—'}</td></tr><tr><td>Policy type</td><td>${policy.policyPlan?.name || policy.type || '—'}</td></tr><tr><td>Effective date</td><td>${formatDate(policy.startDate)}</td></tr><tr><td>Expiration date</td><td>${formatDate(policy.endDate)}</td></tr><tr><td>Status</td><td>${policy.status || '—'}</td></tr><tr><td>Annual premium</td><td>${formatCurrency(policy.premium)}</td></tr></table><p><small>Generated from InsureX Nexus AI policy records.</small></p><button onclick="window.print()">Print / Save as PDF</button></body></html>`)
    certificate.document.close()
  }

  const installmentsPerYear = ({ monthly: 12, quarterly: 4, semi_annual: 2, annual: 1 }[policy?.paymentFrequency] || 1)
  const installmentAmount = (Number(policy?.premium) || 0) / installmentsPerYear
  const paymentSchedule = Array.from({ length: installmentsPerYear }, (_, index) => {
    const date = new Date(`${policy?.startDate || new Date().toISOString().slice(0, 10)}T00:00:00`)
    date.setMonth(date.getMonth() + Math.round(index * 12 / installmentsPerYear))
    return { date, amount: installmentAmount }
  })

  useEffect(() => {
    let cancelled = false
    const fetchPolicy = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await policyService.getPolicy(id)
        if (!cancelled) {
          setPolicy(mapPolicy(res))
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || 'Failed to load policy')
          setPolicy(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPolicy()
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    let active = true
    if (!canManageEndorsements) return () => { active = false }
    policyService.getEndorsements(id).then((rows) => {
      if (active) setEndorsements(Array.isArray(rows) ? rows : [])
    }).catch(() => {
      if (active) setEndorsements([])
    })
    return () => { active = false }
  }, [canManageEndorsements, id])

  const submitEndorsement = async (event) => {
    event.preventDefault()
    setSavingEndorsement(true)
    setEndorsementError('')
    try {
      const assets = endorsementDraft.asset_description.trim()
        ? [{ description: endorsementDraft.asset_description.trim(), value: Number(endorsementDraft.asset_value) }]
        : undefined
      const created = await policyService.createEndorsement(id, {
        change_type: endorsementDraft.change_type,
        ...(endorsementDraft.deductible !== '' ? { deductible: Number(endorsementDraft.deductible) } : {}),
        premium_delta: Number(endorsementDraft.premium_delta || 0),
        ...(assets ? { assets_add: assets } : {}),
      })
      setEndorsements((current) => [created, ...current])
      setEndorsementDraft({ change_type: 'mid_term_adjustment', deductible: '', premium_delta: '0', asset_description: '', asset_value: '' })
    } catch (err) {
      setEndorsementError(err.response?.data?.detail || 'Unable to submit the endorsement for review.')
    } finally {
      setSavingEndorsement(false)
    }
  }

  const approveEndorsement = async (endorsementId) => {
    try {
      const updated = await policyService.approveEndorsement(id, endorsementId)
      setEndorsements((current) => current.map((item) => item.id === updated.id ? updated : item))
      const refreshed = await policyService.getPolicy(id)
      setPolicy(mapPolicy(refreshed))
    } catch (err) {
      setEndorsementError(err.response?.data?.detail || 'Unable to approve this endorsement.')
    }
  }

  if (loading) {
    return (
      <div className="page animate-pulse">
        <div className="page-header">
          <div className="h-8 bg-gray-200 rounded w-48 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-64"></div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6 h-32"><div className="h-full bg-gray-100 rounded"></div></div>
            <div className="card p-6 h-48"><div className="h-full bg-gray-100 rounded"></div></div>
          </div>
          <div className="space-y-6">
            <div className="card p-6 h-32"><div className="h-full bg-gray-100 rounded"></div></div>
            <div className="card p-6 h-32"><div className="h-full bg-gray-100 rounded"></div></div>
          </div>
        </div>
      </div>
    )
  }

  if (!policy) {
    return (
      <div className="page">
        <div className="page-header">
          <Link to="/policies" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4">
            <ArrowLeft className="w-4 h-4" />
            Back to Policies
          </Link>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}
      </div>
    )
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'coverage', label: 'Coverage', icon: Shield },
    { id: 'vehicle', label: policy.vehicle ? 'Vehicle' : 'Property', icon: policy.vehicle ? Car : Home },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'history', label: 'History', icon: Clock },
  ]

  return (
    <div className="page">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/policies" className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Policies
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="page-title">{policy.policyNumber || ''}</h1>
            <StatusBadge status={policy.status} />
          </div>
          <p className="page-subtitle">{policy.policyPlan?.name || policy.type || ''} • {policy.customerName || ''}</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={downloadCertificate}>
            <Download className="w-4 h-4 mr-2" />
            Download
          </Button>
          <Button variant="ghost" size="sm" className="relative">
            <MoreVertical className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1" aria-label="Policy tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-t-lg border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {activeTab === 'overview' && (
            <>
              {canManageEndorsements && <Card>
                <CardHeader title="Policy endorsements" subtitle="Changes are applied only after an administrator approves them." />
                <CardContent>
                  <form onSubmit={submitEndorsement} className="mb-5 grid gap-3 md:grid-cols-2">
                    <input className="input-field" aria-label="Change type" value={endorsementDraft.change_type} onChange={(event) => setEndorsementDraft((d) => ({ ...d, change_type: event.target.value }))} />
                    <input className="input-field" aria-label="New deductible" type="number" min="0" step="0.01" placeholder="New deductible (optional)" value={endorsementDraft.deductible} onChange={(event) => setEndorsementDraft((d) => ({ ...d, deductible: event.target.value }))} />
                    <input className="input-field" aria-label="Annual premium adjustment" type="number" step="0.01" placeholder="Annual premium change (+/−)" value={endorsementDraft.premium_delta} onChange={(event) => setEndorsementDraft((d) => ({ ...d, premium_delta: event.target.value }))} />
                    <input className="input-field" aria-label="Additional insured asset" placeholder="Asset to add (optional)" value={endorsementDraft.asset_description} onChange={(event) => setEndorsementDraft((d) => ({ ...d, asset_description: event.target.value }))} />
                    {endorsementDraft.asset_description && <input className="input-field" aria-label="Additional asset value" type="number" min="0.01" step="0.01" placeholder="Asset value" value={endorsementDraft.asset_value} onChange={(event) => setEndorsementDraft((d) => ({ ...d, asset_value: event.target.value }))} required />}
                    <Button type="submit" variant="outline" disabled={savingEndorsement}>{savingEndorsement ? 'Submitting…' : 'Submit endorsement for review'}</Button>
                  </form>
                  {endorsementError && <p role="alert" className="mb-3 text-sm text-red-700">{endorsementError}</p>}
                  {endorsements.length === 0 ? <p className="text-sm text-gray-500">No endorsement requests yet.</p> : <div className="space-y-3">
                    {endorsements.map((endorsement) => <div key={endorsement.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 p-3">
                      <div><p className="font-medium text-gray-900">{endorsement.change_type} · {endorsement.status}</p><p className="text-sm text-gray-500">Annual premium change: {formatCurrency(endorsement.premium_delta)}</p></div>
                      {user?.role === 'admin' && endorsement.status === 'pending' && <Button type="button" size="sm" onClick={() => approveEndorsement(endorsement.id)}>Approve and apply</Button>}
                    </div>)}
                  </div>}
                </CardContent>
              </Card>}
              {policy.policyPlan && (
                <Card>
                  <CardHeader title="Selected Policy Tier" subtitle={`${policy.policyPlan.id} · ${policy.policyPlan.category}`} />
                  <CardContent>
                    <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                      The tier details and base premium are user-provided estimates, not a verified insurer quote or policy offer.
                    </p>
                    <dl className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div><dt className="text-sm font-medium text-gray-500">Coverage sections</dt><dd className="mt-1 text-gray-900">{(policy.policyPlan.coverage_sections || []).join('; ') || 'None listed'}</dd></div>
                      <div><dt className="text-sm font-medium text-gray-500">Mandatory covers</dt><dd className="mt-1 text-gray-900">{(policy.policyPlan.mandatory_covers || []).join('; ') || 'None listed'}</dd></div>
                      <div><dt className="text-sm font-medium text-gray-500">Available add-ons</dt><dd className="mt-1 text-gray-900">{(policy.policyPlan.addons || []).join(', ') || 'None listed'}</dd></div>
                      <div><dt className="text-sm font-medium text-gray-500">Base premium estimate</dt><dd className="mt-1 text-gray-900">{formatCurrency(policy.policyPlan.base_premium_estimate_inr, 'INR', 'en-IN')} per year</dd></div>
                    </dl>
                  </CardContent>
                </Card>
              )}
              <Card>
                <CardHeader title="Policy Information" />
                <CardContent>
                  <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Policy Type</dt>
                      <dd className="mt-1 text-gray-900 flex items-center gap-2">
                        <span className={clsx('text-gray-400', (policy.type || '').toLowerCase().includes('auto') && 'text-blue-500')}>
                          {(policy.type || '').toLowerCase().includes('auto') ? <Car className="w-4 h-4" /> : <Home className="w-4 h-4" />}
                        </span>
                        {policy.policyPlan?.name || policy.type || ''}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Agent</dt>
                      <dd className="mt-1 text-gray-900">{policy.agent || ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Effective Date</dt>
                      <dd className="mt-1 text-gray-900">{formatDate(policy.startDate)}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Expiration Date</dt>
                      <dd className="mt-1 text-gray-900">{formatDate(policy.endDate)}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Payment Frequency</dt>
                      <dd className="mt-1 text-gray-900 capitalize">{policy.paymentFrequency ? policy.paymentFrequency.replace(/_/g, ' ') : ''}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Auto Renewal</dt>
                      <dd className="mt-1 text-gray-900 flex items-center gap-2">
                        {policy.autoRenew ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-yellow-500" />
                        )}
                        {policy.autoRenew ? 'Enabled' : 'Disabled'}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              <Card>
                <CardHeader title="Financial Summary" />
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <dt className="text-sm font-medium text-gray-500">Annual Premium</dt>
                      <dd className="mt-1 text-2xl font-bold text-gray-900">{formatCurrency(policy.premium)}</dd>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <dt className="text-sm font-medium text-gray-500">Deductible</dt>
                      <dd className="mt-1 text-2xl font-bold text-gray-900">{formatCurrency(policy.deductible)}</dd>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <dt className="text-sm font-medium text-gray-500">Payment per Period</dt>
                      <dd className="mt-1 text-2xl font-bold text-gray-900">
                        {formatCurrency(policy.paymentFrequency === 'monthly' ? (Number(policy.premium) || 0) / 12 : (Number(policy.premium) || 0))}
                      </dd>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {activeTab === 'coverage' && (
            <Card>
              <CardHeader title="Coverage Details" subtitle="Coverage limits and inclusions" />
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 font-medium text-gray-500">Coverage</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-500">Limit</th>
                        <th className="text-right py-3 px-4 font-medium text-gray-500">Deductible</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {Object.entries(policy.coverage || {}).map(([key, value]) => (
                        <tr key={key} className="hover:bg-gray-50">
                          <td className="py-3 px-4 text-gray-900 capitalize">{key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ')}</td>
                          <td className="py-3 px-4 text-right font-medium text-gray-900">{formatCurrency(value)}</td>
                          <td className="py-3 px-4 text-right text-gray-500">
                            {key === 'liability' || key === 'dwelling' || key === 'personalProperty' || key === 'personal_property' ? formatCurrency(policy.deductible) : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'vehicle' && policy.vehicle && (
            <Card>
              <CardHeader title="Vehicle Information" />
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <dl className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Make</dt>
                          <dd className="mt-1 text-gray-900">{policy.vehicle.make || ''} {policy.vehicle.model || ''}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Year</dt>
                          <dd className="mt-1 text-gray-900">{policy.vehicle.year || ''}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Color</dt>
                          <dd className="mt-1 text-gray-900">{policy.vehicle.color || ''}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">VIN</dt>
                          <dd className="mt-1 text-gray-900 font-mono">{policy.vehicle.vin || ''}</dd>
                        </div>
                        <div>
                          <dt className="text-sm font-medium text-gray-500">License Plate</dt>
                          <dd className="mt-1 text-gray-900">{policy.vehicle.licensePlate || ''}</dd>
                        </div>
                      </div>
                    </dl>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'documents' && (
            <Card>
              <CardHeader title="Policy Documents" action={<Button variant="outline" size="sm">Upload</Button>} />
              <CardContent>
                <EmptyState
                  icon={<FileText className="w-12 h-12" />}
                  title="No documents uploaded"
                  description="Policy documents will appear here once uploaded."
                  action={<Button variant="outline" size="sm">Upload Document</Button>}
                />
              </CardContent>
            </Card>
          )}

          {activeTab === 'history' && (
            <Card>
              <CardHeader title="Policy History" />
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                    <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
                      <FileText className="w-4 h-4 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Policy Created</p>
                      <p className="text-sm text-gray-500">{formatDate(policy.startDate)}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Policy Activated</p>
                      <p className="text-sm text-gray-500">{formatDate(policy.startDate)}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Quick Actions" />
            <CardContent>
              <div className="space-y-3">
                {canEditPolicy && <Button variant="outline" className="w-full justify-start gap-3" asChild>
                  <Link to={`/policies/${policy.id}/edit`}>
                    <Edit className="w-4 h-4" />
                    Edit Policy
                  </Link>
                </Button>}
                <Button variant="outline" className="w-full justify-start gap-3" onClick={downloadCertificate}>
                  <Download className="w-4 h-4" />
                  Download Certificate
                </Button>
                <Button variant="outline" className="w-full justify-start gap-3" onClick={() => setScheduleOpen(true)}>
                  <Calendar className="w-4 h-4" />
                  View Payment Schedule
                </Button>
                {canFileClaim && <Button variant="outline" className="w-full justify-start gap-3" asChild>
                  <Link to={`/claims/new?policy=${policy.id}`}>
                    <Shield className="w-4 h-4" />
                    File a Claim
                  </Link>
                </Button>}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Policy Status" />
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">Days Remaining</span>
                    <span className="font-medium text-gray-900">
                       {Math.max(0, Math.ceil(((new Date(policy.endDate)) - new Date()) / (1000 * 60 * 60 * 24)))} days
                     </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{
                         width: `${Math.min(100, Math.max(0, (((new Date()) - new Date(policy.startDate || new Date())) / ((new Date(policy.endDate || new Date())) - new Date(policy.startDate || new Date())) || 0) * 100))}%`
                       }}
                    />
                  </div>
                </div>
                <div className="pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-600">
                    {policy.status === 'active' ? 'Policy is active and in force.' : 'Policy is not currently active.'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
      {scheduleOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setScheduleOpen(false) }}>
          <section role="dialog" aria-modal="true" aria-labelledby="payment-schedule-title" className="w-full max-w-xl rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4"><div><h2 id="payment-schedule-title" className="text-xl font-semibold">Payment Schedule</h2><p className="mt-1 text-sm text-gray-500">{policy.policyNumber} · {policy.paymentFrequency?.replace(/_/g, ' ') || 'annual'} installments</p></div><button className="text-gray-500" onClick={() => setScheduleOpen(false)} aria-label="Close payment schedule">×</button></div>
            <div className="mt-5 divide-y divide-gray-100">{paymentSchedule.map((payment, index) => <div key={index} className="flex justify-between py-3"><span>Installment {index + 1} · {formatDate(payment.date)}</span><strong>{formatCurrency(payment.amount)}</strong></div>)}</div>
            <p className="mt-4 text-sm text-gray-500">This schedule is calculated from the policy premium and frequency. Contact your insurer to arrange or confirm payment.</p>
            <div className="mt-5 flex justify-end"><Button variant="primary" onClick={() => setScheduleOpen(false)}>Done</Button></div>
          </section>
        </div>
      )}
    </div>
  )
}

export default PolicyDetails
