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
  CheckCircle2,
  XCircle,
  Brain,
  Download,
  Share2,
  Users,
  Activity,
  FileCheck,
  ChevronRight,
  UserCheck,
  Building,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { mockClaims, claimStatusWorkflow } from '../../data/claims'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'

export function ClaimDetails() {
  const { id } = useParams()
  const [claim, setClaim] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    const timer = setTimeout(() => {
      const found = mockClaims.find((c) => c.id === id || c.claimNumber === id)
      setClaim(found || null)
      setLoading(false)
    }, 300)
    return () => clearTimeout(timer)
  }, [id])

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
    { id: 'ai', label: 'AI Risk & Assessment', icon: Brain },
    { id: 'documents', label: `Documents (${claim.documents?.length || 0})`, icon: FileText },
    { id: 'timeline', label: 'Activity Timeline', icon: Activity },
  ]

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
            <StatusBadge status={claim.status} />
            {claim.aiAssessment && (
              <Badge variant={claim.aiAssessment.claimPriority === 'High' ? 'danger' : claim.aiAssessment.claimPriority === 'Medium' ? 'warning' : 'success'}>
                {claim.aiAssessment.claimPriority} Priority
              </Badge>
            )}
          </div>
          <p className="page-subtitle">
            Customer: <strong className="text-gray-800">{claim.customerName}</strong> • Policy: <Link to={`/policies/${claim.policyId}`} className="text-primary underline">{claim.policyNumber}</Link>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to={`/claims/${claim.id}/tracking`}>
            <Button variant="outline">
              <Activity className="w-4 h-4 mr-2" />
              Live Workflow Tracking
            </Button>
          </Link>
          <Link to={`/ai-assessment?claim=${claim.id}`}>
            <Button variant="primary">
              <Brain className="w-4 h-4 mr-2" />
              AI Assessment Center
            </Button>
          </Link>
        </div>
      </div>

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
                          {claim.vehicle?.year} {claim.vehicle?.make} {claim.vehicle?.model}
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
                        <span className="font-medium text-gray-900">{claim.incidentType}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Status & Assignment */}
              <Card>
                <CardHeader title="Processing & Personnel" />
                <CardContent className="p-6">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
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
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <span className="text-gray-500 block text-xs">Repair Facility</span>
                      <span className="font-medium text-gray-900 flex items-center gap-1.5 mt-1">
                        <Building className="w-4 h-4 text-emerald-600" />
                        {claim.assignedRepairShop || 'Pending Selection'}
                      </span>
                    </div>
                  </div>
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
                    Vehicle was operating under normal conditions near {claim.location} when incident occurred. Impact resulted in {claim.incidentSeverity.toLowerCase()} damage requiring professional assessment and repair authorization.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'ai' && (
            <Card>
              <CardHeader
                title="AI Assessment Summary"
                subtitle="Machine Learning preliminary insights (v2.3.1 Model Engine)"
                action={
                  <Link to={`/ai-assessment?claim=${claim.id}`}>
                    <Button variant="outline" size="sm">Full AI Center</Button>
                  </Link>
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
                        <div className="text-2xl font-bold text-emerald-800 mt-1">{claim.aiAssessment.confidence}%</div>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                      <span className="text-xs font-bold text-gray-500 uppercase tracking-wider block mb-1">Recommendation</span>
                      <p className="font-semibold text-gray-900 text-base">{claim.aiAssessment.aiRecommendation}</p>
                    </div>

                    <div>
                      <h4 className="font-semibold text-gray-900 text-sm mb-3">Assessment Contributing Factors</h4>
                      <div className="space-y-2">
                        {claim.aiAssessment.factors?.map((f, i) => (
                          <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-gray-100 bg-white">
                            <span className="text-sm font-medium text-gray-800">{f.factor}</span>
                            <Badge variant={f.impact === 'positive' ? 'success' : f.impact === 'negative' ? 'danger' : 'neutral'}>
                              {f.impact} ({(f.weight * 100).toFixed(0)}%)
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
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
                            <p className="text-xs text-gray-500">{doc.type} • Uploaded {formatDate(doc.uploadedAt)}</p>
                          </div>
                        </div>
                        <Button variant="outline" size="sm">
                          <Download className="w-4 h-4 mr-1.5" />
                          Download
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
                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-200">
                  {claim.timeline?.map((item) => (
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
                {claimStatusWorkflow.map((step, idx) => {
                  const isCurrent = step.id === claim.status
                  const order = step.order
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
                          {order}
                        </span>
                        <span>{step.label}</span>
                      </div>
                      {isCurrent && <span className="text-xs bg-white/20 px-2 py-0.5 rounded">Active</span>}
                    </div>
                  )
                })}
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200">
                <Link to={`/claims/${claim.id}/tracking`} className="block">
                  <Button variant="outline" className="w-full">
                    View Live Tracking Details
                  </Button>
                </Link>
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
                <span className="font-medium text-gray-900">$500.00</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-500">Estimated Payout</span>
                <span className="font-bold text-emerald-600">{formatCurrency(Math.max(0, claim.claimAmount - 500))}</span>
              </div>
              <div className="pt-2">
                <Link to="/settlements">
                  <Button variant="secondary" className="w-full text-xs">
                    Open Settlement Dashboard
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default ClaimDetails
