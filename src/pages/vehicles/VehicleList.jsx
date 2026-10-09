import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Car,
  Search,
  Filter,
  Plus,
  MoreVertical,
  Calendar,
  Wrench,
  FileText,
  AlertTriangle,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { mockVehicles } from '../../data/vehicles'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TablePagination } from '../../components/tables/DataTable'
import { EmptyState } from '../../components/ui/EmptyState'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'

const vehicleStatuses = [
  { value: '', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'sold', label: 'Sold' },
  { value: 'totaled', label: 'Totaled' },
  { value: 'inactive', label: 'Inactive' },
]

export function VehicleList() {
  const [loading, setLoading] = useState(true)
  const [vehicles, setVehicles] = useState([])
  const [filteredVehicles, setFilteredVehicles] = useState([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [sortConfig, setSortConfig] = useState({ key: 'year', direction: 'desc' })

  useEffect(() => {
    const timer = setTimeout(() => {
      setVehicles(mockVehicles)
      setFilteredVehicles(mockVehicles)
      setLoading(false)
    }, 500)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    let result = [...vehicles]

    if (search) {
      const searchLower = search.toLowerCase()
      result = result.filter(
        (v) =>
          v.make.toLowerCase().includes(searchLower) ||
          v.model.toLowerCase().includes(searchLower) ||
          v.licensePlate.toLowerCase().includes(searchLower) ||
          v.vin.toLowerCase().includes(searchLower)
      )
    }

    if (statusFilter) {
      result = result.filter((v) => v.status === statusFilter)
    }

    result.sort((a, b) => {
      const aVal = a[sortConfig.key]
      const bVal = b[sortConfig.key]
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })

    setFilteredVehicles(result)
    setCurrentPage(1)
  }, [search, statusFilter, sortConfig, vehicles])

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const paginatedVehicles = filteredVehicles.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

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
          <h1 className="page-title">Vehicles</h1>
          <p className="page-subtitle">Manage insured vehicles and their details</p>
        </div>
        <Link to="/vehicles/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Add Vehicle
          </Button>
        </Link>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <Input
                placeholder="Search vehicles..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              options={vehicleStatuses}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              placeholder="Filter by status"
              className="w-48"
            />
          </div>

          <div className="overflow-x-auto">
            {filteredVehicles.length > 0 ? (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead onClick={() => handleSort('year')} className="cursor-pointer">
                        Vehicle {sortConfig.key === 'year' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('licensePlate')} className="cursor-pointer">
                        License Plate {sortConfig.key === 'licensePlate' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('vin')} className="cursor-pointer">
                        VIN {sortConfig.key === 'vin' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead onClick={() => handleSort('status')} className="cursor-pointer">
                        Status {sortConfig.key === 'status' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                      </TableHead>
                      <TableHead>Registration Expiry</TableHead>
                      <TableHead>Policy</TableHead>
                      <TableHead>Claims</TableHead>
                      <TableHead className="w-24">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedVehicles.map((vehicle) => (
                      <TableRow key={vehicle.id} clickable onClick={() => window.location.href = `/vehicles/${vehicle.id}`}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-8 bg-gray-100 rounded flex items-center justify-center">
                              <Car className="w-5 h-5 text-gray-400" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-900">{vehicle.year} {vehicle.make} {vehicle.model}</p>
                              <p className="text-sm text-gray-500">{vehicle.color} • {vehicle.fuelType}</p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="font-mono font-medium">{vehicle.licensePlate}</TableCell>
                        <TableCell className="font-mono text-sm">{vehicle.vin}</TableCell>
                        <TableCell><StatusBadge status={vehicle.status} /></TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm">
                            <Calendar className="w-3.5 h-3.5 text-gray-400" />
                            {formatDate(vehicle.registrationExpiry)}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600">{vehicle.policyId}</TableCell>
                        <TableCell>
                          <Badge variant="neutral" size="sm">{vehicle.claims.length} claim(s)</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Link to={`/vehicles/${vehicle.id}`} className="text-primary hover:underline text-sm">View</Link>
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
                  totalPages={Math.ceil(filteredVehicles.length / pageSize)}
                  onPageChange={setCurrentPage}
                  pageSize={pageSize}
                  totalItems={filteredVehicles.length}
                  onPageSizeChange={setPageSize}
                />
              </>
            ) : (
              <EmptyState
                icon={<Car className="w-12 h-12" />}
                title="No vehicles found"
                description={search || statusFilter ? 'Try adjusting your search or filters' : 'No vehicles have been added yet'}
                action={<Button asChild><Link to="/vehicles/new">Add Vehicle</Link></Button>}
              />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default VehicleList