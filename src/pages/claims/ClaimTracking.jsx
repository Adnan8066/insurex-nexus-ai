import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Activity,
  ArrowLeft,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Brain,
  Shield,
  FileText,
  Car,
  Wrench,
  Gavel,
  ChevronRight,
  UserCheck,
  Send,
} from 'lucide-react'
import { clsx } from 'clsx'
import { mockClaims, claimStatusWorkflow } from '../../data/claims'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'

const workflowStages = [
  {
    id: 'submitted',
    name: '1. Claim Submission',
    desc: 'Customer submits incident details, documents, and vehicle photos.',
    role: 'Customer / Intake Agent',
  },
  {
    id: 'under-review',
    name: '2. Under Review',
    desc: 'Initial policy coverage verification and adjuster assignment.',
    role: 'Claims Adjuster',
  },
  {
    id: 'ai-assessment',
    name: '3. AI Assessment',
    desc: 'ML repair cost estimation, fraud risk scoring, and total loss prediction.',
    role: 'Nexus AI Engine',
  },
  {
    id: 'investigation',
    name: '4. Investigation',
    desc: 'Special Investigations Unit (SIU) analysis for flagged anomalies.',
    role: 'SIU Investigator',
  },
  {
    id: 'approved',
    name: '5. Decision (Approved/Rejected)',
    desc: 'Final adjudication of claim liability and payout authorization.',
    role: 'Claims Authority',
  },
  {
    id: 'repair-settlement',
    name: '6. Repair & Settlement',
    desc: 'Certified repair shop dispatch and electronic deductible settlement.',
    role: 'Repair Facility & Finance',
  },
  {
    id: 'closed',
    name: '7. Claim Closed',
    desc: 'Vehicle delivered, settlement disbursed, case archived.',
    role: 'System Complete',
  },
]

export function ClaimTracking() {
  const { id } = useParams()
  const [claim, setClaim] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => {
      const found = mockClaims.find((c) => c.id === id || c.claimNumber === id) || mockClaims[0]
      setClaim(found)
      setLoading(false)
    }, 300)
    return () => clearTimeout(timer)
  }, [id])

  if (loading || !claim) {
    return (
      <div className="page animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 rounded w-48"></div>
        <div className="h-96 bg-gray-200 rounded-xl"></div>
      </div>
    )
  }

  // Find index in stages
  const currentStageIndex = workflowStages.findIndex((s) => s.id === claim.status) || 1

  return (
    <div className="page max-w-5xl mx-auto">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to={`/claims/${claim.id}`} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to claim {claim.claimNumber}
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="page-title">Lifecycle & Workflow Tracker</h1>
            <StatusBadge status={claim.status} />
          </div>
          <p className="page-subtitle">
            Tracking Claim <span className="font-mono font-semibold text-gray-800">{claim.claimNumber}</span> • Customer: {claim.customerName}
          </p>
        </div>

        <div className="flex gap-2">
          <Link to={`/claims/${claim.id}`}>
            <Button variant="secondary">View Full Details</Button>
          </Link>
          <Link to="/ai-decision">
            <Button variant="primary">
              <Brain className="w-4 h-4 mr-2" />
              AI Decision Center
            </Button>
          </Link>
        </div>
      </div>

      {/* Progress Bar Header */}
      <Card className="mb-8">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
            <div>
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Overall Workflow Progress</span>
              <h3 className="text-lg font-bold text-gray-900 mt-0.5">
                Stage {currentStageIndex + 1} of 7: {workflowStages[currentStageIndex]?.name.replace(/^\d+\.\s*/, '')}
              </h3>
            </div>
            <div className="text-right">
              <span className="text-2xl font-black text-primary">
                {Math.round(((currentStageIndex + 1) / 7) * 100)}%
              </span>
              <span className="text-xs text-gray-500 block">Workflow Completion</span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
            <div
              className="bg-primary h-3 rounded-full transition-all duration-500"
              style={{ width: `${Math.round(((currentStageIndex + 1) / 7) * 100)}%` }}
            />
          </div>

          {/* Workflow stages visual pills */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 mt-6">
            {workflowStages.map((stage, idx) => {
              const isPast = idx < currentStageIndex
              const isCurrent = idx === currentStageIndex
              return (
                <div
                  key={stage.id}
                  className={clsx(
                    'p-2.5 rounded-xl border text-center transition',
                    isCurrent
                      ? 'border-primary bg-primary/10 text-primary font-bold shadow-sm ring-2 ring-primary/20'
                      : isPast
                      ? 'border-emerald-200 bg-emerald-50/50 text-emerald-800 font-medium'
                      : 'border-gray-200 bg-gray-50/50 text-gray-400'
                  )}
                >
                  <div className="text-[10px] uppercase font-semibold">Step {idx + 1}</div>
                  <div className="text-xs truncate font-medium mt-0.5">
                    {stage.name.replace(/^\d+\.\s*/, '')}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Vertical Stages Details */}
      <div className="space-y-4">
        {workflowStages.map((stage, idx) => {
          const isPast = idx < currentStageIndex
          const isCurrent = idx === currentStageIndex
          const isFuture = idx > currentStageIndex

          return (
            <div
              key={stage.id}
              className={clsx(
                'rounded-xl border p-5 transition bg-white',
                isCurrent
                  ? 'border-primary shadow-md ring-1 ring-primary/20'
                  : isPast
                  ? 'border-emerald-200'
                  : 'border-gray-200 opacity-60'
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div
                    className={clsx(
                      'w-10 h-10 rounded-full flex items-center justify-center font-bold flex-shrink-0 text-sm',
                      isCurrent
                        ? 'bg-primary text-white ring-4 ring-primary/20'
                        : isPast
                        ? 'bg-emerald-600 text-white'
                        : 'bg-gray-100 text-gray-500'
                    )}
                  >
                    {isPast ? <CheckCircle2 className="w-5 h-5" /> : idx + 1}
                  </div>
                  <div>
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <h4 className="font-bold text-gray-900 text-base">{stage.name}</h4>
                      {isCurrent && (
                        <span className="bg-primary text-white text-xs font-semibold px-2.5 py-0.5 rounded-full animate-pulse">
                          In Progress
                        </span>
                      )}
                      {isPast && (
                        <span className="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2 py-0.5 rounded-full">
                          Completed
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{stage.desc}</p>
                    <div className="mt-2 text-xs text-gray-500 flex items-center gap-2">
                      <span className="font-semibold text-gray-700">Handler:</span> {stage.role}
                    </div>
                  </div>
                </div>

                <div className="text-right flex-shrink-0 text-xs text-gray-400">
                  {isCurrent && (
                    <span className="text-primary font-semibold text-xs">Estimated completion: 1-2 days</span>
                  )}
                  {isPast && (
                    <span className="text-emerald-700 font-medium">Verified Stage</span>
                  )}
                </div>
              </div>

              {/* Extended Details for Current Stage */}
              {isCurrent && (
                <div className="mt-4 pt-4 border-t border-gray-100 bg-gray-50/80 -mx-5 -mb-5 p-5 rounded-b-xl">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-sm">
                    <div>
                      <span className="font-bold text-gray-800 block">Current Action Required:</span>
                      <span className="text-gray-600">
                        {stage.id === 'ai-assessment' && 'Awaiting automated cross-verification of damage photo embeddings.'}
                        {stage.id === 'under-review' && 'Adjuster Sarah Mitchell reviewing submitted documentation.'}
                        {stage.id === 'investigation' && 'Investigator assigned to review conflicting timeline notes.'}
                        {stage.id === 'approved' && 'Finance team preparing digital settlement agreement.'}
                        {stage.id === 'repair-settlement' && 'AutoFix Repair facility performing scheduled body repair work.'}
                        {stage.id === 'submitted' && 'Intake queue validating initial police report and photos.'}
                        {stage.id === 'closed' && 'Claim archive completed.'}
                      </span>
                    </div>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => alert(`Simulated action triggered for stage: ${stage.name}`)}
                    >
                      Update Stage Note
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ClaimTracking
