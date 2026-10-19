import { useState, useEffect, useMemo, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Gavel,
  DollarSign,
  CheckCircle2,
  Clock,
  Search,
  Filter,
  CreditCard,
  Building,
  ArrowRight,
  Download,
  AlertCircle,
} from 'lucide-react'
import { clsx } from 'clsx'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import { Modal } from '../../components/ui/Modal'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { settlementService, claimService, policyService } from '../../services'
import { useAuth } from '../../context/useAuth'

export function SettlementDashboard() {
  const { user } = useAuth()
  const canProcessPayouts = ['employee', 'admin'].includes(user?.role)
  const [settlements, setSettlements] = useState([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [payModalOpen, setPayModalOpen] = useState(false)
  const [activeSettlementForPay, setActiveSettlementForPay] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [processingPayment, setProcessingPayment] = useState(false)
  const [payoutReference, setPayoutReference] = useState('')
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [approvalTarget, setApprovalTarget] = useState(null)
  const [approvedAmount, setApprovedAmount] = useState('')
  const [eligibleClaims, setEligibleClaims] = useState([])
  const [policies, setPolicies] = useState([])
  const [settlementDraft, setSettlementDraft] = useState({ claim: '', estimated_amount: '', deductible: '', approved_amount: '' })

  const mapSettlement = (s) => ({
    id: s.id,
    settlementNumber: s.settlement_number,
    claimId: s.claim,
    claimNumber: s.claim_number,
    customerId: s.customer,
    customerName: s.customer_name || s.customer_email || '—',
    customerEmail: s.customer_email,
    estimatedAmount: Number(s.estimated_amount) || 0,
    deductible: Number(s.deductible) || 0,
    depreciationAmount: Number(s.depreciation_amount) || 0,
    assetAgeYears: Number(s.asset_age_years) || 0,
    zeroDepreciationApplied: Boolean(s.zero_depreciation_applied),
    approvedAmount: Number(s.approved_amount) || 0,
    status: s.status,
    paymentStatus: s.payment_status,
    paymentMethod: s.payment_method,
    paymentReference: s.payment_reference || s.payments?.[0]?.payment_reference || s.payments?.[0]?.payment_number || null,
    latestPaymentId: s.payments?.[0]?.id || null,
    approvedBy: s.approved_by_name || '—',
    approvedAt: s.approved_at,
    paidBy: s.paid_by_name || null,
    paidAt: s.paid_at,
    notes: s.notes || '',
    timeline: s.timeline || [],
    payments: s.payments || [],
  })

  const loadSettlements = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await settlementService.getSettlements()
      const items = Array.isArray(response) ? response : response.results || []
      setSettlements(items.map(mapSettlement))
    } catch (err) {
      console.error('Failed to load settlements:', err)
      setError(err.message || 'Failed to load settlements. Please try again.')
      setSettlements([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSettlements()
  }, [loadSettlements])

  const stats = useMemo(() => ({
    totalSettlements: settlements.length,
    totalApprovedAmount: settlements.reduce((sum, s) => sum + (Number(s.approvedAmount) || 0), 0),
    totalPaidAmount: settlements
      .filter((s) => s.paymentStatus === 'completed')
      .reduce((sum, s) => sum + (Number(s.approvedAmount) || 0), 0),
    pendingSettlements: settlements.filter((s) => s.paymentStatus === 'pending').length,
  }), [settlements])

  const handleProcessPayment = (settlement) => {
    setActiveSettlementForPay(settlement)
    setPayoutReference('')
    setPayModalOpen(true)
  }

  const confirmPayment = async () => {
    if (!activeSettlementForPay) return
    setProcessingPayment(true)
    try {
      await settlementService.processPayment(activeSettlementForPay.id, {
        payment_method: activeSettlementForPay.paymentMethod || 'bank_transfer',
        payment_reference: payoutReference.trim(),
      })
      setPayModalOpen(false)
      setActiveSettlementForPay(null)
      await loadSettlements()
    } catch (err) {
      console.error('Failed to process payment:', err)
      setError(err.message || 'Failed to process payment. Please try again.')
    } finally {
      setProcessingPayment(false)
    }
  }

  const markPayoutComplete = async (settlement) => {
    if (!settlement.latestPaymentId) {
      setError('The initiated payment record could not be found. Reload and try again.')
      return
    }
    if (!window.confirm('Confirm that this payment was completed outside InsureX? This only records the completion; it does not transfer funds.')) return
    setProcessingPayment(true)
    setError(null)
    try {
      await settlementService.completePayment(settlement.id, settlement.latestPaymentId)
      await loadSettlements()
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Failed to record the completed payout.')
    } finally {
      setProcessingPayment(false)
    }
  }

  const openCreateSettlement = async () => {
    setError(null)
    setCreateModalOpen(true)
    try {
      const [claimResponse, policyResponse] = await Promise.all([
        claimService.getClaims({ status: 'approved' }),
        policyService.getPolicies(),
      ])
      const claims = Array.isArray(claimResponse) ? claimResponse : claimResponse.results || []
      const policyItems = Array.isArray(policyResponse) ? policyResponse : policyResponse.results || []
      const existingClaimIds = new Set(settlements.map((settlement) => Number(settlement.claimId)))
      setEligibleClaims(claims.filter((claim) => !existingClaimIds.has(Number(claim.id))))
      setPolicies(policyItems)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load claims and policies for settlement setup.')
    }
  }

  const selectSettlementClaim = async (claimId) => {
    const claim = eligibleClaims.find((item) => String(item.id) === String(claimId))
    let policy = policies.find((item) => Number(item.id) === Number(claim?.policy))
    if (!policy && claim?.policy) {
      try {
        policy = await policyService.getPolicy(claim.policy)
      } catch (err) {
        setError(err.response?.data?.detail || 'Could not load the claim policy deductible.')
      }
    }
    const estimate = Number(claim?.estimated_repair_cost || claim?.ai_assessment?.predicted_repair_cost || claim?.claim_amount || 0)
    const deductible = Number(policy?.deductible || 0)
    setSettlementDraft({
      claim: claimId,
      estimated_amount: String(estimate),
      deductible: String(deductible),
      approved_amount: String(Math.max(0, estimate - deductible)),
    })
  }

  const createSettlement = async (event) => {
    event.preventDefault()
    setProcessingPayment(true)
    setError(null)
    try {
      await settlementService.createSettlement({
        claim: Number(settlementDraft.claim),
        estimated_amount: Number(settlementDraft.estimated_amount),
        deductible: Number(settlementDraft.deductible),
        approved_amount: Number(settlementDraft.approved_amount),
      })
      setCreateModalOpen(false)
      setSettlementDraft({ claim: '', estimated_amount: '', deductible: '', approved_amount: '' })
      await loadSettlements()
    } catch (err) {
      const data = err.response?.data
      setError(data?.detail || data?.error || 'Could not create the settlement record.')
    } finally {
      setProcessingPayment(false)
    }
  }

  const approveSettlement = async (event) => {
    event.preventDefault()
    if (!approvalTarget) return
    setProcessingPayment(true)
    setError(null)
    try {
      await settlementService.approveSettlement(approvalTarget.id, { approved_amount: Number(approvedAmount) })
      setApprovalTarget(null)
      await loadSettlements()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not approve this settlement.')
    } finally {
      setProcessingPayment(false)
    }
  }

  const rejectSettlement = async (settlement) => {
    if (!window.confirm(`Reject settlement ${settlement.settlementNumber}?`)) return
    setError(null)
    try {
      await settlementService.rejectSettlement(settlement.id)
      await loadSettlements()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not reject this settlement.')
    }
  }

  const filtered = settlements.filter((s) => {
    const q = search.toLowerCase()
    const matchesSearch =
      s.settlementNumber.toLowerCase().includes(q) ||
      s.claimNumber.toLowerCase().includes(q) ||
      s.customerName.toLowerCase().includes(q)
    const matchesStatus = !statusFilter || s.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const handleExport = () => {
    const rows = [
      ['Settlement ID', 'Claim Ref', 'Customer', 'Estimated Amount', 'Deductible', 'Approved Amount', 'Status', 'Payment Status', 'Reference'],
      ...filtered.map((s) => [
        s.settlementNumber,
        s.claimNumber,
        s.customerName,
        s.estimatedAmount,
        s.deductible,
        s.approvedAmount,
        s.status,
        s.paymentStatus,
        s.paymentReference || '',
      ]),
    ]
    const csv = rows
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
      .join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `settlements-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <Gavel className="w-3.5 h-3.5 text-emerald-600" />
              Claims Adjudication & Payout
            </span>
          </div>
          <h1 className="page-title">Settlement Management Dashboard</h1>
          <p className="page-subtitle">
            Review approved claim settlements, calculate deductibles, and record payment status. InsureX does not transfer funds.
          </p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={openCreateSettlement}>
            Create Settlement
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" />
            Export Ledger
          </Button>
          <Button asChild variant="primary"><Link to="/claims">Browse Claims</Link></Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={loadSettlements}>Retry</Button>
        </div>
      )}

      {loading && settlements.length === 0 && (
        <div className="p-8 text-center text-sm text-gray-400">Loading settlements...</div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Settlements</p>
            <p className="text-2xl font-black text-gray-900 mt-1">{stats.totalSettlements}</p>
            <span className="text-xs text-gray-500">Processed cases</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Gavel className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Approved Amount</p>
            <p className="text-2xl font-black text-emerald-600 mt-1">{formatCurrency(stats.totalApprovedAmount)}</p>
            <span className="text-xs text-emerald-700">Net of Deductibles</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <DollarSign className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Disbursed (Paid)</p>
            <p className="text-2xl font-black text-primary mt-1">{formatCurrency(stats.totalPaidAmount)}</p>
            <span className="text-xs text-gray-500">Recorded payment completions</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <CreditCard className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Pending Payout</p>
            <p className="text-2xl font-black text-amber-600 mt-1">{stats.pendingSettlements}</p>
            <span className="text-xs text-amber-600">Awaiting clearance</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Settlements Table */}
      <Card>
        <CardHeader
          title="Settlement Records & Deductible Reconciliation"
          subtitle="Itemized approved payouts after policy deductible subtraction"
        />
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search settlement #, claim ID, or customer..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              options={[
                { value: '', label: 'All Settlement Statuses' },
                { value: 'calculated', label: 'Calculated' },
                { value: 'under_review', label: 'Under Review' },
                { value: 'approved', label: 'Approved' },
                { value: 'paid', label: 'Paid' },
                { value: 'under_review', label: 'Under Review' },
              ]}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-56"
            />
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Settlement ID</TableHead>
                  <TableHead>Claim Ref</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Estimated Amount</TableHead>
                  <TableHead>Deductible</TableHead>
                  <TableHead>Depreciation</TableHead>
                  <TableHead>Approved Amount</TableHead>
                  <TableHead>Settlement Status</TableHead>
                  <TableHead>Payment Status</TableHead>
                  <TableHead>Reference</TableHead>
                  <TableHead className="w-32 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((s) => (
                  <TableRow key={s.id} hover>
                    <TableCell>
                      <span className="font-mono font-bold text-gray-900">{s.settlementNumber}</span>
                    </TableCell>
                    <TableCell>
                      <Link to={`/claims/${s.claimId}`} className="font-mono text-primary hover:underline font-semibold">
                        {s.claimNumber}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium text-gray-900">{s.customerName}</div>
                      <div className="text-xs text-gray-400">By {s.approvedBy}</div>
                    </TableCell>
                    <TableCell className="text-gray-600 font-medium">
                      {formatCurrency(s.estimatedAmount)}
                    </TableCell>
                    <TableCell className="text-red-600 font-medium">
                      -{formatCurrency(s.deductible)}
                    </TableCell>
                    <TableCell className="text-amber-700 font-medium">
                      {s.zeroDepreciationApplied ? 'Waived (add-on)' : `-${formatCurrency(s.depreciationAmount)}`}
                    </TableCell>
                    <TableCell className="text-emerald-700 font-extrabold text-base">
                      {formatCurrency(s.approvedAmount)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={s.status === 'paid' ? 'success' : 'primary'}>
                        {s.status.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className={clsx(
                        'text-xs font-semibold px-2 py-0.5 rounded-full inline-block',
                        s.paymentStatus === 'completed'
                          ? 'bg-emerald-100 text-emerald-800'
                          : s.paymentStatus === 'processing'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-amber-100 text-amber-800'
                      )}>
                        {s.paymentStatus === 'completed'
                          ? 'Disbursed'
                          : s.paymentStatus === 'processing'
                            ? 'Processing'
                            : 'Pending ACH'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-mono text-gray-600">
                        {s.paymentReference || 'Unassigned'}
                      </span>
                    </TableCell>
                    <TableCell align="right">
                      {['calculated', 'under_review'].includes(s.status) ? (
                        <div className="flex justify-end gap-1">
                          <Button variant="primary" size="sm" disabled={processingPayment} onClick={() => { setApprovalTarget(s); setApprovedAmount(String(s.approvedAmount || Math.max(0, s.estimatedAmount - s.deductible))) }}>Review</Button>
                          <Button variant="outline" size="sm" onClick={() => rejectSettlement(s)}>Reject</Button>
                        </div>
                      ) : s.paymentStatus === 'pending' ? (
                        canProcessPayouts ? (
                          <Button
                            variant="primary"
                            size="sm"
                            disabled={processingPayment}
                            onClick={() => handleProcessPayment(s)}
                          >
                            Record Payout
                          </Button>
                        ) : <span className="text-xs text-amber-700">Pending</span>
                      ) : s.paymentStatus === 'processing' ? (
                        canProcessPayouts ? (
                          <Button variant="outline" size="sm" disabled={processingPayment} onClick={() => markPayoutComplete(s)}>
                            Record Paid
                          </Button>
                        ) : (
                          <span className="text-xs text-blue-600 font-semibold flex items-center justify-end gap-1">
                            <Clock className="w-3.5 h-3.5" />
                            Processing
                          </span>
                        )
                      ) : (
                        <span className="text-xs text-emerald-600 font-semibold flex items-center justify-end gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Paid
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {createModalOpen && (
        <Modal isOpen onClose={() => setCreateModalOpen(false)} title="Create Settlement Record" size="md">
          <form onSubmit={createSettlement} className="space-y-4">
            <p className="text-sm text-gray-600">Select an approved claim. Amounts are prefilled from its model estimate, claim amount, and policy deductible; review them before saving.</p>
            <Select
              label="Approved claim"
              value={settlementDraft.claim}
              onChange={(event) => selectSettlementClaim(event.target.value)}
              options={eligibleClaims.map((claim) => ({ value: String(claim.id), label: `${claim.claim_number} — ${claim.customer_name || claim.customer_email}`}))}
              placeholder="Select a claim"
              required
            />
            {eligibleClaims.length === 0 && <p className="text-sm text-amber-700">No eligible approved claims without an existing settlement were found.</p>}
            <Input label="Estimated amount" type="number" min="0" step="0.01" required value={settlementDraft.estimated_amount} onChange={(event) => setSettlementDraft((draft) => ({ ...draft, estimated_amount: event.target.value }))} />
            <Input label="Policy deductible" type="number" min="0" step="0.01" required value={settlementDraft.deductible} onChange={(event) => setSettlementDraft((draft) => ({ ...draft, deductible: event.target.value }))} />
            <Input label="Proposed net settlement" type="number" min="0" step="0.01" required value={settlementDraft.approved_amount} onChange={(event) => setSettlementDraft((draft) => ({ ...draft, approved_amount: event.target.value }))} />
            <div className="flex justify-end gap-2 pt-3 border-t">
              <Button type="button" variant="secondary" onClick={() => setCreateModalOpen(false)}>Cancel</Button>
              <Button type="submit" variant="primary" loading={processingPayment} disabled={processingPayment || !settlementDraft.claim}>Save for Review</Button>
            </div>
          </form>
        </Modal>
      )}

      {approvalTarget && (
        <Modal isOpen onClose={() => setApprovalTarget(null)} title={`Review ${approvalTarget.settlementNumber}`} size="md">
          <form onSubmit={approveSettlement} className="space-y-4">
            <p className="text-sm text-gray-600">Confirm the amount as an authorized adjuster. Saving approval does not trigger a payment.</p>
            <Input label="Approved amount" type="number" min="0" step="0.01" required value={approvedAmount} onChange={(event) => setApprovedAmount(event.target.value)} />
            <div className="flex justify-end gap-2 pt-3 border-t">
              <Button type="button" variant="secondary" onClick={() => setApprovalTarget(null)}>Cancel</Button>
              <Button type="submit" variant="primary" loading={processingPayment} disabled={processingPayment}>Approve Settlement</Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Disburse Payment Modal */}
      {payModalOpen && activeSettlementForPay && (
        <Modal
          isOpen={payModalOpen}
          onClose={() => setPayModalOpen(false)}
          title={`Execute Settlement Disbursement: ${activeSettlementForPay.settlementNumber}`}
          size="md"
        >
          <div className="space-y-4">
            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 text-sm space-y-1.5">
              <div className="flex justify-between">
                <span className="text-emerald-800 font-medium">Payee:</span>
                <strong className="text-emerald-950">{activeSettlementForPay.customerName}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-emerald-800 font-medium">Claim Amount:</span>
                <span className="text-emerald-950">{formatCurrency(activeSettlementForPay.estimatedAmount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-emerald-800 font-medium">Deductible Withheld:</span>
                <span className="text-red-700">-{formatCurrency(activeSettlementForPay.deductible)}</span>
              </div>
              <div className="flex justify-between text-base font-bold pt-2 border-t border-emerald-200">
                <span className="text-emerald-900">Total Net Disbursement:</span>
                <span className="text-emerald-950">{formatCurrency(activeSettlementForPay.approvedAmount)}</span>
              </div>
            </div>

            <p className="text-xs text-gray-500">
              This records a payout initiation in InsureX. It does not send funds. Enter the external transfer reference after arranging payment, then record completion once the transfer clears.
            </p>

            <Input
              label="External transfer reference (optional)"
              value={payoutReference}
              onChange={(event) => setPayoutReference(event.target.value)}
              placeholder="Bank or payment provider reference"
            />

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="secondary" onClick={() => setPayModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={confirmPayment}>
                Record Payout Initiation
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default SettlementDashboard
