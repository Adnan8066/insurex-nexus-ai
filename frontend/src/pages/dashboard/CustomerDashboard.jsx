import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  FileText,
  Briefcase,
  Clock,
  CheckCircle,
  AlertTriangle,
  Bell,
  Car,
  DollarSign,
  TrendingUp,
  Shield,
  ArrowRight,
  MoreVertical,
  RefreshCw,
  Download,
  Calendar,
  WifiOff,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { policyService, claimService, vehicleService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ChartCard, MetricChart, AreaChart, DoughnutChart } from '../../components/charts/ChartComponents'
import { EmptyState } from '../../components/ui/EmptyState'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'

import ErrorBoundary, {
  ChartErrorFallback,
  DataTableErrorFallback,
} from '../../components/ui/ErrorBoundary'

import { DashboardSkeleton, ChartSkeleton, TableSkeleton } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/toastHooks'
import { analyticsService } from '../../services/analyticsService'

const claimStatusConfig = {
  submitted: { label: 'Submitted', color: 'info' },
  under_review: { label: 'Under Review', color: 'warning' },
  ai_assessment: { label: 'AI Assessment', color: 'primary' },
  investigation: { label: 'Investigation', color: 'warning' },
  approved: { label: 'Approved', color: 'success' },
  rejected: { label: 'Rejected', color: 'danger' },
  repair_settlement: { label: 'Repair/Settlement', color: 'primary' },
  closed: { label: 'Closed', color: 'neutral' },
}

const TIMEFRAME_OPTIONS = [
  { value: 'week', label: 'Last 7 Days', days: 7 },
  { value: 'month', label: 'Last 30 Days', days: 30 },
  { value: 'quarter', label: 'Current Quarter', days: 90 },
  { value: 'ytd', label: 'Year to Date', days: 365 },
  { value: 'year', label: 'Last Year', days: 365 },
]

export function CustomerDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  const [loading, setLoading] = useState(true)
  const [policies, setPolicies] = useState([])
  const [claims, setClaims] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [notifications, setNotifications] = useState([])
  const [timeframe, setTimeframe] = useState(searchParams.get('timeframe') || 'quarter')
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [connectionError, setConnectionError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(new Date())

  const mapClaim = (c) => ({
    id: c.id,
    claimNumber: c.claim_number,
    customerName: c.customer_name,
    policyNumber: c.policy_number,
    vehicle: c.vehicle_info ? {
      id: c.vehicle_info.id,
      year: c.vehicle_info.year,
      make: c.vehicle_info.make,
      model: c.vehicle_info.model,
      licensePlate: c.vehicle_info.license_plate,
    } : null,
    incidentDate: c.incident_date,
    incidentType: c.incident_type,
    incidentSeverity: c.incident_severity,
    location: c.location,
    claimAmount: c.claim_amount,
    status: c.status,
    priority: c.priority,
    submittedAt: c.submitted_at,
    aiAssessment: c.ai_assessment ? {
      ...c.ai_assessment,
      totalLossProbability: c.ai_assessment.total_loss_probability,
      claimPriority: c.ai_assessment.claim_priority || c.ai_assessment.priority,
    } : null,
  })

  const mapPolicy = (p) => ({
    id: p.id,
    policyNumber: p.policy_number,
    customerName: p.customer_name,
    type: p.type,
    status: p.status,
    startDate: p.start_date,
    endDate: p.end_date,
    premium: p.premium,
    deductible: p.deductible,
    paymentFrequency: p.payment_frequency,
    autoRenew: p.auto_renew,
    vehicle: p.vehicle_info ? {
      id: p.vehicle_info.id,
      year: p.vehicle_info.year,
      make: p.vehicle_info.make,
      model: p.vehicle_info.model,
      licensePlate: p.vehicle_info.license_plate,
    } : null,
    property: { address: p.property_address },
    createdAt: p.created_at,
  })

  const mapVehicle = (v) => ({
    id: v.id,
    make: v.make,
    model: v.model,
    year: v.year,
    vin: v.vin,
    licensePlate: v.license_plate,
    color: v.color,
    fuelType: v.fuel_type,
    transmission: v.transmission,
    status: v.status,
    currentMileage: v.current_mileage,
  })

  const fetchData = useCallback(async (timeframeParam = timeframe) => {
    setRefreshing(true)
    setConnectionError(null)
    try {
      const [polRes, clmRes, vehRes] = await Promise.all([
        policyService.getPolicies().catch(() => ({ results: [] })),
        claimService.getClaims().catch(() => ({ results: [] })),
        vehicleService.getVehicles().catch(() => ({ results: [] })),
      ])
      const pols = Array.isArray(polRes) ? polRes : (polRes.results || [])
      const clms = Array.isArray(clmRes) ? clmRes : (clmRes.results || [])
      const vehs = Array.isArray(vehRes) ? vehRes : (vehRes.results || [])
      setPolicies(pols.map(mapPolicy))
      setClaims(clms.map(mapClaim))
      setVehicles(vehs.map(mapVehicle))
      setNotifications([])
      setLastUpdated(new Date())
      setConnectionError(null)
    } catch (err) {
      setConnectionError(err.response?.data?.detail || err.message || 'Backend unreachable')
      toast.showRetryToast('Connection error. Unable to load dashboard data.', () => fetchData(timeframeParam))
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }, [timeframe, toast])

  useEffect(() => {
    fetchData(timeframe)
  }, [fetchData, timeframe])

  useEffect(() => {
    const params = new URLSearchParams(searchParams)
    if (timeframe !== 'quarter') {
      params.set('timeframe', timeframe)
    } else {
      params.delete('timeframe')
    }
    setSearchParams(params, { replace: true })
  }, [timeframe, searchParams, setSearchParams])

  useEffect(() => {
    let interval
    if (autoRefresh) {
      interval = setInterval(() => fetchData(timeframe), 60000)
    }
    return () => clearInterval(interval)
  }, [autoRefresh, timeframe, fetchData])

  const activePolicies = policies.filter((p) => p.status === 'active')
  const activeClaims = claims.filter((c) => !['closed', 'rejected'].includes(c.status))
  const pendingClaims = claims.filter((c) => ['submitted', 'under_review', 'ai_assessment', 'investigation'].includes(c.status))
  const approvedClaims = claims.filter((c) => c.status === 'approved')
  const totalLossCases = claims.filter((c) => c.incidentSeverity === 'total_loss' || (c.aiAssessment?.totalLossProbability || 0) > 50)
  const recentClaims = [...claims].sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt)).slice(0, 5)

  const claimsByStatus = claims.reduce((acc, claim) => {
    acc[claim.status] = (acc[claim.status] || 0) + 1
    return acc
  }, {})

  const claimStatusData = useMemo(() => ({
    labels: Object.keys(claimStatusConfig).map((k) => claimStatusConfig[k].label),
    datasets: [
      {
        data: Object.keys(claimStatusConfig).map((k) => claimsByStatus[k] || 0),
        backgroundColor: [
          '#3b82f6',
          '#f59e0b',
          '#1e3a5f',
          '#f59e0b',
          '#10b981',
          '#ef4444',
          '#1e3a5f',
          '#94a3b8',
        ],
        borderWidth: 0,
      },
    ],
  }), [claimsByStatus])

  const monthlyClaimsData = useMemo(() => {
    const monthLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const counts = new Array(12).fill(0)
    claims.forEach((c) => {
      if (c.submittedAt) {
        const m = new Date(c.submittedAt).getMonth()
        if (m >= 0 && m < 12) counts[m] += 1
      }
    })
    return {
      labels: monthLabels,
      datasets: [
        {
          label: 'Claims Submitted',
          data: counts,
          borderColor: '#1e3a5f',
          backgroundColor: 'rgba(30, 58, 95, 0.1)',
          fill: true,
          tension: 0.4,
        },
      ],
    }
  }, [claims])

  const handleTimeframeChange = (newTimeframe) => {
    setTimeframe(newTimeframe)
    setLoading(true)
    fetchData(newTimeframe)
  }

  const handleExport = async () => {
    try {
      const report = await analyticsService.exportReport('csv', { timeframe, claims: claims.length, policies: policies.length })
      const blob = new Blob([report], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `customer-report-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      toast.showSuccess('Report exported successfully')
    } catch (err) {
      toast.showError('Failed to export report')
    }
  }

  const metricCards = [
    {
      title: 'Active Policies',
      value: activePolicies.length,
      icon: FileText,
      iconColor: 'text-blue-600',
      bgColor: 'bg-blue-50',
      link: '/policies',
    },
    {
      title: 'Total Claims',
      value: claims.length,
      icon: Briefcase,
      iconColor: 'text-purple-600',
      bgColor: 'bg-purple-50',
      link: '/claims',
    },
    {
      title: 'Pending Claims',
      value: pendingClaims.length,
      icon: Clock,
      iconColor: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
      link: '/claims?status=pending',
    },
    {
      title: 'Approved Claims',
      value: approvedClaims.length,
      icon: CheckCircle,
      iconColor: 'text-green-600',
      bgColor: 'bg-green-50',
      link: '/claims?status=approved',
    },
  ]

  const totalLossCards = [
    {
      title: 'Total Loss Cases',
      value: totalLossCases.length,
      icon: AlertTriangle,
      iconColor: 'text-orange-600',
      bgColor: 'bg-orange-50',
      link: '/claims?status=total_loss',
    },
  ]

  const quickActions = [
    { label: 'File New Claim', href: '/claims/new', icon: AlertTriangle, color: 'bg-red-50 text-red-600 hover:bg-red-100' },
    { label: 'View Policies', href: '/policies', icon: FileText, color: 'bg-blue-50 text-blue-600 hover:bg-blue-100' },
    { label: 'Manage Vehicles', href: '/vehicles', icon: Car, color: 'bg-green-50 text-green-600 hover:bg-green-100' },
    { label: 'Make Payment', href: '/settlements', icon: DollarSign, color: 'bg-purple-50 text-purple-600 hover:bg-purple-100' },
  ]

  if (loading) {
    return <DashboardSkeleton />
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Welcome back, {user?.first_name || user?.get_full_name?.call(user) || (user?.email || '').split('@')[0] || 'Customer'}! Here&apos;s an overview of your insurance portfolio.</p>
          {connectionError && (
            <div className="mt-2 flex items-center gap-2 text-sm text-red-600">
              <WifiOff className="w-4 h-4" />
              <span>Connection error: {connectionError}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <select
              value={timeframe}
              onChange={(e) => handleTimeframeChange(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-primary focus:border-primary"
            >
              {TIMEFRAME_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={clsx(autoRefresh && 'text-primary bg-primary/10')}
            title={autoRefresh ? 'Auto-refresh ON (60s)' : 'Auto-refresh OFF'}
          >
            <RefreshCw className={clsx('w-4 h-4', autoRefresh && 'animate-spin')} />
            <span className="ml-1">{autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh'}</span>
          </Button>

          <Button variant="ghost" size="sm" className="relative" onClick={() => fetchData(timeframe)} loading={refreshing}>
            <RefreshCw className="w-4 h-4" />
          </Button>

          <Button variant="ghost" size="sm" className="relative">
            <Bell className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs font-semibold rounded-full flex items-center justify-center">3</span>
          </Button>

          <Button variant="primary" size="sm" onClick={handleExport} loading={refreshing}>
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metricCards.map((metric) => (
          <ErrorBoundary
            key={metric.title}
            fallback={({ resetError }) => (
              <div className="card p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">{metric.title}</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">-</p>
                  </div>
                  <div className={clsx('w-12 h-12 rounded-xl flex items-center justify-center', metric.bgColor, metric.iconColor)}>
                    <metric.icon className="w-6 h-6" />
                  </div>
                </div>
                <Button variant="ghost" size="sm" onClick={resetError} className="mt-4">
                  Retry
                </Button>
              </div>
            )}
          >
            <Link key={metric.title} to={metric.link} className="card hover:shadow-lg transition-shadow group">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">{metric.title}</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">{metric.value}</p>
                  </div>
                  <div className={clsx('w-12 h-12 rounded-xl flex items-center justify-center', metric.bgColor, metric.iconColor)}>
                    <metric.icon className="w-6 h-6" />
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm text-gray-500 group-hover:text-primary transition-colors">
                  <span>View details</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </div>
              </CardContent>
            </Link>
          </ErrorBoundary>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <ChartErrorFallback title="Claims Overview" resetError={resetError} retryCount={retryCount} />
          )}>
            <ChartCard title="Claims Overview" subtitle={`Monthly claims submitted (${TIMEFRAME_OPTIONS.find((t) => t.value === timeframe)?.label})`}>
              <AreaChart data={monthlyClaimsData} height={300} />
            </ChartCard>
          </ErrorBoundary>
        </div>
        <div>
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <ChartErrorFallback title="Claim Status Distribution" resetError={resetError} retryCount={retryCount} />
          )}>
            <ChartCard title="Claim Status Distribution" subtitle="Current status of all your claims">
              <DoughnutChart data={claimStatusData} height={300} />
            </ChartCard>
          </ErrorBoundary>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <DataTableErrorFallback title="Recent Claims" resetError={resetError} retryCount={retryCount} />
          )}>
            <Card>
              <CardHeader
                title="Recent Claims"
                subtitle="Your 5 most recent claims"
                action={
                  <Button variant="ghost" size="sm" asChild>
                    <Link to="/claims">View All <ArrowRight className="w-4 h-4 ml-1" /></Link>
                  </Button>
                }
              />
              <CardContent className="p-0">
                {recentClaims.length > 0 ? (
                  <div className="divide-y divide-gray-200">
                    {recentClaims.map((claim) => (
                      <Link key={claim.id} to={`/claims/${claim.id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3 flex-wrap">
                              <span className="font-semibold text-gray-900">{claim.claimNumber}</span>
                              <StatusBadge status={claim.status} />
                              <span className="text-sm text-gray-500">{formatDate(claim.incidentDate)}</span>
                            </div>
                            <p className="text-sm text-gray-600 mt-1 truncate">{claim.incidentType?.replace(/_/g, ' ')} • {claim.vehicle ? `${claim.vehicle.make} ${claim.vehicle.model}` : 'N/A'}</p>
                            <p className="text-sm text-gray-500 mt-0.5">{claim.location}</p>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="font-semibold text-gray-900">{formatCurrency(claim.claimAmount)}</p>
                            <p className="text-xs text-gray-500">{formatRelativeTime(claim.submittedAt)}</p>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="No claims yet"
                    description="You haven't filed any claims yet. Click 'File Claim' to get started."
                    action={<Button asChild><Link to="/claims/new">File Claim</Link></Button>}
                  />
                )}
              </CardContent>
            </Card>
          </ErrorBoundary>
        </div>
        <div>
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <DataTableErrorFallback title="Active Policies" resetError={resetError} retryCount={retryCount} />
          )}>
            <Card>
              <CardHeader
                title="Active Policies"
                subtitle="Your current coverage"
                action={
                  <Button variant="ghost" size="sm" asChild>
                    <Link to="/policies">View All</Link>
                  </Button>
                }
              />
              <CardContent className="p-0">
                {activePolicies.length > 0 ? (
                  <div className="divide-y divide-gray-200">
                    {activePolicies.map((policy) => (
                      <Link key={policy.id} to={`/policies/${policy.id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-medium text-gray-900">{policy.type}</span>
                              <StatusBadge status={policy.status} />
                            </div>
                            <p className="text-sm text-gray-500 mt-1 truncate">
                              {policy.vehicle ? `${policy.vehicle.make} ${policy.vehicle.model} (${policy.vehicle.year})` : policy.property?.address}
                            </p>
                            <p className="text-sm text-gray-500">Expires {formatDate(policy.endDate)}</p>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="font-semibold text-gray-900">{formatCurrency(policy.premium)}/yr</p>
                            <p className="text-xs text-gray-500">Deductible: {formatCurrency(policy.deductible)}</p>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<FileText className="w-12 h-12" />}
                    title="No active policies"
                    description="You don't have any active policies at the moment."
                  />
                )}
              </CardContent>
            </Card>
          </ErrorBoundary>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {quickActions.map((action) => (
          <Link key={action.label} to={action.href} className="card group">
            <CardContent className="p-6 flex flex-col items-center text-center">
              <div className={clsx('w-14 h-14 rounded-xl flex items-center justify-center mb-4 transition-colors', action.color)}>
                <action.icon className="w-7 h-7" />
              </div>
              <h3 className="font-semibold text-gray-900 group-hover:text-primary transition-colors">{action.label}</h3>
              <p className="text-sm text-gray-500 mt-1">Click to get started</p>
            </CardContent>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default CustomerDashboard
