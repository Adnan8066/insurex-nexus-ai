import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Activity,
  ArrowLeft,
  Brain,
  CheckCircle2,
  Circle,
  FileText,
  Headphones,
  XCircle,
} from 'lucide-react'
import { clsx } from 'clsx'
import { claimService } from '../../services/claimService'
import { useAuth } from '../../context/useAuth'
import { Card, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { StatusBadge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { CLAIM_STATUSES, labelFor } from '../../constants/domain'
import { formatCurrency, formatDate } from '../../utils/helpers'

// Five plain-language steps; every backend status maps onto one of them.
const STEPS = [
  { key: 'submitted', label: 'Submitted' },
  { key: 'review', label: 'Under review' },
  { key: 'decision', label: 'Decision' },
  { key: 'settlement', label: 'Repair & payment' },
  { key: 'closed', label: 'Closed' },
]

const STEP_FOR_STATUS = {
  submitted: 'submitted',
  under_review: 'review',
  ai_assessment: 'review',
  investigation: 'review',
  approved: 'decision',
  rejected: 'decision',
  repair_settlement: 'settlement',
  closed: 'closed',
}

// Internal review stages are shown to customers as a single "Under review" step.
const CUSTOMER_STATUS = { ai_assessment: 'under_review', investigation: 'under_review' }

const CUSTOMER_NEXT = {
  submitted: 'We have received your claim. A claims specialist will review it shortly. Adding damage photos and a repair estimate helps us decide faster.',
  under_review: 'We are reviewing your claim and documents. We will contact you if we need anything else.',
  approved: 'Good news: your claim is approved. We will arrange the repair or payment and keep you updated.',
  rejected: 'Your claim was not approved. If you have questions about this decision, please contact support.',
  repair_settlement: 'Your repair or payment is in progress. We will let you know when it is complete.',
  closed: 'This claim is complete. No further action is needed.',
}

const STAFF_NEXT = {
  submitted: 'Review the claim details and assign an adjuster.',
  under_review: 'Run the AI assessment or record a decision.',
  ai_assessment: 'Check the AI results in Automated Review, then decide.',
  investigation: 'Waiting for the investigator to finish their review.',
  approved: 'Arrange the repair or settlement.',
  rejected: 'No further action unless the customer appeals.',
  repair_settlement: 'Complete the repair or payment, then close the claim.',
  closed: 'No action needed.',
}

function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

export function ClaimTracking() {
  const { id } = useParams()
  const { user } = useAuth()
  const isStaff = ['admin', 'employee', 'investigator'].includes(user?.role)
  const [claim, setClaim] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const fetchClaim = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await claimService.getClaim(id)
        if (!cancelled) setClaim(res)
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.status === 404 ? '' : 'We could not load this claim. Please try again.')
          setClaim(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchClaim()
    return () => { cancelled = true }
  }, [id])

  if (loading) {
    return (
      <div className="page max-w-4xl mx-auto animate-pulse space-y-6" role="status" aria-label="Loading claim">
        <div className="h-8 bg-gray-200 rounded w-48"></div>
        <div className="h-40 bg-gray-200 rounded-xl"></div>
        <div className="h-64 bg-gray-200 rounded-xl"></div>
      </div>
    )
  }

  if (!claim) {
    return (
      <div className="page max-w-4xl mx-auto">
        {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">{error}</div>}
        <EmptyState
          icon={<Activity className="w-12 h-12" />}
          title="Claim not found"
          description="This claim doesn't exist or you don't have access to it."
          action={<Button asChild><Link to="/claims">Go to my claims</Link></Button>}
        />
      </div>
    )
  }

  const status = claim.status
  const shownStatus = isStaff ? status : (CUSTOMER_STATUS[status] || status)
  const isRejected = status === 'rejected'
  const currentStep = Math.max(0, STEPS.findIndex((step) => step.key === STEP_FOR_STATUS[status]))
  const nextText = (isStaff ? STAFF_NEXT : CUSTOMER_NEXT)[shownStatus]

  // Status history, oldest first. Customers see simplified labels and no internal reasons.
  const history = [...(claim.status_history || [])]
    .sort((a, b) => new Date(a.changed_at) - new Date(b.changed_at))
    .map((entry) => ({
      id: entry.id,
      status: isStaff ? entry.to_status : (CUSTOMER_STATUS[entry.to_status] || entry.to_status),
      at: entry.changed_at,
      by: isStaff ? entry.changed_by_name : null,
      reason: isStaff ? entry.reason : null,
    }))
    .filter((entry, index, list) => isStaff || index === 0 || entry.status !== list[index - 1].status)
  if (!history.some((entry) => entry.status === 'submitted')) {
    history.unshift({ id: 'submitted', status: 'submitted', at: claim.submitted_at })
  }

  return (
    <div className="page max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <Link to={`/claims/${claim.id}`} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to claim
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="page-title">Track claim <span className="font-mono">{claim.claim_number}</span></h1>
            <StatusBadge status={shownStatus} />
          </div>
          <p className="page-subtitle">
            Submitted {formatDate(claim.submitted_at)} · {formatCurrency(claim.claim_amount)} claimed
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="secondary"><Link to={`/claims/${claim.id}`}><FileText className="w-4 h-4 mr-2" />Claim details</Link></Button>
          {isStaff && <Button asChild variant="primary"><Link to="/ai-decision"><Brain className="w-4 h-4 mr-2" />Automated Review</Link></Button>}
        </div>
      </div>

      {/* Progress */}
      <Card>
        <CardContent className="p-5 sm:p-6">
          <ol className="grid grid-cols-1 gap-3 sm:grid-cols-5 sm:gap-2" aria-label="Claim progress">
            {STEPS.map((step, index) => {
              const done = index < currentStep && !(isRejected && step.key === 'settlement')
              const current = index === currentStep
              const skipped = isRejected && index > currentStep
              const failed = current && isRejected
              const label = step.key === 'decision' && current
                ? (isRejected ? 'Not approved' : 'Approved')
                : step.label
              return (
                <li
                  key={step.key}
                  className="flex items-center gap-3 sm:flex-col sm:items-center sm:gap-2 sm:text-center"
                  aria-current={current ? 'step' : undefined}
                >
                  <span
                    className={clsx(
                      'flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
                      failed ? 'bg-red-600 text-white'
                        : current ? 'bg-primary text-white ring-4 ring-primary/20'
                          : done ? 'bg-emerald-600 text-white'
                            : 'bg-gray-100 text-gray-400'
                    )}
                  >
                    {failed ? <XCircle className="h-5 w-5" /> : done ? <CheckCircle2 className="h-5 w-5" /> : current ? <span className="text-sm font-bold">{index + 1}</span> : <Circle className="h-4 w-4" />}
                  </span>
                  <span className={clsx(
                    'text-sm',
                    current ? 'font-bold text-gray-900' : done ? 'font-medium text-gray-700' : 'text-gray-400',
                    skipped && 'line-through',
                  )}
                  >
                    {label}
                    {current && !isStaff && <span className="sr-only"> (current step)</span>}
                  </span>
                </li>
              )
            })}
          </ol>

          {nextText && (
            <div className={clsx(
              'mt-6 rounded-xl p-4 text-sm',
              isRejected ? 'bg-red-50 text-red-800' : status === 'closed' ? 'bg-emerald-50 text-emerald-800' : 'bg-blue-50 text-blue-900'
            )}
            >
              <p className="font-semibold">{isStaff ? 'Next action' : 'What happens next'}</p>
              <p className="mt-1">{nextText}</p>
              {isStaff && ['under_review', 'ai_assessment', 'investigation'].includes(status) && (
                <p className="mt-1 text-xs opacity-80">Current stage: {labelFor(CLAIM_STATUSES, status)}</p>
              )}
              {!isStaff && status === 'submitted' && (
                <Link to={`/claims/${claim.id}`} className="mt-2 inline-flex font-semibold text-primary hover:underline">Add photos or documents</Link>
              )}
              {!isStaff && isRejected && (
                <Link to="/support" className="mt-2 inline-flex items-center gap-1.5 font-semibold text-primary hover:underline"><Headphones className="h-4 w-4" />Contact support</Link>
              )}
            </div>
          )}

          <dl className="mt-5 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-gray-500">{isStaff ? 'Adjuster' : 'Your claims specialist'}</dt>
              <dd className="font-medium text-gray-900">{claim.assigned_adjuster_name || 'Not assigned yet'}</dd>
            </div>
            {isStaff && (
              <div>
                <dt className="text-gray-500">Investigator</dt>
                <dd className="font-medium text-gray-900">{claim.assigned_investigator_name || 'None'}</dd>
              </div>
            )}
            {!isStaff && (
              <div>
                <dt className="text-gray-500">Policy</dt>
                <dd className="font-medium text-gray-900">{claim.policy_number || '—'}</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* History */}
      <Card>
        <CardContent className="p-5 sm:p-6">
          <h2 className="text-base font-semibold text-gray-900">History</h2>
          <ol className="mt-4 space-y-4 border-l-2 border-gray-100 pl-5">
            {[...history].reverse().map((entry) => (
              <li key={entry.id} className="relative">
                <span className="absolute -left-[27px] top-1 h-3 w-3 rounded-full border-2 border-white bg-primary" aria-hidden="true" />
                <p className="text-sm font-semibold text-gray-900">{labelFor(CLAIM_STATUSES, entry.status)}</p>
                <p className="text-xs text-gray-500">
                  {formatDateTime(entry.at)}{entry.by ? ` · ${entry.by}` : ''}
                </p>
                {entry.reason && <p className="mt-1 text-sm text-gray-600">{entry.reason}</p>}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
    </div>
  )
}
