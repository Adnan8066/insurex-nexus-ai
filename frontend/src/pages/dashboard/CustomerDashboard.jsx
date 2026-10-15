import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  FileText,
  Briefcase,
  Clock,
  CheckCircle,
  Headphones,
  DollarSign,
  ArrowRight,
  RefreshCw,
  Download,
  Calendar,
  WifiOff,
  FilePlus2,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { policyService, claimService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ChartCard, AreaChart, DoughnutChart } from '../../components/charts/ChartComponents'
import { EmptyState } from '../../components/ui/EmptyState'

import ErrorBoundary, {
  ChartErrorFallback,
  DataTableErrorFallback,
} from '../../components/ui/ErrorBoundary'

import { DashboardSkeleton } from '../../components/ui/Skeleton'
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
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  const [loading, setLoading] = useState(true)
  const [policies, setPolicies] = useState([])
  const [claims, setClaims] = useState([])
  const [timeframe, setTimeframe] = useState(searchParams.get('timeframe') || 'quarter')
  const [refreshing, setRefreshing] = useState(false)
  const [connectionError, setConnectionError] = useState(null)

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

  const fetchData = useCallback(async () => {
    setRefreshing(true)
    setConnectionError(null)
    try {
      const [polRes, clmRes] = await Promise.all([
        policyService.getPolicies(),
        claimService.getClaims(),
      ])
      const pols = Array.isArray(polRes) ? polRes : (polRes.results || [])
      const clms = Array.isArray(clmRes) ? clmRes : (clmRes.results || [])
      setPolicies(pols.map(mapPolicy))
      setClaims(clms.map(mapClaim))
      setConnectionError(null)
    } catch (err) {
      setConnectionError(err.response?.data?.detail || err.message || 'Backend unreachable')
      toast.showRetryToast('Connection error. Unable to load dashboard data.', () => fetchData())
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    const params = new URLSearchParams(searchParams)
    if (timeframe !== 'quarter') {
      params.set('timeframe', timeframe)
    } else {
      params.delete('timeframe')
    }
    setSearchParams(params, { replace: true })
  }, [timeframe, searchParams, setSearchParams])

  const activePolicies = policies.filter((p) => p.status === 'active')
  const pendingClaims = claims.filter((c) => ['submitted', 'under_review', 'ai_assessment', 'investigation'].includes(c.status))
  const approvedClaims = claims.filter((c) => c.status === 'approved')
  const recentClaims = [...claims].sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt)).slice(0, 5)

  const claimStatusData = useMemo(() => {
    const claimsByStatus = claims.reduce((acc, claim) => {
      acc[claim.status] = (acc[claim.status] || 0) + 1
      return acc
    }, {})

    return {
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
    }
  }, [claims])

  const monthlyClaimsData = useMemo(() => {
    const today = new Date()
    const option = TIMEFRAME_OPTIONS.find((item) => item.value === timeframe) || TIMEFRAME_OPTIONS[2]
    const start = new Date(today)
    const periodEnd = new Date(today)
    if (timeframe === 'ytd') start.setMonth(0, 1)
    else if (timeframe === 'year') {
      start.setFullYear(today.getFullYear() - 1, 0, 1)
      periodEnd.setFullYear(today.getFullYear() - 1, 11, 31)
      periodEnd.setHours(23, 59, 59, 999)
    } else if (timeframe === 'quarter') {
      start.setMonth(Math.floor(today.getMonth() / 3) * 3, 1)
    } else start.setDate(today.getDate() - option.days + 1)
    start.setHours(0, 0, 0, 0)
    const daily = timeframe === 'week' || timeframe === 'month'
    const labels = []
    const counts = []
    const bucketDates = []
    const cursor = new Date(start)
    while (cursor <= periodEnd) {
      const bucketDate = new Date(cursor)
      if (!daily) bucketDate.setDate(1)
      const key = daily
        ? `${bucketDate.getFullYear()}-${bucketDate.getMonth()}-${bucketDate.getDate()}`
        : `${bucketDate.getFullYear()}-${bucketDate.getMonth()}`
      if (!bucketDates.includes(key)) {
        bucketDates.push(key)
        labels.push(daily
          ? bucketDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
          : bucketDate.toLocaleDateString(undefined, { month: 'short' }))
        counts.push(0)
      }
      cursor.setDate(cursor.getDate() + 1)
    }
    claims.forEach((claim) => {
      if (!claim.submittedAt) return
      const submittedAt = new Date(claim.submittedAt)
      if (Number.isNaN(submittedAt.getTime()) || submittedAt < start || submittedAt > periodEnd) return
      const key = daily
        ? `${submittedAt.getFullYear()}-${submittedAt.getMonth()}-${submittedAt.getDate()}`
        : `${submittedAt.getFullYear()}-${submittedAt.getMonth()}`
      const index = bucketDates.indexOf(key)
      if (index >= 0) counts[index] += 1
    })
    return {
      labels,
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
  }, [claims, timeframe])

  const handleTimeframeChange = (newTimeframe) => {
    setTimeframe(newTimeframe)
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

  const quickActions = [
    { label: 'File a Claim', href: '/claims/new', icon: FilePlus2, color: 'bg-blue-50 text-blue-700 hover:bg-blue-100', description: 'Start a new claim' },
    { label: 'Make a Payment', href: '/settlements', icon: DollarSign, color: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100', description: 'Review payments and settlements' },
    { label: 'Get Support', href: '/notifications', icon: Headphones, color: 'bg-violet-50 text-violet-700 hover:bg-violet-100', description: 'View updates about your account' },
  ]

  const firstName = user?.first_name || user?.firstName || user?.name?.trim().split(/\s+/)[0] || user?.get_full_name?.call(user)?.trim().split(/\s+/)[0] || user?.email?.split('@')[0] || 'there'

  if (loading) {
    return <DashboardSkeleton />
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Welcome back, {firstName}! Here&apos;s an overview of your insurance portfolio.</p>
          {connectionError && (
            <div className="mt-2 flex items-center gap-2 text-sm text-red-600">
              <WifiOff className="w-4 h-4" />
              <span>Connection error: {connectionError}</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm mb-6">
        <p className="text-sm text-slate-500">Your coverage and claims, at a glance</p>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-500" />
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

          <Button variant="ghost" size="sm" className="relative" onClick={() => fetchData()} loading={refreshing} aria-label="Refresh dashboard" title="Refresh dashboard">
            <RefreshCw className="w-4 h-4" />
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

      {claims.length === 0 ? (
        <section className="mb-8 overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-8 shadow-sm sm:p-10">
          <div className="mx-auto max-w-xl text-center">
            <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
              <FilePlus2 className="h-7 w-7" aria-hidden="true" />
            </div>
            <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-700">Your dashboard is ready</p>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Your claims activity will appear here</h2>
            <p className="mt-2 text-slate-600">When you file a claim, you can follow its progress and see updates in this space.</p>
            <Button asChild variant="primary" className="mt-6">
              <Link to="/claims/new">File a Claim <ArrowRight className="ml-2 h-4 w-4" /></Link>
            </Button>
          </div>
        </section>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2">
            <ErrorBoundary fallback={({ resetError, retryCount }) => (
              <ChartErrorFallback title="Claims Overview" resetError={resetError} retryCount={retryCount} />
            )}>
              <ChartCard title="Claims Overview" subtitle={`Claims submitted (${TIMEFRAME_OPTIONS.find((t) => t.value === timeframe)?.label})`}>
                <AreaChart data={monthlyClaimsData} height={300} options={{ scales: { y: { min: 0, beginAtZero: true } } }} />
              </ChartCard>
            </ErrorBoundary>
          </div>
          <div>
            <ErrorBoundary fallback={({ resetError, retryCount }) => (
              <ChartErrorFallback title="Claim Status Distribution" resetError={resetError} retryCount={retryCount} />
            )}>
              <ChartCard title="Claim Status Distribution" subtitle="Current status of your claims">
                <DoughnutChart data={claimStatusData} height={300} />
              </ChartCard>
            </ErrorBoundary>
          </div>
        </div>
      )}

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
                    description="Your recent claim activity will appear here."
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
        {quickActions.filter((action) => claims.length > 0 || action.label !== 'File a Claim').map((action) => (
          <Link key={action.label} to={action.href} className="card group">
            <CardContent className="p-6 flex flex-col items-center text-center">
              <div className={clsx('w-14 h-14 rounded-xl flex items-center justify-center mb-4 transition-colors', action.color)}>
                <action.icon className="w-7 h-7" />
              </div>
              <h3 className="font-semibold text-gray-900 group-hover:text-primary transition-colors">{action.label}</h3>
              <p className="text-sm text-gray-500 mt-1">{action.description}</p>
            </CardContent>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default CustomerDashboard
