import { useState, useEffect } from 'react'
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
import { mockSettlements, mockSettlementStats } from '../../data/settlements'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import { Modal } from '../../components/ui/Modal'
import { formatCurrency, formatDate } from '../../utils/helpers'

export function SettlementDashboard() {
  const [settlements, setSettlements] = useState(mockSettlements)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [payModalOpen, setPayModalOpen] = useState(false)
  const [activeSettlementForPay, setActiveSettlementForPay] = useState(null)

  const stats = mockSettlementStats

  const handleProcessPayment = (settlement) => {
    setActiveSettlementForPay(settlement)
    setPayModalOpen(true)
  }

  const confirmPayment = () => {
    if (!activeSettlementForPay) return
    setSettlements((prev) =>
      prev.map((s) =>
        s.id === activeSettlementForPay.id
          ? {
              ...s,
              paymentStatus: 'completed',
              paidAt: new Date().toISOString(),
              paymentReference: 'TXN-' + Math.floor(100000 + Math.random() * 900000),
            }
          : s
      )
    )
    setPayModalOpen(false)
    setActiveSettlementForPay(null)
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
            Authorize financial claim settlements, calculate deductibles, and execute electronic disbursements
          </p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Export Ledger
          </Button>
          <Link to="/claims">
            <Button variant="primary">
              Browse Claims
            </Button>
          </Link>
        </div>
      </div>

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
            <span className="text-xs text-gray-500">Direct ACH / Wire</span>
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
                { value: 'approved', label: 'Approved' },
                { value: 'paid', label: 'Paid' },
                { value: 'under-review', label: 'Under Review' },
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
                        s.paymentStatus === 'completed' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      )}>
                        {s.paymentStatus === 'completed' ? 'Disbursed' : 'Pending ACH'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-mono text-gray-600">
                        {s.paymentReference || 'Unassigned'}
                      </span>
                    </TableCell>
                    <TableCell align="right">
                      {s.paymentStatus === 'pending' ? (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleProcessPayment(s)}
                        >
                          Disburse
                        </Button>
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
              Disbursement will initiate direct ACH transfer to policyholder's verified bank account on file.
            </p>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="secondary" onClick={() => setPayModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={confirmPayment}>
                Confirm Payout Transfer
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default SettlementDashboard
