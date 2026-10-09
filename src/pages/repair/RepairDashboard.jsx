import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Wrench,
  Car,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  DollarSign,
  Search,
  Filter,
  Eye,
  Building,
  Shield,
  Layers,
  ChevronRight,
} from 'lucide-react'
import { clsx } from 'clsx'
import { mockRepairShops } from '../../data/operations'
import { mockClaims } from '../../data/claims'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import { Modal } from '../../components/ui/Modal'
import { formatCurrency, formatDate } from '../../utils/helpers'

const mockRepairJobs = [
  {
    id: 'REP-2024-001',
    claimId: 'CLM-2024-001234',
    claimNumber: 'CLM-2024-001234',
    customerName: 'John Anderson',
    vehicle: { make: 'Toyota', model: 'Camry', year: 2022, licensePlate: 'ABC-1234', vin: '1HGCM82633A123456' },
    estimatedCost: 8200,
    status: 'In Progress',
    repairStage: 'Frame & Body Work',
    priority: 'High',
    completionDate: '2024-02-23',
    startedAt: '2024-02-17',
    assignedBay: 'Bay 3',
  },
  {
    id: 'REP-2024-002',
    claimId: 'CLM-2024-001230',
    claimNumber: 'CLM-2024-001230',
    customerName: 'John Anderson',
    vehicle: { make: 'Toyota', model: 'Camry', year: 2022, licensePlate: 'ABC-1234', vin: '1HGCM82633A123456' },
    estimatedCost: 2950,
    status: 'Parts Ordered',
    repairStage: 'PDR Hail Correction',
    priority: 'Low',
    completionDate: '2024-02-28',
    startedAt: '2024-02-22',
    assignedBay: 'Bay 5',
  },
  {
    id: 'REP-2023-009',
    claimId: 'CLM-2023-000891',
    claimNumber: 'CLM-2023-000891',
    customerName: 'John Anderson',
    vehicle: { make: 'Toyota', model: 'Camry', year: 2022, licensePlate: 'ABC-1234', vin: '1HGCM82633A123456' },
    estimatedCost: 1500,
    status: 'Completed',
    repairStage: 'Delivered to Customer',
    priority: 'Medium',
    completionDate: '2023-11-30',
    startedAt: '2023-11-25',
    assignedBay: 'Bay 1',
  },
]

export function RepairDashboard() {
  const [selectedShopId, setSelectedShopId] = useState(1)
  const [shops] = useState(mockRepairShops)
  const [jobs, setJobs] = useState(mockRepairJobs)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedJobForUpdate, setSelectedJobForUpdate] = useState(null)
  const [newStatus, setNewStatus] = useState('')

  const activeShop = shops.find((s) => s.id === Number(selectedShopId)) || shops[0]

  const handleUpdateStatus = () => {
    if (!selectedJobForUpdate) return
    setJobs((prev) =>
      prev.map((j) => (j.id === selectedJobForUpdate.id ? { ...j, status: newStatus } : j))
    )
    setSelectedJobForUpdate(null)
  }

  const filteredJobs = jobs.filter((j) => {
    const q = search.toLowerCase()
    const matchesSearch =
      j.claimNumber.toLowerCase().includes(q) ||
      j.customerName.toLowerCase().includes(q) ||
      `${j.vehicle.make} ${j.vehicle.model}`.toLowerCase().includes(q)
    const matchesStatus = !statusFilter || j.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <Wrench className="w-3.5 h-3.5 text-emerald-600" />
              Certified Collision Network
            </span>
          </div>
          <h1 className="page-title">Repair Shop Dashboard</h1>
          <p className="page-subtitle">
            Manage authorized insurance repairs, vehicle intake, parts ordering, and estimated turnaround schedules
          </p>
        </div>

        {/* Shop Switcher */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-gray-500 uppercase">Shop:</label>
          <select
            value={selectedShopId}
            onChange={(e) => setSelectedShopId(e.target.value)}
            className="input-field text-sm font-semibold py-2 px-3 border border-gray-300 rounded-lg bg-white"
            aria-label="Active Repair Facility"
          >
            {shops.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.rating} ★)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Facility Header Card */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-primary text-white flex items-center justify-center font-bold text-xl shadow-md">
            <Building className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-gray-900">{activeShop.name}</h2>
              <Badge variant="success">Approved Network Facility</Badge>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{activeShop.address} • License: {activeShop.licenseNumber}</p>
            <div className="flex gap-1.5 mt-2 flex-wrap">
              {activeShop.certifications.map((c, i) => (
                <span key={i} className="text-[11px] font-medium bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full">
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-6 border-t md:border-t-0 md:border-l pt-4 md:pt-0 md:pl-6 text-sm">
          <div>
            <span className="text-xs text-gray-400 block font-medium">Bay Capacity</span>
            <span className="text-xl font-bold text-gray-900">{activeShop.currentJobs} / {activeShop.capacity} bays</span>
          </div>
          <div>
            <span className="text-xs text-gray-400 block font-medium">Customer Rating</span>
            <span className="text-xl font-bold text-amber-600">{activeShop.rating} ★</span>
          </div>
          <div>
            <span className="text-xs text-gray-400 block font-medium">Avg Turnaround</span>
            <span className="text-xl font-bold text-gray-900">{activeShop.averageTurnaroundDays} days</span>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active Repair Jobs</p>
            <p className="text-2xl font-black text-gray-900 mt-1">{jobs.filter((j) => j.status !== 'Completed').length}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Wrench className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">High Priority / Fast Track</p>
            <p className="text-2xl font-black text-red-600 mt-1">
              {jobs.filter((j) => j.priority === 'High').length}
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Work in Progress</p>
            <p className="text-2xl font-black text-emerald-600 mt-1">
              {formatCurrency(jobs.reduce((acc, j) => acc + j.estimatedCost, 0))}
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <DollarSign className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Completed This Month</p>
            <p className="text-2xl font-black text-primary mt-1">
              {jobs.filter((j) => j.status === 'Completed').length}
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Repair Jobs Table */}
      <Card>
        <CardHeader
          title="Assigned Vehicle Repair Work Orders"
          subtitle="Repair orders dispatched by insurance adjusters and AI settlement engine"
        />
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search job ID, claim, vehicle, or customer..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              options={[
                { value: '', label: 'All Repair Statuses' },
                { value: 'In Progress', label: 'In Progress' },
                { value: 'Parts Ordered', label: 'Parts Ordered' },
                { value: 'Completed', label: 'Completed' },
              ]}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-52"
            />
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job ID & Claim</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Vehicle Information</TableHead>
                  <TableHead>Repair Stage</TableHead>
                  <TableHead>Est. Cost</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Repair Status</TableHead>
                  <TableHead>Target Completion</TableHead>
                  <TableHead className="w-32 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredJobs.map((job) => (
                  <TableRow key={job.id} hover>
                    <TableCell>
                      <div className="font-mono font-bold text-gray-900">{job.id}</div>
                      <Link to={`/claims/${job.claimId}`} className="text-xs text-primary hover:underline font-mono">
                        {job.claimNumber}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <div className="font-semibold text-gray-900">{job.customerName}</div>
                      <div className="text-xs text-gray-500">Bay: {job.assignedBay}</div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm font-medium text-gray-900">
                        {job.vehicle.year} {job.vehicle.make} {job.vehicle.model}
                      </div>
                      <div className="text-xs text-gray-500 font-mono">
                        Plate: {job.vehicle.licensePlate} • VIN: ...{job.vehicle.vin.slice(-6)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-medium text-gray-800 bg-gray-100 px-2 py-0.5 rounded">
                        {job.repairStage}
                      </span>
                    </TableCell>
                    <TableCell className="font-bold text-gray-900">
                      {formatCurrency(job.estimatedCost)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={job.priority === 'High' ? 'danger' : job.priority === 'Medium' ? 'warning' : 'success'}>
                        {job.priority} Priority
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className={clsx(
                        'text-xs font-semibold px-2 py-0.5 rounded-full inline-block',
                        job.status === 'Completed' ? 'bg-emerald-100 text-emerald-800' :
                        job.status === 'In Progress' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
                      )}>
                        {job.status}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm font-medium text-gray-900 flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-gray-400" />
                        {formatDate(job.completionDate)}
                      </div>
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedJobForUpdate(job)
                          setNewStatus(job.status)
                        }}
                      >
                        Update
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Update Job Modal */}
      {selectedJobForUpdate && (
        <Modal
          isOpen={!!selectedJobForUpdate}
          onClose={() => setSelectedJobForUpdate(null)}
          title={`Update Repair Job: ${selectedJobForUpdate.id}`}
          size="md"
        >
          <div className="space-y-4">
            <div className="p-3 bg-gray-50 rounded-xl text-xs space-y-1">
              <div>Vehicle: <strong>{selectedJobForUpdate.vehicle.year} {selectedJobForUpdate.vehicle.make} {selectedJobForUpdate.vehicle.model}</strong></div>
              <div>Estimated Cost: <strong>{formatCurrency(selectedJobForUpdate.estimatedCost)}</strong></div>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 uppercase block mb-1.5">Update Repair Status</label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="input-field"
              >
                <option value="Parts Ordered">Parts Ordered</option>
                <option value="In Progress">In Progress (Frame / Teardown)</option>
                <option value="Painting">Painting & Refinishing</option>
                <option value="Quality Inspection">Quality Inspection</option>
                <option value="Completed">Completed & Ready for Pickup</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="secondary" onClick={() => setSelectedJobForUpdate(null)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleUpdateStatus}>
                Save Changes
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default RepairDashboard
