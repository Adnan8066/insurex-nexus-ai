import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardList } from 'lucide-react'
import { policyService } from '../../services'
import { formatApiError } from '../../services/api'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { Alert } from '../../components/ui/Alert'
import { LoadingState } from '../../components/ui/LoadingSpinner'

const STATUS = {
  quoted: { label: 'Waiting for review', variant: 'warning', detail: 'Your request and estimate are with the insurance team for review.' },
  bound: { label: 'Policy issued', variant: 'success', detail: 'Your request was approved and converted into a policy.' },
  declined: { label: 'Declined', variant: 'danger', detail: 'The insurance team could not approve this request.' },
}

export function MyPolicyRequests() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const result = await policyService.getPolicyApplications()
        const items = Array.isArray(result) ? result : result.results || []
        if (!cancelled) setRequests(items)
      } catch (err) {
        if (!cancelled) setError(formatApiError(err, 'Could not load your policy requests.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  return (
    <div className="page mx-auto max-w-5xl space-y-6">
      <div className="page-header flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-50 p-3 text-blue-700"><ClipboardList className="h-6 w-6" /></div>
          <div>
            <h1 className="page-title">My policy requests</h1>
            <p className="page-subtitle">Check the review status of each policy request you have sent.</p>
          </div>
        </div>
        <Button asChild variant="outline"><Link to="/policies/plans">Compare plans</Link></Button>
      </div>

      {error && <Alert>{error}</Alert>}
      {loading ? <LoadingState label="Loading your policy requests…" /> : requests.length === 0 ? (
        <EmptyState
          icon={<ClipboardList className="h-12 w-12" />}
          title="No policy requests yet"
          description="When you request a quote for a vehicle, you can follow its review status here."
          action={<Button asChild><Link to="/vehicles">View my vehicles</Link></Button>}
        />
      ) : (
        <div className="space-y-4">
          {requests.map((request) => {
            const status = STATUS[request.status] || STATUS.quoted
            const plan = request.policy_terms?.coverage?.policy_plan?.name || request.policy_type
            const coverDates = request.policy_terms || {}
            return (
              <Card key={request.id}>
                <CardHeader
                  title={plan}
                  subtitle={`${request.vehicle_label || 'Vehicle'} · Requested ${formatDate(request.created_at)}`}
                  action={<Badge variant={status.variant}>{status.label}</Badge>}
                />
                <CardContent className="space-y-3">
                  <p className="text-sm text-gray-700">{status.detail}</p>
                  <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
                    <div><dt className="text-gray-500">Estimated annual premium</dt><dd className="font-semibold text-gray-900">{formatCurrency(Number(request.quoted_premium))}</dd></div>
                    <div><dt className="text-gray-500">Requested cover period</dt><dd className="font-medium text-gray-900">{formatDate(coverDates.start_date)} – {formatDate(coverDates.end_date)}</dd></div>
                    <div><dt className="text-gray-500">Deductible</dt><dd className="font-medium text-gray-900">{formatCurrency(Number(request.deductible))}</dd></div>
                  </dl>
                  {request.review_note && <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700">Review note: {request.review_note}</p>}
                  {request.bound_policy && (
                    <Button asChild size="sm"><Link to={`/policies/${request.bound_policy}`}>View issued policy{request.bound_policy_number ? ` ${request.bound_policy_number}` : ''}</Link></Button>
                  )}
                  <p className="text-xs text-gray-500">The premium shown is an estimate until the policy is reviewed and issued.</p>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default MyPolicyRequests
