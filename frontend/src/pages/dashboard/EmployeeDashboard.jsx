import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  FileText,
  Briefcase,
  Clock,
  AlertTriangle,
  Shield,
  ArrowRight,
  Brain,
  BarChart3,
  RefreshCw,
  Download,
  Calendar,
  WifiOff,
} from 'lucide-react'
import { clsx } from 'clsx'
import { format, parseISO } from 'date-fns'
import { formatCurrency, formatCurrencyCompact, formatRelativeTime } from '../../utils/helpers'
import { policyService, claimService, analyticsService } from '../../services'
import { formatApiError } from '../../services/api'
import {
  CLAIM_STATUSES,
  PENDING_CLAIM_STATUSES,
  INCIDENT_TYPES,
  CLAIM_PRIORITIES,
  fraudRiskLevel,
  labelFor,
} from '../../constants/domain'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ChartCard, ComboChart, DoughnutChart } from '../../components/charts/ChartComponents'
import { EmptyState } from '../../components/ui/EmptyState'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import ErrorBoundary, { ChartErrorFallback, DataTableErrorFallback } from '../../components/ui/ErrorBoundary'
import { DashboardSkeleton } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/toastHooks'

const TIMEFRAME_OPTIONS = [
  { value: 'week', label: 'Last 7 Days' },
  { value: 'month', label: 'Last 30 Days' },
  { value: 'quarter', label: 'Current Quarter' },
  { value: 'ytd', label: 'Year to Date' },
  { value: 'year', label: 'Last Year' },
]

// Short ranges are shown per day; longer ones per month (same as the Analytics page).
const TREND_GRANULARITY = { week: 'day', month: 'day', quarter: 'month', ytd: 'month', year: 'month' }

// Matches the backend total-loss threshold used by the dashboard summary.
const TOTAL_LOSS_THRESHOLD = 50

const STATUS_COLORS = ['#3b82f6', '#f59e0b', '#1e3a5f', '#d97706', '#10b981', '#ef4444', '#6366f1', '#94a3b8']
const RISK_VARIANT = { high: 'danger', medium: 'warning', low: 'success' }
const PRIORITY_VARIANT = { critical: 'danger', high: 'danger', medium: 'warning', low: 'success' }

const mapClaim = (c) => ({
  id: c.id,
  claimNumber: c.claim_number,
  customerName: c.customer_name,
  incidentType: c.incident_type,
  claimAmount: Number(c.claim_amount) || 0,
  status: c.status,
  priority: String(c.priority || c.ai_assessment?.claim_priority || '').toLowerCase(),
  submittedAt: c.submitted_at,
  assignedAdjuster: c.assigned_adjuster_name,
  fraudRiskScore: Number(c.fraud_risk_score) || 0,
  riskLevel: fraudRiskLevel(c.fraud_risk_score),
  totalLossProbability: Number(c.total_loss_probability ?? c.ai_assessment?.total_loss_probability) || 0,
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
})

export function EmployeeDashboard() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  const initialTimeframe = searchParams.get('timeframe')
  const [timeframe, setTimeframe] = useState(
    TIMEFRAME_OPTIONS.some((o) => o.value === initialTimeframe) ? initialTimeframe : 'quarter'
  )
  const [loading, setLoading] = useState(true)
  const [claims, setClaims] = useState([])
  const [policies, setPolicies] = useState([])
  const [summary, setSummary] = useState(null)
  const [fraudBands, setFraudBands] = useState(null)
  const [trend, setTrend] = useState([])
  const [refreshing, setRefreshing] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [connectionError, setConnectionError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(new Date())

  const granularity = TREND_GRANULARITY[timeframe] || 'day'

  const fetchData = useCallback(async () => {
    setRefreshing(true)
    setConnectionError(null)
    try {
      const [clmRes, polRes, summaryRes, fraudRes, trendRes] = await Promise.all([
        claimService.getClaims(),
        policyService.getPolicies(),
        analyticsService.getDashboardSummary(timeframe),
        analyticsService.getFraudRiskDistribution(timeframe),
        analyticsService.getClaimsTrendForTimeframe(timeframe, granularity),
      ])
      const clms = Array.isArray(clmRes) ? clmRes : (clmRes?.results || [])
      const pols = Array.isArray(polRes) ? polRes : (polRes?.results || [])
      setClaims(clms.map(mapClaim))
      setPolicies(pols.map(mapPolicy))
      setSummary(summaryRes || null)
      setFraudBands(fraudRes?.by_level || null)
      setTrend(Array.isArray(trendRes) ? trendRes : [])
      setLastUpdated(new Date())
    } catch (err) {
      const message = formatApiError(err, 'Unable to load dashboard data.')
      setConnectionError(message)
      toast.error(message, {
        action: { label: 'Retry', onClick: () => fetchData(), persist: false },
      })
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }, [timeframe, granularity, toast])

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
    if (params.toString() !== searchParams.toString()) {
      setSearchParams(params, { replace: true })
    }
  }, [timeframe, searchParams, setSearchParams])

  const timeframeLabel = TIMEFRAME_OPTIONS.find((t) => t.value === timeframe)?.label || 'Selected period'
  const summaryClaims = summary?.claims || {}
  const byStatus = useMemo(() => summary?.claims?.by_status || {}, [summary])
  const periodClaimCount = summaryClaims.total || 0
  const pendingCount = PENDING_CLAIM_STATUSES.reduce((sum, status) => sum + (byStatus[status] || 0), 0)
  const highRiskCount = summary?.fraud?.high_risk_claims ?? fraudBands?.high ?? 0
  const totalLossCount = summaryClaims.total_loss_cases ?? 0
  const activePolicyCount = summary?.policies?.active ?? policies.filter((p) => p.status === 'active').length

  const claimStatusData = useMemo(() => ({
    labels: CLAIM_STATUSES.map((s) => s.label),
    datasets: [
      {
        data: CLAIM_STATUSES.map((s) => byStatus[s.value] || 0),
        backgroundColor: STATUS_COLORS,
        borderWidth: 0,
      },
    ],
  }), [byStatus])

  const fraudRiskData = useMemo(() => ({
    labels: ['Low', 'Medium', 'High'],
    datasets: [
      {
        data: [fraudBands?.low || 0, fraudBands?.medium || 0, fraudBands?.high || 0],
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
        borderWidth: 0,
      },
    ],
  }), [fraudBands])

  const hasTrendData = trend.some((d) => d.count > 0)
  const claimsOverTimeData = {
    labels: trend.map((d) => format(parseISO(String(d.date)), granularity === 'month' ? 'MMM yyyy' : 'd MMM')),
    datasets: [
      {
        type: 'bar',
        label: 'Claims submitted',
        data: trend.map((d) => d.count),
        backgroundColor: '#1e3a5f',
        borderRadius: 4,
        maxBarThickness: 36,
        yAxisID: 'y',
        order: 2,
      },
      {
        type: 'line',
        label: 'Claim amount',
        data: trend.map((d) => Math.round(Number(d.total_amount) || 0)),
        borderColor: '#10b981',
        backgroundColor: '#10b981',
        pointRadius: 3,
        tension: 0.3,
        yAxisID: 'y1',
        order: 1,
      },
    ],
  }
  const claimsOverTimeOptions = {
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'Claims' }, ticks: { precision: 0 } },
      y1: {
        beginAtZero: true,
        position: 'right',
        grid: { drawOnChartArea: false },
        title: { display: true, text: 'Amount' },
        ticks: { callback: (value) => formatCurrencyCompact(value) },
      },
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) => (ctx.dataset.yAxisID === 'y1'
            ? `${ctx.dataset.label}: ${formatCurrency(ctx.raw)}`
            : `${ctx.dataset.label}: ${ctx.raw}`),
        },
      },
    },
  }

  const recentClaims = [...claims].sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt)).slice(0, 5)
  const fraudAlerts = claims
    .filter((c) => c.riskLevel !== 'low')
    .sort((a, b) => b.fraudRiskScore - a.fraudRiskScore)

  const handleExport = () => {
    setExporting(true)
    try {
      const csvCell = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`
      const totalClaimAmount = claims.reduce((sum, c) => sum + c.claimAmount, 0)
      const rows = [
        ['Claims and Policies Report'],
        ['Reporting period', timeframeLabel],
        ['Generated at', new Date().toLocaleString()],
        ['Claims in period', periodClaimCount],
        ['Pending claims in period', pendingCount],
        ['High fraud risk claims in period', highRiskCount],
        ['Likely total loss claims in period', totalLossCount],
        ['Active policies', activePolicyCount],
        [],
        ['Claims (latest)'],
        ['Claim number', 'Customer', 'Status', 'Incident type', 'Submitted', 'Amount', 'Priority', 'Fraud risk'],
        ...claims.map((claim) => [
          claim.claimNumber,
          claim.customerName,
          labelFor(CLAIM_STATUSES, claim.status),
          labelFor(INCIDENT_TYPES, claim.incidentType),
          claim.submittedAt,
          claim.claimAmount,
          labelFor(CLAIM_PRIORITIES, claim.priority),
          claim.riskLevel,
        ]),
        ['Total claim amount', '', '', '', '', totalClaimAmount],
        [],
        ['Policies'],
        ['Policy number', 'Customer', 'Type', 'Status', 'Start date', 'End date', 'Premium'],
        ...policies.map((policy) => [policy.policyNumber, policy.customerName, policy.type, policy.status, policy.startDate, policy.endDate, policy.premium]),
      ]
      const report = rows.map((row) => row.map(csvCell).join(',')).join('\r\n')
      const blob = new Blob([report], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `claims-report-${format(new Date(), 'yyyy-MM-dd')}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      toast.success('Report downloaded')
    } catch {
      toast.error('Failed to export report')
    } finally {
      setExporting(false)
    }
  }

  const metricCards = [
    {
      title: 'Active Policies',
      value: activePolicyCount,
      caption: 'In force during the period',
      icon: FileText,
      iconColor: 'text-blue-600',
      bgColor: 'bg-blue-50',
      link: '/policies',
    },
    {
      title: 'Claims',
      value: periodClaimCount,
      caption: `Submitted · ${timeframeLabel}`,
      icon: Briefcase,
      iconColor: 'text-purple-600',
      bgColor: 'bg-purple-50',
      link: '/claims',
    },
    {
      title: 'Pending Claims',
      value: pendingCount,
      caption: 'Waiting for a decision',
      icon: Clock,
      iconColor: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
      link: '/claims?status=pending',
    },
    {
      title: 'High Fraud Risk',
      value: highRiskCount,
      caption: 'Claims with a high fraud score',
      icon: AlertTriangle,
      iconColor: 'text-red-600',
      bgColor: 'bg-red-50',
      link: '/fraud',
    },
    {
      title: 'Likely Total Loss',
      value: totalLossCount,
      caption: `${TOTAL_LOSS_THRESHOLD}%+ total-loss probability`,
      icon: Shield,
      iconColor: 'text-orange-600',
      bgColor: 'bg-orange-50',
      link: '/claims',
    },
  ]

  const quickActions = [
    { label: 'Review Claims', href: '/claims', icon: Briefcase, color: 'bg-blue-50 text-blue-600 hover:bg-blue-100' },
    { label: 'Fraud Alerts', href: '/fraud', icon: AlertTriangle, color: 'bg-red-50 text-red-600 hover:bg-red-100' },
    { label: 'Claim Assessment', href: '/ai-assessment', icon: Brain, color: 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100' },
    { label: 'Analytics', href: '/analytics', icon: BarChart3, color: 'bg-green-50 text-green-600 hover:bg-green-100' },
  ]

  if (loading) {
    return <DashboardSkeleton />
  }

  return (
    <div className="page">
      <div className="page-header flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Claims and policies at a glance</p>
          {connectionError && (
            <div className="mt-2 flex items-center gap-2 text-sm text-red-600" role="alert">
              <WifiOff className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              <span>{connectionError}</span>
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" aria-hidden="true" />
            <span className="sr-only">Time period</span>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-primary focus:border-primary"
            >
              {TIMEFRAME_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <Button variant="ghost" size="sm" onClick={() => fetchData()} loading={refreshing} aria-label="Refresh dashboard" title="Refresh dashboard">
            <RefreshCw className="w-4 h-4" />
          </Button>

          <Button variant="primary" size="sm" onClick={handleExport} loading={exporting} disabled={exporting}>
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-6 mb-8">
        {metricCards.map((metric) => (
          <Card key={metric.title} hover className="group cursor-pointer" onClick={() => navigate(metric.link)}>
            <CardContent className="p-6">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-500">{metric.title}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{metric.value}</p>
                  <p className="mt-2 text-xs text-gray-500">{metric.caption}</p>
                </div>
                <div className={clsx('w-12 h-12 flex-shrink-0 rounded-xl flex items-center justify-center', metric.bgColor, metric.iconColor)}>
                  <metric.icon className="w-6 h-6" aria-hidden="true" />
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-gray-100 flex items-center text-sm text-gray-500 group-hover:text-primary transition-colors">
                <span>View details</span>
                <ArrowRight className="w-4 h-4 ml-1" aria-hidden="true" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <ErrorBoundary fallback={({ resetError, retryCount }) => (
          <ChartErrorFallback title="Claims Over Time" resetError={resetError} retryCount={retryCount} />
        )}>
          <ChartCard
            title="Claims Over Time"
            subtitle={`${granularity === 'month' ? 'Monthly' : 'Daily'} claims and claim amount · ${timeframeLabel}`}
            action={
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Clock className="w-4 h-4" aria-hidden="true" />
                <span>Updated {formatRelativeTime(lastUpdated)}</span>
              </div>
            }
          >
            {hasTrendData ? (
              <ComboChart data={claimsOverTimeData} options={claimsOverTimeOptions} height={300} />
            ) : (
              <div className="flex items-center justify-center text-center text-sm text-gray-400" style={{ height: 300 }}>
                No claims were submitted in this period.
              </div>
            )}
          </ChartCard>
        </ErrorBoundary>

        <div className="grid grid-cols-1 gap-6">
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <ChartErrorFallback title="Claim Status" resetError={resetError} retryCount={retryCount} />
          )}>
            <ChartCard title="Claim Status" subtitle={`Claims by stage · ${timeframeLabel}`}>
              <DoughnutChart data={claimStatusData} height={250} />
            </ChartCard>
          </ErrorBoundary>

          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <ChartErrorFallback title="Fraud Risk" resetError={resetError} retryCount={retryCount} />
          )}>
            <ChartCard title="Fraud Risk" subtitle={`Claims by fraud risk level · ${timeframeLabel}`}>
              <DoughnutChart data={fraudRiskData} height={250} />
            </ChartCard>
          </ErrorBoundary>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 min-w-0">
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <DataTableErrorFallback title="Recent Claims" resetError={resetError} retryCount={retryCount} />
          )}>
            <Card>
              <CardHeader
                title="Recent Claims"
                subtitle="Latest claims submitted"
                action={
                  <Button variant="ghost" size="sm" asChild>
                    <Link to="/claims">View All <ArrowRight className="w-4 h-4 ml-1" aria-hidden="true" /></Link>
                  </Button>
                }
              />
              <CardContent className="p-0">
                {recentClaims.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Claim ID</TableHead>
                        <TableHead>Customer</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Priority</TableHead>
                        <TableHead>Assigned</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {recentClaims.map((claim) => (
                        <TableRow key={claim.id} clickable onClick={() => navigate(`/claims/${claim.id}`)}>
                          <TableCell className="font-mono font-medium">{claim.claimNumber}</TableCell>
                          <TableCell>{claim.customerName || '—'}</TableCell>
                          <TableCell>{labelFor(INCIDENT_TYPES, claim.incidentType)}</TableCell>
                          <TableCell className="font-medium">{formatCurrency(claim.claimAmount)}</TableCell>
                          <TableCell><StatusBadge status={claim.status} /></TableCell>
                          <TableCell>
                            {claim.priority ? (
                              <Badge variant={PRIORITY_VARIANT[claim.priority] || 'neutral'}>
                                {labelFor(CLAIM_PRIORITIES, claim.priority)}
                              </Badge>
                            ) : '—'}
                          </TableCell>
                          <TableCell className="text-sm text-gray-600">{claim.assignedAdjuster || 'Unassigned'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="p-8">
                    <EmptyState
                      title="No recent claims"
                      description="No claims have been submitted recently."
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </ErrorBoundary>
        </div>
        <div className="min-w-0">
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <DataTableErrorFallback title="Fraud Alerts" resetError={resetError} retryCount={retryCount} />
          )}>
            <Card>
              <CardHeader
                title="Fraud Alerts"
                subtitle="Claims with a medium or high fraud score"
              />
              <CardContent className="p-0">
                {fraudAlerts.length > 0 ? (
                  <div className="divide-y divide-gray-200">
                    {fraudAlerts.slice(0, 5).map((alert) => (
                      <Link key={alert.id} to={`/claims/${alert.id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-semibold text-gray-900">{alert.claimNumber}</span>
                              <Badge variant={RISK_VARIANT[alert.riskLevel]}>
                                {alert.riskLevel} risk
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-600 mt-1">{alert.customerName || '—'}</p>
                            {alert.submittedAt && (
                              <p className="text-xs text-gray-500">Submitted {formatRelativeTime(alert.submittedAt)}</p>
                            )}
                          </div>
                          <div className="text-right flex-shrink-0">
                            <span className="text-lg font-bold text-gray-900">{Math.round(alert.fraudRiskScore)}%</span>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<Shield className="w-12 h-12" />}
                    title="No fraud alerts"
                    description="No risky claims detected at this time."
                  />
                )}
              </CardContent>
            </Card>
          </ErrorBoundary>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {quickActions.map((action) => (
          <Link key={action.label} to={action.href} className="card group">
            <CardContent className="p-6 flex flex-col items-center text-center">
              <div className={clsx('w-14 h-14 rounded-xl flex items-center justify-center mb-4 transition-colors', action.color)}>
                <action.icon className="w-7 h-7" aria-hidden="true" />
              </div>
              <h3 className="font-semibold text-gray-900 group-hover:text-primary transition-colors">{action.label}</h3>
            </CardContent>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default EmployeeDashboard
