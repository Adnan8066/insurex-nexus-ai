import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Briefcase,
  Search,
  Filter,
  Plus,
  ArrowRight,
  Calendar,
  AlertTriangle,
  Car,
  Clock,
  Eye,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { mockClaims, claimStatusWorkflow } from '../../data/claims'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TablePagination } from '../../components/tables/DataTable'
import { EmptyState } from '../../components/ui/EmptyState'

const incidentTypes = [
  { value: '', label: 'All Incident Types' },
  { value: 'Collision', label: 'Collision' },
  { value: 'Comprehensive', label: 'Comprehensive' },
  { value: 'Theft', label: 'Theft' },
  { value: 'Vandalism', label: 'Vandalism' },
]

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'under-review', label: 'Under Review' },
  { value: 'ai-assessment', label: 'AI Assessment' },
  { value: 'investigation', label: 'Investigation' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'repair-settlement', label: 'Repair/Settlement' },
  { value: 'closed', label: 'Closed' },
]

export function ClaimList() {
  const [searchParams] = useSearchParams()
  const statusParam = searchParams.get('status')

  const [loading, setLoading] = useState(true)
  const [claims, setClaims] = useState([])
  const [filteredClaims, setFilteredClaims] = useState([])
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState(statusParam || '')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [sortConfig, setSortConfig] = useState({ key: 'submittedAt', direction: 'desc' })

  useEffect(() => {
    const timer = setTimeout(() => {
      setClaims(mockClaims)
      setFilteredClaims(mockClaims)
      setLoading(false)
    }, 400)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    let result = [...claims]

    if (search) {
      const q = search.toLowerCase()
      result = result.filter(
        (c) =>
          c.claimNumber.toLowerCase().includes(q) ||
          c.customerName.toLowerCase().includes(q) ||
          c.policyNumber.toLowerCase().includes(q) ||
          (c.vehicle && `${c.vehicle.make} ${c.vehicle.model}`.toLowerCase().includes(q)) ||
          c.location.toLowerCase().includes(q)
      )
    }

    if (typeFilter) {
      result = result.filter((c) => c.incidentType === typeFilter)
    }

    if (statusFilter) {
      if (statusFilter === 'pending') {
        result = result.filter((c) => ['submitted', 'under-review', 'ai-assessment', 'investigation'].includes(c.status))
      } else {
        result = result.filter((c) => c.status === statusFilter)
      }
    }

    result.sort((a, b) => {
      let aVal = a[sortConfig.key]
      let bVal = b[sortConfig.key]
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

  const paginatedClaims = filteredClaims.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  const stats = {
    total: claims.length,
    pending: claims.filter((c) => ['submitted', 'under-review', 'ai-assessment', 'investigation'].includes(c.status)).length,
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
          <h1 className="page-title">Claim Management</h1>
          <p className="page-subtitle">Track, review, and manage all auto insurance claims across their full lifecycle</p>
        </div>
        <div className="flex gap-2">
          <Link to="/claims/new">
            <Button variant="primary">
              <Plus className="w-4 h-4 mr-2" />
              Submit Claim
            </Button>
          </Link>
        </div>
      </div>

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
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search by Claim ID, customer, vehicle, location..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex gap-2">
              <Select
                options={incidentTypes}
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                placeholder="Incident Type"
                className="w-44"
              />
              <Select
                options={statusOptions}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                placeholder="Status"
                className="w-44"
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
                          <span className="text-sm font-medium text-gray-900">{claim.incidentType}</span>
                          <span className={clsx(
                            'ml-1.5 inline-block text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded',
                            claim.incidentSeverity === 'Major' ? 'bg-red-100 text-red-700' :
                            claim.incidentSeverity === 'Moderate' ? 'bg-amber-100 text-amber-700' :
                            'bg-blue-100 text-blue-700'
                          )}>
                            {claim.incidentSeverity}
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
                                claim.aiAssessment.claimPriority === 'High' ? 'danger' :
                                claim.aiAssessment.claimPriority === 'Medium' ? 'warning' : 'success'
                              }
                            >
                              {claim.aiAssessment.claimPriority} Priority
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
                description={search || typeFilter || statusFilter ? 'Try clearing your search or filter filters.' : 'No claims have been submitted yet.'}
                action={<Button asChild><Link to="/claims/new">Submit a New Claim</Link></Button>}
              />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default ClaimList
