import { useState, useEffect, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Briefcase,
  Search,
  Plus,
  Calendar,
  Car,
  Clock,
  Eye,
  ShieldCheck,
  TrendingUp,
  Trash2,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { claimService } from '../../services'
import { formatApiError } from '../../services/api'
import { canDeleteClaim } from '../../utils/claimPermissions'
import { CLAIM_STATUSES, PENDING_CLAIM_STATUSES, INCIDENT_TYPES, labelFor } from '../../constants/domain'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TablePagination } from '../../components/tables/DataTable'
import { EmptyState } from '../../components/ui/EmptyState'
import { ConfirmDialog } from '../../components/ui/Modal'

const incidentTypes = [
  { value: '', label: 'All incident types' },
  ...INCIDENT_TYPES.map(({ value, label }) => ({ value, label })),
]

const statusOptions = [
  { value: '', label: 'All statuses' },
  { value: 'pending', label: 'All pending' },
  ...CLAIM_STATUSES,
]

export function ClaimList() {
  const { user } = useAuth()
  const canViewAI = ['admin', 'employee', 'investigator'].includes(user?.role)
  const canSubmitClaim = ['customer', 'employee', 'admin'].includes(user?.role)
  const [searchParams] = useSearchParams()
  const statusParam = searchParams.get('status')

  const [loading, setLoading] = useState(true)
  const [claims, setClaims] = useState([])
  const [filteredClaims, setFilteredClaims] = useState([])
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState(() => {
    if (statusParam === 'ai_assessment' && !canViewAI) return 'under_review'
    return statusOptions.some((option) => option.value === statusParam) ? statusParam : ''
  })
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [sortConfig, setSortConfig] = useState({ key: 'submittedAt', direction: 'desc' })
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [error, setError] = useState('')

  const fetchClaims = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await claimService.getClaims()
      const results = Array.isArray(res) ? res : (res.results || [])
      const mapped = results.map((c) => ({
        id: c.id,
        claimNumber: c.claim_number,
        customer: c.customer,
        customerName: c.customer_name,
        customerEmail: c.customer_email,
        policy: c.policy,
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
        numberOfVehicles: c.number_of_vehicles,
        injuries: c.injuries,
        propertyDamage: c.property_damage,
        witnesses: c.witnesses,
        policeReport: c.police_report,
        claimAmount: Number(c.claim_amount) || 0,
        description: c.description,
        status: !canViewAI && c.status === 'ai_assessment' ? 'under_review' : c.status,
        priority: c.priority,
        assignedAdjuster: c.assigned_adjuster_name,
        assignedInvestigator: c.assigned_investigator_name,
        aiAssessment: c.ai_assessment ? {
          ...c.ai_assessment,
          claimPriority: c.ai_assessment.priority || c.ai_assessment.claim_priority,
        } : null,
        fraudRiskScore: c.fraud_risk_score,
        totalLossProbability: c.total_loss_probability,
        submittedAt: c.submitted_at,
        updatedAt: c.updated_at,
        closedAt: c.closed_at,
      }))
      setClaims(mapped)
      setFilteredClaims(mapped)
    } catch (err) {
      setError(formatApiError(err, 'Failed to load claims'))
      setClaims([])
      setFilteredClaims([])
    } finally {
      setLoading(false)
    }
  }, [canViewAI])

  useEffect(() => {
    fetchClaims()
  }, [fetchClaims])

  useEffect(() => {
    let result = [...claims]

    if (search) {
      const q = search.toLowerCase()
      result = result.filter(
        (c) =>
          (c.claimNumber || '').toLowerCase().includes(q) ||
          (c.customerName || '').toLowerCase().includes(q) ||
          (c.policyNumber || '').toLowerCase().includes(q) ||
          (c.vehicle && `${c.vehicle.make || ''} ${c.vehicle.model || ''}`.toLowerCase().includes(q)) ||
          (c.location || '').toLowerCase().includes(q)
      )
    }

    if (typeFilter) {
      result = result.filter((c) => c.incidentType === typeFilter)
    }

    if (statusFilter) {
      if (statusFilter === 'pending') {
        result = result.filter((c) => PENDING_CLAIM_STATUSES.includes(c.status))
      } else {
        result = result.filter((c) => c.status === statusFilter)
      }
    }

    result.sort((a, b) => {
      let aVal = a[sortConfig.key]
      let bVal = b[sortConfig.key]
      if (aVal == null) return 1
      if (bVal == null) return -1
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })

    setFilteredClaims(result)
    setCurrentPage(1)
  }, [search, typeFilter, statusFilter, sortConfig, claims])

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await claimService.deleteClaim(deleteTarget.id)
      setClaims((prev) => prev.filter((c) => c.id !== deleteTarget.id))
      setFilteredClaims((prev) => prev.filter((c) => c.id !== deleteTarget.id))
      setDeleteTarget(null)
      setDeleteError('')
    } catch (err) {
      setDeleteError(formatApiError(err, 'Failed to delete claim'))
    } finally {
      setDeleting(false)
    }
  }

  const paginatedClaims = filteredClaims.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  const stats = {
    total: claims.length,
    pending: claims.filter((c) => PENDING_CLAIM_STATUSES.includes(c.status)).length,
    approved: claims.filter((c) => c.status === 'approved').length,
    closed: claims.filter((c) => c.status === 'closed').length,
  }

  if (loading) {
    return (
      <div className="page animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 rounded w-48 mb-2"></div>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl"></div>
          ))}
        </div>
        <div className="h-96 bg-gray-200 rounded-xl"></div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Claims</h1>
          <p className="page-subtitle">{canViewAI ? 'Review and track every claim from submission to settlement' : 'See and track the claims you have made'}</p>
        </div>
        <div className="flex gap-2">
          {canSubmitClaim && <Button asChild variant="primary"><Link to="/claims/new"><Plus className="w-4 h-4 mr-2" />Submit Claim</Link></Button>}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase">Total Claims</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{stats.total}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <Briefcase className="w-5 h-5" />
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase">Pending Review</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{stats.pending}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase">Approved</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{stats.approved}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase">Settled / Closed</p>
            <p className="text-2xl font-bold text-gray-700 mt-1">{stats.closed}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center">
            <TrendingUp className="w-5 h-5" />
          </div>
        </div>
      </div>

      <Card>
        <CardContent className="p-6">
          {/* Filters Bar */}
          <div className="flex flex-col md:flex-row gap-3 mb-6">
            <div className="flex-1">
              <Input
                placeholder="Search by claim ID, customer, vehicle, location..."
                aria-label="Search claims"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                leftIcon={<Search className="w-4 h-4 text-gray-400" />}
              />
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Select
                options={incidentTypes}
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                aria-label="Filter by incident type"
                className="sm:w-48"
              />
              <Select
                options={canViewAI ? statusOptions : statusOptions.filter((option) => option.value !== 'ai_assessment')}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter by status"
                className="sm:w-48"
              />
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            {filteredClaims.length > 0 ? (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead onClick={() => handleSort('claimNumber')} className="cursor-pointer">
                        Claim ID
                      </TableHead>
                      <TableHead onClick={() => handleSort('customerName')} className="cursor-pointer">
                        Customer
                      </TableHead>
                      <TableHead>Vehicle</TableHead>
                      <TableHead onClick={() => handleSort('incidentDate')} className="cursor-pointer">
                        Incident Date
                      </TableHead>
                      <TableHead>Type & Severity</TableHead>
                      <TableHead onClick={() => handleSort('claimAmount')} className="cursor-pointer">
                        Amount
                      </TableHead>
                      <TableHead onClick={() => handleSort('status')} className="cursor-pointer">
                        Status
                      </TableHead>
                      <TableHead>AI Priority</TableHead>
                      <TableHead className="w-32 text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedClaims.map((claim) => (
                      <TableRow key={claim.id} hover>
                        <TableCell>
                          <Link to={`/claims/${claim.id}`} className="font-mono font-semibold text-primary hover:underline">
                            {claim.claimNumber}
                          </Link>
                          <div className="text-[11px] text-gray-500 font-mono mt-0.5">{claim.policyNumber}</div>
                        </TableCell>
                        <TableCell>
                          <div className="font-medium text-gray-900">{claim.customerName}</div>
                          <div className="text-xs text-gray-500">{claim.assignedAdjuster || 'Unassigned'}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-900">
                            {claim.vehicle ? `${claim.vehicle.year} ${claim.vehicle.make} ${claim.vehicle.model}` : 'N/A'}
                          </div>
                          <div className="text-xs text-gray-500 font-mono">{claim.vehicle?.licensePlate}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-900">{formatDate(claim.incidentDate)}</div>
                          <div className="text-xs text-gray-500">{formatRelativeTime(claim.submittedAt)}</div>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm font-medium text-gray-900">{labelFor(INCIDENT_TYPES, claim.incidentType)}</span>
                          <span className={clsx(
                            'ml-1.5 inline-block text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded',
                            claim.incidentSeverity === 'major' || claim.incidentSeverity === 'total_loss' ? 'bg-red-100 text-red-700' :
                            claim.incidentSeverity === 'moderate' ? 'bg-amber-100 text-amber-700' :
                            'bg-blue-100 text-blue-700'
                          )}>
                            {claim.incidentSeverity?.replace(/_/g, ' ')}
                          </span>
                        </TableCell>
                        <TableCell className="font-semibold text-gray-900">
                          {formatCurrency(claim.claimAmount)}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={claim.status} />
                        </TableCell>
                        <TableCell>
                          {claim.aiAssessment ? (
                            <Badge
                              variant={
                                claim.aiAssessment.claimPriority === 'high' || claim.aiAssessment.claimPriority === 'critical' ? 'danger' :
                                claim.aiAssessment.claimPriority === 'medium' ? 'warning' : 'success'
                              }
                            >
                              {claim.aiAssessment.claimPriority ? claim.aiAssessment.claimPriority.charAt(0).toUpperCase() + claim.aiAssessment.claimPriority.slice(1) : 'N/A'} Priority
                            </Badge>
                          ) : (
                            <span className="text-xs text-gray-400">Pending</span>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Link to={`/claims/${claim.id}`} className="btn btn-secondary btn-sm" title="View Details">
                              <Eye className="w-3.5 h-3.5 mr-1" />
                              Details
                            </Link>
                            <Link to={`/claims/${claim.id}/tracking`} className="btn btn-outline btn-sm" title="Track Workflow">
                              Track
                            </Link>
                            {canDeleteClaim(user?.role, claim.status) && (
                              <button
                                type="button"
                                onClick={() => {
                                  setDeleteError('')
                                  setDeleteTarget(claim)
                                }}
                                className="btn btn-ghost btn-sm text-red-600 hover:text-red-700"
                                title="Delete claim"
                                aria-label={`Delete claim ${claim.claimNumber}`}
                              >
                                <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                              </button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <TablePagination
                  currentPage={currentPage}
                  totalPages={Math.ceil(filteredClaims.length / pageSize)}
                  onPageChange={setCurrentPage}
                  pageSize={pageSize}
                  totalItems={filteredClaims.length}
                  onPageSizeChange={setPageSize}
                />
              </>
            ) : (
              <EmptyState
                icon={<Briefcase className="w-12 h-12" />}
                title="No claims match your criteria"
                description={search || typeFilter || statusFilter ? 'Try clearing your search or filters.' : 'No claims have been submitted yet.'}
                action={canSubmitClaim ? <Button asChild><Link to="/claims/new">Submit a New Claim</Link></Button> : undefined}
              />
            )}
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Claim"
        message={`Are you sure you want to delete claim ${deleteTarget?.claimNumber}? This action cannot be undone.`}
        confirmText="Delete"
        loading={deleting}
        error={deleteError}
      />
    </div>
  )
}

export default ClaimList
