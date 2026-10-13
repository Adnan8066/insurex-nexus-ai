import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Wrench,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  DollarSign,
  Search,
  Building,
  Play,
  Flag,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'
import { clsx } from 'clsx'
import { repairService, claimService } from '../../services'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import { Modal } from '../../components/ui/Modal'
import { formatCurrency, formatDate } from '../../utils/helpers'

const JOB_STATUS_LABELS = {
  scheduled: 'Scheduled',
  parts_ordered: 'Parts Ordered',
  in_progress: 'In Progress',
  painting: 'Painting & Refinishing',
  quality_inspection: 'Quality Inspection',
  completed: 'Completed',
  delivered: 'Delivered',
  on_hold: 'On Hold',
  cancelled: 'Cancelled',
}

const ACTIVE_JOB_STATUSES = ['scheduled', 'parts_ordered', 'in_progress', 'painting', 'quality_inspection', 'on_hold']

const PRIORITY_VARIANT = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'success',
}

const STATUS_STYLE = (status) =>
  status === 'completed' || status === 'delivered'
    ? 'bg-emerald-100 text-emerald-800'
    : status === 'in_progress' || status === 'painting' || status === 'quality_inspection'
      ? 'bg-blue-100 text-blue-800'
      : status === 'cancelled'
        ? 'bg-red-100 text-red-800'
        : 'bg-amber-100 text-amber-800'

export function RepairDashboard() {
  const [shops, setShops] = useState([])
  const [jobs, setJobs] = useState([])
  const [claimsMap, setClaimsMap] = useState({})
  const [selectedShopId, setSelectedShopId] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedJobForUpdate, setSelectedJobForUpdate] = useState(null)
  const [updateForm, setUpdateForm] = useState({ status: '', repair_stage: '', assigned_bay: '' })
  const [updating, setUpdating] = useState(false)
  const [completingJob, setCompletingJob] = useState(null)
  const [completeForm, setCompleteForm] = useState({ actual_cost: '', quality_score: '' })
  const [completing, setCompleting] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [shopsRes, jobsRes] = await Promise.allSettled([
        repairService.getShops(),
        repairService.getJobs(),
      ])
      const shopItems =
        shopsRes.status === 'fulfilled'
          ? Array.isArray(shopsRes.value) ? shopsRes.value : shopsRes.value.results || []
          : []
      const jobItems =
        jobsRes.status === 'fulfilled'
          ? Array.isArray(jobsRes.value) ? jobsRes.value : jobsRes.value.results || []
          : []
      setShops(shopItems)
      setJobs(jobItems)
      if (shopItems.length && !selectedShopId) {
        setSelectedShopId(String(shopItems[0].id))
      }

      // Fetch claim details for customer + vehicle info
      const claimIds = [...new Set(jobItems.map((j) => j.claim).filter(Boolean))]
      const claimResults = await Promise.allSettled(
        claimIds.map((id) => claimService.getClaim(id))
      )
      const map = {}
      claimResults.forEach((res, i) => {
        if (res.status === 'fulfilled') {
          map[claimIds[i]] = res.value
        }
      })
      setClaimsMap(map)
    } catch (err) {
      console.error('Failed to load repair data:', err)
      setError(err.message || 'Failed to load repair jobs. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [selectedShopId])

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const filteredJobs = jobs.filter((j) => {
    const claim = claimsMap[j.claim] || {}
    const q = search.toLowerCase()
    const matchesSearch =
      (j.job_number || '').toLowerCase().includes(q) ||
      (j.claim_number || '').toLowerCase().includes(q) ||
      (claim.customer_name || '').toLowerCase().includes(q) ||
      (claim.vehicle_info ? `${claim.vehicle_info.make} ${claim.vehicle_info.model}`.toLowerCase() : '').includes(q)
    const matchesStatus = !statusFilter || j.status === statusFilter
    const matchesShop = !selectedShopId || j.repair_shop === Number(selectedShopId)
    return matchesSearch && matchesStatus && matchesShop
  })

  const activeJobs = jobs.filter((j) => ACTIVE_JOB_STATUSES.includes(j.status))
  const highPriority = jobs.filter((j) => j.priority === 'high' || j.priority === 'critical')
  const totalWipCost = activeJobs.reduce((acc, j) => acc + Number(j.estimated_cost || 0), 0)
  const completedCount = jobs.filter((j) => j.status === 'completed' || j.status === 'delivered').length

  const activeShop = shops.find((s) => String(s.id) === String(selectedShopId)) || shops[0] || {}

  const handleStartJob = async (job) => {
    try {
      await repairService.startJob(job.id)
      await loadData()
    } catch (err) {
      console.error('Failed to start job:', err)
      setError(err.message || 'Failed to start job.')
    }
  }

  const handleUpdateJob = async (e) => {
    e.preventDefault()
    if (!selectedJobForUpdate) return
    setUpdating(true)
    try {
      await repairService.updateJob(selectedJobForUpdate.id, {
        status: updateForm.status,
        repair_stage: updateForm.repair_stage,
        assigned_bay: updateForm.assigned_bay,
      })
      setSelectedJobForUpdate(null)
      await loadData()
    } catch (err) {
      console.error('Failed to update job:', err)
      setError(err.message || 'Failed to update job.')
    } finally {
      setUpdating(false)
    }
  }

  const handleCompleteJob = async (e) => {
    e.preventDefault()
    if (!completingJob) return
    setCompleting(true)
    try {
      await repairService.completeJob(completingJob.id, {
        actual_cost: completeForm.actual_cost || undefined,
        quality_score: completeForm.quality_score || undefined,
      })
      setCompletingJob(null)
      setCompleteForm({ actual_cost: '', quality_score: '' })
      await loadData()
    } catch (err) {
      console.error('Failed to complete job:', err)
      setError(err.message || 'Failed to complete job.')
    } finally {
      setCompleting(false)
    }
  }

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

        {shops.length > 0 && (
          <div className="flex items-center gap-3">
            <label className="text-xs font-bold text-gray-500 uppercase">Shop:</label>
            <Select
              options={shops.map((s) => ({
                value: String(s.id),
                label: `${s.name} (${s.city}, ${s.state})`,
              }))}
              value={selectedShopId}
              onChange={(e) => setSelectedShopId(e.target.value)}
              className="w-64"
            />
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </span>
          <Button variant="outline" size="sm" onClick={loadData}>
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Retry
          </Button>
        </div>
      )}

      {loading && jobs.length === 0 && (
        <div className="p-8 text-center text-sm text-gray-400">Loading repair jobs...</div>
      )}

      {/* Facility Header Card */}
      {activeShop && activeShop.id && (
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-primary text-white flex items-center justify-center font-bold text-xl shadow-md">
              <Building className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-gray-900">{activeShop.name}</h2>
                <Badge variant={activeShop.status === 'approved' ? 'success' : 'warning'}>
                  {activeShop.status === 'approved' ? 'Approved Network Facility' : activeShop.status}
                </Badge>
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                {activeShop.address} • License: {activeShop.license_number}
              </p>
              <div className="flex gap-1.5 mt-2 flex-wrap">
                {(activeShop.specialties || []).map((c, i) => (
                  <span key={i} className="text-[11px] font-medium bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full">
                    {c}
                  </span>
                ))}
                {(!activeShop.specialties || !activeShop.specialties.length) && (
                  <span className="text-[11px] text-gray-400">No specialties listed</span>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-6 border-t md:border-t-0 md:border-l pt-4 md:pt-0 md:pl-6 text-sm">
            <div>
              <span className="text-xs text-gray-400 block font-medium">Bay Capacity</span>
              <span className="text-xl font-bold text-gray-900">{activeShop.current_jobs} / {activeShop.capacity} bays</span>
            </div>
            <div>
              <span className="text-xs text-gray-400 block font-medium">Customer Rating</span>
              <span className="text-xl font-bold text-amber-600">{activeShop.rating} ★</span>
            </div>
            <div>
              <span className="text-xs text-gray-400 block font-medium">Avg Turnaround</span>
              <span className="text-xl font-bold text-gray-900">{activeShop.average_turnaround_days} days</span>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active Repair Jobs</p>
            <p className="text-2xl font-black text-gray-900 mt-1">{activeJobs.length}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Wrench className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">High Priority / Fast Track</p>
            <p className="text-2xl font-black text-red-600 mt-1">{highPriority.length}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Work in Progress</p>
            <p className="text-2xl font-black text-emerald-600 mt-1">{formatCurrency(totalWipCost)}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <DollarSign className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Completed Jobs</p>
            <p className="text-2xl font-black text-primary mt-1">{completedCount}</p>
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
                placeholder="Search job #, claim, vehicle, or customer..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              options={[
                { value: '', label: 'All Repair Statuses' },
                ...Object.entries(JOB_STATUS_LABELS).map(([value, label]) => ({ value, label })),
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
                  <TableHead className="w-40 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredJobs.map((job) => {
                  const claim = claimsMap[job.claim] || {}
                  const vehicle = claim.vehicle_info || {}
                  return (
                    <TableRow key={job.id} hover>
                      <TableCell>
                        <div className="font-mono font-bold text-gray-900">{job.job_number}</div>
                        <Link to={`/claims/${job.claim}`} className="text-xs text-primary hover:underline font-mono">
                          {job.claim_number}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="font-semibold text-gray-900">{claim.customer_name || '—'}</div>
                        <div className="text-xs text-gray-500">
                          Bay: {job.assigned_bay || 'Unassigned'} • {job.repair_shop_name || ''}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm font-medium text-gray-900">
                          {vehicle.year} {vehicle.make} {vehicle.model}
                        </div>
                        <div className="text-xs text-gray-500 font-mono">
                          {vehicle.license_plate ? `Plate: ${vehicle.license_plate} • ` : ''}
                          {vehicle.vin ? `VIN: ...${String(vehicle.vin).slice(-6)}` : ''}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-medium text-gray-800 bg-gray-100 px-2 py-0.5 rounded">
                          {job.repair_stage || '—'}
                        </span>
                      </TableCell>
                      <TableCell className="font-bold text-gray-900">
                        {formatCurrency(job.estimated_cost)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={PRIORITY_VARIANT[job.priority] || 'warning'}>
                          {(job.priority || 'medium').toUpperCase()} Priority
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className={clsx(
                          'text-xs font-semibold px-2 py-0.5 rounded-full inline-block',
                          STATUS_STYLE(job.status)
                        )}>
                          {JOB_STATUS_LABELS[job.status] || job.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm font-medium text-gray-900 flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-gray-400" />
                          {job.estimated_completion ? formatDate(job.estimated_completion) : '—'}
                        </div>
                      </TableCell>
                      <TableCell align="right">
                        <div className="flex items-center justify-end gap-1.5">
                          {job.status === 'scheduled' && (
                            <Button
                              variant="outline"
                              size="sm"
                              title="Start Job"
                              onClick={() => handleStartJob(job)}
                            >
                              <Play className="w-3.5 h-3.5 mr-1" />
                              Start
                            </Button>
                          )}
                          {(ACTIVE_JOB_STATUSES.includes(job.status)) && (
                            <Button
                              variant="secondary"
                              size="sm"
                              title="Complete Job"
                              onClick={() => {
                                setCompletingJob(job)
                                setCompleteForm({
                                  actual_cost: job.actual_cost || '',
                                  quality_score: job.quality_score || '',
                                })
                              }}
                            >
                              <Flag className="w-3.5 h-3.5 mr-1" />
                              Complete
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedJobForUpdate(job)
                              setUpdateForm({
                                status: job.status,
                                repair_stage: job.repair_stage || '',
                                assigned_bay: job.assigned_bay || '',
                              })
                            }}
                          >
                            Update
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
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
          title={`Update Repair Job: ${selectedJobForUpdate.job_number}`}
          size="md"
        >
          <form onSubmit={handleUpdateJob} className="space-y-4">
            <div className="p-3 bg-gray-50 rounded-xl text-xs space-y-1">
              <div>Claim: <strong className="font-mono">{selectedJobForUpdate.claim_number}</strong></div>
              <div>Estimated Cost: <strong>{formatCurrency(selectedJobForUpdate.estimated_cost)}</strong></div>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 uppercase block mb-1.5">Repair Status</label>
              <Select
                options={Object.entries(JOB_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
                value={updateForm.status}
                onChange={(e) => setUpdateForm({ ...updateForm, status: e.target.value })}
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 uppercase block mb-1.5">Repair Stage</label>
              <Input
                value={updateForm.repair_stage}
                onChange={(e) => setUpdateForm({ ...updateForm, repair_stage: e.target.value })}
                placeholder="e.g., Frame & Body Work"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 uppercase block mb-1.5">Assigned Bay</label>
              <Input
                value={updateForm.assigned_bay}
                onChange={(e) => setUpdateForm({ ...updateForm, assigned_bay: e.target.value })}
                placeholder="e.g., Bay 3"
              />
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="secondary" onClick={() => setSelectedJobForUpdate(null)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" disabled={updating}>
                {updating ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Complete Job Modal */}
      {completingJob && (
        <Modal
          isOpen={!!completingJob}
          onClose={() => setCompletingJob(null)}
          title={`Complete Repair Job: ${completingJob.job_number}`}
          size="md"
        >
          <form onSubmit={handleCompleteJob} className="space-y-4">
            <div className="p-3 bg-gray-50 rounded-xl text-xs space-y-1">
              <div>Claim: <strong className="font-mono">{completingJob.claim_number}</strong></div>
              <div>Estimated Cost: <strong>{formatCurrency(completingJob.estimated_cost)}</strong></div>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 uppercase block mb-1.5">Actual Cost ($)</label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={completeForm.actual_cost}
                onChange={(e) => setCompleteForm({ ...completeForm, actual_cost: e.target.value })}
                placeholder="Final repair cost"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-700 uppercase block mb-1.5">Quality Score (0-100)</label>
              <Input
                type="number"
                min="0"
                max="100"
                value={completeForm.quality_score}
                onChange={(e) => setCompleteForm({ ...completeForm, quality_score: e.target.value })}
                placeholder="e.g., 95"
              />
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="secondary" onClick={() => setCompletingJob(null)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" disabled={completing}>
                {completing ? 'Completing...' : 'Mark Completed'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

export default RepairDashboard
