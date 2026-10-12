import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  FileText,
  Search,
  Filter,
  Plus,
  MoreVertical,
  Shield,
  Calendar,
  DollarSign,
  Car,
  Home,
  Building2,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { mockPolicies } from '../../data/policies'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TablePagination } from '../../components/tables/DataTable'
import { EmptyState } from '../../components/ui/EmptyState'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'

const policyTypes = [
  { value: '', label: 'All Types' },
  { value: 'auto', label: 'Auto Insurance' },
  { value: 'home', label: 'Homeowners' },
  { value: 'renters', label: 'Renters' },
  { value: 'life', label: 'Life Insurance' },
  { value: 'commercial', label: 'Commercial' },
]

const policyStatuses = [
  { value: '', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'pending', label: 'Pending' },
  { value: 'expired', label: 'Expired' },
  { value: 'cancelled', label: 'Cancelled' },
]

export function PolicyList() {
  const [loading, setLoading] = useState(true)
  const [policies, setPolicies] = useState([])
  const [filteredPolicies, setFilteredPolicies] = useState([])
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [sortConfig, setSortConfig] = useState({ key: 'startDate', direction: 'desc' })

  useEffect(() => {
    const timer = setTimeout(() => {
      setPolicies(mockPolicies)
      setFilteredPolicies(mockPolicies)
      setLoading(false)
    }, 500)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    let result = [...policies]

    if (search) {
      const searchLower = search.toLowerCase()
      result = result.filter(
        (p) =>
          p.policyNumber.toLowerCase().includes(searchLower) ||
          p.type.toLowerCase().includes(searchLower) ||
          p.customerName.toLowerCase().includes(searchLower) ||
          (p.vehicle && p.vehicle.make.toLowerCase().includes(searchLower)) ||
          (p.vehicle && p.vehicle.model.toLowerCase().includes(searchLower))
      )
    }

    if (typeFilter) {
      result = result.filter((p) => {
        if (typeFilter === 'auto') return p.type.toLowerCase().includes('auto')
        if (typeFilter === 'home') return p.type.toLowerCase().includes('home')
        return p.type.toLowerCase().includes(typeFilter)
      })
    }

    if (statusFilter) {
      result = result.filter((p) => p.status === statusFilter)
    }

    result.sort((a, b) => {
      const aVal = a[sortConfig.key]
      const bVal = b[sortConfig.key]
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })

    setFilteredPolicies(result)
    setCurrentPage(1)
  }, [search, typeFilter, statusFilter, sortConfig, policies])

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const paginatedPolicies = filteredPolicies.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  const getTypeIcon = (type) => {
    if (type.toLowerCase().includes('auto')) return <Car className="w-4 h-4" />
    if (type.toLowerCase().includes('home')) return <Home className="w-4 h-4" />
    if (type.toLowerCase().includes('commercial')) return <Building2 className="w-4 h-4" />
    return <Shield className="w-4 h-4" />
  }

  if (loading) {
    return (
      <div className="page animate-pulse">
        <div className="page-header">
          <div className="h-8 bg-gray-200 rounded w-48 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-64"></div>
        </div>
        <div className="card p-6">
          <div className="h-10 bg-gray-200 rounded mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Policies</h1>
          <p className="page-subtitle">Manage and view all insurance policies</p>
        </div>
        <Link to="/policies/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Policy
          </Button>
        </Link>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <Input
                placeholder="Search policies..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-3">
              <Select
                options={policyTypes}
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                placeholder="Filter by type"
                className="w-48"
              />
              <Select
                options={policyStatuses}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                placeholder="Filter by status"
                className="w-48"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            {filteredPolicies.length > 0 ? (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead onClick={() => handleSort('policyNumber')} className="cursor-pointer">
                        Policy Number {sortConfig.key === 'policyNumber' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('type')} className="cursor-pointer">
                        Type {sortConfig.key === 'type' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('customerName')} className="cursor-pointer">
                        Customer {sortConfig.key === 'customerName' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('status')} className="cursor-pointer">
                        Status {sortConfig.key === 'status' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('startDate')} className="cursor-pointer">
                        Effective Date {sortConfig.key === 'startDate' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('endDate')} className="cursor-pointer">
                        Expiration {sortConfig.key === 'endDate' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('premium')} className="cursor-pointer">
                        Premium {sortConfig.key === 'premium' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead className="w-24">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedPolicies.map((policy) => (
                      <TableRow key={policy.id}>
                        <TableCell>
                          <Link to={`/policies/${policy.id}`} className="font-mono font-medium text-primary hover:underline">
                            {policy.policyNumber}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className={clsx('text-gray-400', policy.type.toLowerCase().includes('auto') && 'text-blue-500', policy.type.toLowerCase().includes('home') && 'text-green-500')}>
                              {getTypeIcon(policy.type)}
                            </span>
                            <span>{policy.type}</span>
                          </div>
                        </TableCell>
                        <TableCell>{policy.customerName}</TableCell>
                        <TableCell><StatusBadge status={policy.status} /></TableCell>
                        <TableCell>{formatDate(policy.startDate)}</TableCell>
                        <TableCell>{formatDate(policy.endDate)}</TableCell>
                        <TableCell className="font-medium">{formatCurrency(policy.premium)}/yr</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Link to={`/policies/${policy.id}`} className="text-primary hover:underline text-sm">View</Link>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <TablePagination
                  currentPage={currentPage}
                  totalPages={Math.ceil(filteredPolicies.length / pageSize)}
                  onPageChange={setCurrentPage}
                  pageSize={pageSize}
                  totalItems={filteredPolicies.length}
                  onPageSizeChange={setPageSize}
                />
              </>
            ) : (
              <EmptyState
                icon={<FileText className="w-12 h-12" />}
                title="No policies found"
                description={search || typeFilter || statusFilter ? 'Try adjusting your search or filters' : 'No policies have been created yet'}
                action={<Button asChild><Link to="/policies/new">Create Policy</Link></Button>}
              />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default PolicyList