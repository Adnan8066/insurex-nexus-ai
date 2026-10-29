import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardList, RefreshCw } from 'lucide-react'
import { policyService } from '../../services'
import { formatApiError } from '../../services/api'
import { POLICY_TYPES, labelFor } from '../../constants/domain'
import { Card, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { ConfirmDialog, Modal } from '../../components/ui/Modal'
import { Textarea } from '../../components/forms/FormFields'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/tables/DataTable'
import { useToast } from '../../components/ui/toastHooks'
import { useAuth } from '../../context/useAuth'
import { formatCurrency, formatDate } from '../../utils/helpers'

const STATUS_TABS = [
  { value: 'quoted', label: 'Waiting for review' },
  { value: 'bound', label: 'Issued' },
  { value: 'declined', label: 'Declined' },
]
const STATUS_BADGES = { quoted: 'warning', bound: 'success', declined: 'neutral' }

// Review queue: each customer request is assigned to one employee, who issues it
// as an active policy or declines it with a note. Admins see every request.
export function PolicyRequests() {
  const toast = useToast()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [statusFilter, setStatusFilter] = useState('quoted')
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [issuing, setIssuing] = useState(null)
  const [declining, setDeclining] = useState(null)
  const [declineNote, setDeclineNote] = useState('')
  const [actionError, setActionError] = useState('')
  const [working, setWorking] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await policyService.getPolicyApplications({ status: statusFilter })
      setApplications(Array.isArray(result) ? result : result.results || [])
    } catch (err) {
      setError(formatApiError(err, 'Could not load policy requests.'))
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => { load() }, [load])

  const closeDialogs = () => {
    setIssuing(null)
    setDeclining(null)
    setDeclineNote('')
    setActionError('')
  }

  const issuePolicy = async () => {
    setWorking(true)
    setActionError('')
    try {
      const policy = await policyService.bindPolicyQuote(issuing.id)
      toast.success(`Policy ${policy.policy_number} issued to ${issuing.customer_name}.`)
      closeDialogs()
      await load()
    } catch (err) {
      setActionError(formatApiError(err, 'Could not issue this policy.'))
    } finally {
      setWorking(false)
    }
  }

  const declineRequest = async () => {
    setWorking(true)
    setActionError('')
    try {
      await policyService.declinePolicyApplication(declining.id, declineNote)
      toast.success(`Request from ${declining.customer_name} declined.`)
      closeDialogs()
      await load()
    } catch (err) {
      setActionError(formatApiError(err, 'Could not decline this request.'))
    } finally {
      setWorking(false)
    }
  }

  return (
    <div className="page mx-auto max-w-7xl space-y-6">
      <div className="page-header flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-50 p-3 text-blue-700"><ClipboardList className="h-6 w-6" /></div>
          <div>
            <h1 className="page-title">Policy Requests</h1>
            <p className="page-subtitle">
              {isAdmin
                ? 'Customer requests are assigned automatically to the least-busy employee'
                : 'Requests assigned to you. Review the quote and issue the policy'}
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" /> Refresh
        </Button>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Request status">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={statusFilter === tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${statusFilter === tab.value ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 ring-1 ring-gray-200 hover:bg-gray-50'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <p className="p-8 text-center text-sm text-gray-500">Loading requests…</p>
          ) : applications.length === 0 ? (
            <EmptyState title="No requests here" description={statusFilter === 'quoted' ? 'New customer requests will appear here.' : 'Nothing to show for this status yet.'} />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Requested</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Assigned to</TableHead>
                    <TableHead>Vehicle</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead align="right">Value covered</TableHead>
                    <TableHead align="right">Premium</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead align="right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {applications.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <div className="text-sm text-gray-900">{formatDate(item.created_at)}</div>
                        <div className="text-xs text-gray-500">{item.requested_by_customer ? 'Customer request' : 'Staff quote'}</div>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-gray-900">{item.customer_name}</div>
                        <div className="text-xs text-gray-500">{item.customer_email}</div>
                      </TableCell>
                      <TableCell className="text-sm">{item.assigned_to_name || <span className="text-gray-400">Unassigned</span>}</TableCell>
                      <TableCell className="text-sm">{item.vehicle_label || '—'}</TableCell>
                      <TableCell>
                        <div className="text-sm text-gray-900">{item.policy_terms?.coverage?.policy_plan?.name || labelFor(POLICY_TYPES, item.policy_type)}</div>
                        <div className="text-xs text-gray-500">Risk score {Number(item.risk_score)} · deductible {formatCurrency(Number(item.deductible))}</div>
                      </TableCell>
                      <TableCell align="right">{formatCurrency(Number(item.coverage_limit))}</TableCell>
                      <TableCell align="right" className="font-semibold">{formatCurrency(Number(item.quoted_premium))}</TableCell>
                      <TableCell>
                        <Badge variant={STATUS_BADGES[item.status] || 'neutral'}>{STATUS_TABS.find((tab) => tab.value === item.status)?.label || item.status}</Badge>
                        {item.bound_policy_number && (
                          <Link to={`/policies/${item.bound_policy_number}`} className="mt-1 block text-xs text-primary hover:underline">{item.bound_policy_number}</Link>
                        )}
                        {item.review_note && <p className="mt-1 max-w-48 text-xs text-gray-500">{item.review_note}</p>}
                      </TableCell>
                      <TableCell align="right">
                        {item.status === 'quoted' ? (
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="primary" onClick={() => setIssuing(item)}>Issue policy</Button>
                            <Button size="sm" variant="outline" onClick={() => setDeclining(item)}>Decline</Button>
                          </div>
                        ) : (
                          <span className="text-xs text-gray-500">{item.reviewed_by_name ? `by ${item.reviewed_by_name}` : ''}</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        isOpen={Boolean(issuing)}
        onClose={closeDialogs}
        onConfirm={issuePolicy}
        title="Issue this policy?"
        message={issuing ? `${issuing.customer_name}'s ${issuing.vehicle_label || 'vehicle'} will be insured from ${formatDate(issuing.policy_terms?.start_date)} at an annual premium of ${formatCurrency(Number(issuing.quoted_premium))}. The customer will be notified.` : ''}
        confirmText="Issue policy"
        variant="primary"
        loading={working}
        error={actionError}
      />

      <Modal
        isOpen={Boolean(declining)}
        onClose={closeDialogs}
        title="Decline this request?"
        description={declining ? `${declining.customer_name} will be notified. Add a short reason they can act on.` : ''}
        size="sm"
        footer={(
          <>
            <button type="button" className="btn btn-secondary" onClick={closeDialogs} disabled={working}>Cancel</button>
            <button type="button" className="btn btn-danger" onClick={declineRequest} disabled={working}>{working ? 'Declining…' : 'Decline request'}</button>
          </>
        )}
      >
        <Textarea
          label="Reason (optional)"
          value={declineNote}
          onChange={(event) => setDeclineNote(event.target.value)}
          maxLength={2000}
          rows={3}
          placeholder="e.g. Please upload the vehicle's registration certificate first."
        />
        {actionError && <p className="mt-3 text-sm text-red-600" role="alert">{actionError}</p>}
      </Modal>
    </div>
  )
}

export default PolicyRequests
