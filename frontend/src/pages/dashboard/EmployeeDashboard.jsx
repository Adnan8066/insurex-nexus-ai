import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
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
  Users,
  Wrench,
  Gavel,
  Brain,
  BarChart3,
  RefreshCw,
  Download,
  Calendar,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatCurrencyCompact, formatDate, formatRelativeTime } from '../../utils/helpers'
import { policyService, claimService, vehicleService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ChartCard, MetricChart, AreaChart, BarChart, DoughnutChart } from '../../components/charts/ChartComponents'
import { EmptyState } from '../../components/ui/EmptyState'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import ErrorBoundary, { ChartErrorFallback, DataTableErrorFallback } from '../../components/ui/ErrorBoundary'
import { DashboardSkeleton, ChartSkeleton, TableSkeleton, SkeletonCard } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/toastHooks'
import { useAnalytics, useAutoRefresh } from '../../hooks/useAnalytics'
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

export function EmployeeDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  const [loading, setLoading] = useState(true)
  const [claims, setClaims] = useState([])
  const [policies, setPolicies] = useState([])
  const [fraudAlerts, setFraudAlerts] = useState([])
  const [recentActivity, setRecentActivity] = useState([])
  const [timeframe, setTimeframe] = useState(searchParams.get('timeframe') || 'quarter')
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [connectionError, setConnectionError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(new Date())

  const mapClaim = (c) => ({
    id: c.id,
    claimNumber: c.claim_number,
    customerName: c.customer_name,
    customerEmail: c.customer_email,
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
    assignedAdjuster: c.assigned_adjuster_name,
    assignedInvestigator: c.assigned_investigator_name,
    fraudRiskScore: c.fraud_risk_score,
    totalLossProbability: c.total_loss_probability,
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
    customerEmail: p.customer_email,
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

  const fetchData = useCallback(async (timeframeParam = timeframe) => {
    setRefreshing(true)
    setConnectionError(null)
    try {
      const [clmRes, polRes] = await Promise.all([
        claimService.getClaims(),
        policyService.getPolicies(),
      ])
      const clms = Array.isArray(clmRes) ? clmRes : (clmRes.results || [])
      const pols = Array.isArray(polRes) ? polRes : (polRes.results || [])
      setClaims(clms.map(mapClaim))
      setPolicies(pols.map(mapPolicy))
      setFraudAlerts(clms.filter((c) => (c.fraud_risk_score || 0) >= 50 || (c.priority === 'high' || c.priority === 'critical')).map(mapClaim))
      setRecentActivity(
        clms.slice(0, 5).map((c, i) => ({
          id: c.id || i,
          type: 'claim',
          title: `Claim ${c.claim_number} - ${c.status?.replace(/_/g, ' ')}`,
          detail: `${c.customer_name || 'Customer'} • ${c.incident_type?.replace(/_/g, ' ') || 'N/A'}`,
          time: c.submitted_at ? formatRelativeTime(c.submitted_at) : 'N/A',
          icon: Briefcase,
          color: 'text-blue-600 bg-blue-50',
        }))
      )
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

  useAutoRefresh(autoRefresh, 60000, () => fetchData(timeframe))

  const activePolicies = policies.filter((p) => p.status === 'active')
  const activeClaims = claims.filter((c) => !['closed', 'rejected'].includes(c.status))
  const pendingClaims = claims.filter((c) => ['submitted', 'under_review', 'ai_assessment', 'investigation'].includes(c.status))
  const highRiskClaims = fraudAlerts.filter((f) => f.riskLevel === 'high')
  const totalLossCases = claims.filter((c) => c.status === 'total_loss' || c.aiAssessment?.totalLossProbability > 50)
  const totalClaimAmount = claims.reduce((sum, c) => sum + c.claimAmount, 0)
  const avgClaimCost = claims.length > 0 ? totalClaimAmount / claims.length : 0

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
          '#3b82f6', '#f59e0b', '#1e3a5f', '#f59e0b', '#10b981', '#ef4444', '#1e3a5f', '#94a3b8',
        ],
        borderWidth: 0,
      },
    ],
  }), [claimsByStatus])

  const fraudRiskData = useMemo(() => ({
    labels: ['Low', 'Medium', 'High'],
    datasets: [
      {
        data: [
          fraudAlerts.filter((f) => f.riskLevel === 'low').length,
          fraudAlerts.filter((f) => f.riskLevel === 'medium').length,
          fraudAlerts.filter((f) => f.riskLevel === 'high').length,
        ],
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
        borderWidth: 0,
      },
    ],
  }), [fraudAlerts])

  const monthlyData = useMemo(() => ({
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
    datasets: [
      {
        label: 'New Claims',
        data: [12, 19, 15, 22, 18, 25, 20],
        borderColor: '#1e3a5f',
        backgroundColor: 'rgba(30, 58, 95, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Resolved Claims',
        data: [8, 15, 12, 18, 14, 20, 16],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  }), [])

  const recentClaims = [...claims].sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt)).slice(0, 5)

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
      link.download = `executive-report-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      toast.showSuccess('Executive report exported successfully')
    } catch (err) {
      toast.showError('Failed to export report')
    }
  }

  const metricCards = [
    {
      title: 'Total Policies',
      value: policies.length,
      icon: FileText,
      iconColor: 'text-blue-600',
      bgColor: 'bg-blue-50',
      trend: 'Live count',
      trendLabel: 'current records',
      link: '/policies',
    },
    {
      title: 'Active Claims',
      value: activeClaims.length,
      icon: Briefcase,
      iconColor: 'text-purple-600',
      bgColor: 'bg-purple-50',
      trend: 'Live count',
      trendLabel: 'current records',
      link: '/claims',
    },
    {
      title: 'Pending Claims',
      value: pendingClaims.length,
      icon: Clock,
      iconColor: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
      trend: 'Live count',
      trendLabel: 'current records',
      link: '/claims?status=pending',
    },
    {
      title: 'Fraud Alerts',
      value: highRiskClaims.length,
      icon: AlertTriangle,
      iconColor: 'text-red-600',
      bgColor: 'bg-red-50',
      trend: 'Live count',
      trendLabel: 'current records',
      link: '/fraud',
    },
  ]

  const totalLossCards = [
    {
      title: 'Total Loss Cases',
      value: totalLossCases.length,
      icon: AlertTriangle,
      iconColor: 'text-orange-600',
      bgColor: 'bg-orange-50',
      trend: 'Live count',
      trendLabel: 'current records',
      link: '/claims?status=total_loss',
    },
  ]

  const quickActions = [
    { label: 'Review Claims', href: '/claims', icon: Briefcase, color: 'bg-blue-50 text-blue-600 hover:bg-blue-100' },
    { label: 'Fraud Investigation', href: '/fraud', icon: AlertTriangle, color: 'bg-red-50 text-red-600 hover:bg-red-100' },
    { label: 'AI Assessment', href: '/ai-assessment', icon: Brain, color: 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100' },
    { label: 'Analytics', href: '/analytics', icon: BarChart3, color: 'bg-green-50 text-green-600 hover:bg-green-100' },
  ]

  if (loading) {
    return <DashboardSkeleton />
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Employee Dashboard</h1>
          <p className="page-subtitle">Insurance operations overview and key metrics</p>
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
            Export Executive Report
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
            <Card hover className="group cursor-pointer" onClick={() => navigate(metric.link)}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">{metric.title}</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">{metric.value}</p>
                    <div className="flex items-center gap-1 mt-2 text-sm font-medium text-green-600">
                      <TrendingUp className="w-4 h-4" />
                      <span>{metric.trend}</span>
                      <span className="text-gray-500">{metric.trendLabel}</span>
                    </div>
                  </div>
                  <div className={clsx('w-12 h-12 rounded-xl flex items-center justify-center', metric.bgColor, metric.iconColor)}>
                    <metric.icon className="w-6 h-6" />
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-gray-100 flex items-center text-sm text-gray-500 group-hover:text-primary transition-colors">
                  <span>View details</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </div>
              </CardContent>
            </Card>
          </ErrorBoundary>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <ErrorBoundary fallback={({ resetError, retryCount }) => (
          <ChartErrorFallback title="Claims Over Time" resetError={resetError} retryCount={retryCount} />
        )}>
          <ChartCard
            title="Claims Over Time"
            subtitle={`New vs resolved claims (${TIMEFRAME_OPTIONS.find((t) => t.value === timeframe)?.label})`}
            action={
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Clock className="w-4 h-4" />
                <span>Updated {formatRelativeTime(lastUpdated)}</span>
              </div>
            }
          >
            <AreaChart data={monthlyData} height={300} />
          </ChartCard>
        </ErrorBoundary>

        <div className="grid grid-cols-1 gap-6">
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <ChartErrorFallback title="Claim Status Distribution" resetError={resetError} retryCount={retryCount} />
          )}>
            <ChartCard title="Claim Status Distribution" subtitle="Current pipeline status">
              <DoughnutChart data={claimStatusData} height={250} />
            </ChartCard>
          </ErrorBoundary>

          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <ChartErrorFallback title="Fraud Risk Distribution" resetError={resetError} retryCount={retryCount} />
          )}>
            <ChartCard title="Fraud Risk Distribution" subtitle="Risk levels across flagged claims">
              <DoughnutChart data={fraudRiskData} height={250} />
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
                subtitle="Latest claims requiring attention"
                action={
                  <Button variant="ghost" size="sm" asChild>
                    <Link to="/claims">View All <ArrowRight className="w-4 h-4 ml-1" /></Link>
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
                        <TableHead className="w-24">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {recentClaims.map((claim) => (
                        <TableRow key={claim.id} clickable onClick={() => navigate(`/claims/${claim.id}`)}>
                          <TableCell className="font-mono font-medium">{claim.claimNumber}</TableCell>
                          <TableCell>{claim.customerName}</TableCell>
                          <TableCell>{claim.incidentType}</TableCell>
                          <TableCell className="font-medium">{formatCurrency(claim.claimAmount)}</TableCell>
                          <TableCell><StatusBadge status={claim.status} /></TableCell>
                          <TableCell>
                            <Badge variant={claim.aiAssessment?.claimPriority === 'High' ? 'danger' : claim.aiAssessment?.claimPriority === 'Medium' ? 'warning' : 'success'}>
                              {claim.aiAssessment?.claimPriority || 'Medium'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-gray-600">{claim.assignedAdjuster || 'Unassigned'}</TableCell>
                          <TableCell>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </TableCell>
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
        <div>
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <DataTableErrorFallback title="High-Risk Fraud Alerts" resetError={resetError} retryCount={retryCount} />
          )}>
            <Card>
              <CardHeader
                title="High-Risk Fraud Alerts"
                subtitle="Claims requiring investigation"
              />
              <CardContent className="p-0">
                {fraudAlerts.length > 0 ? (
                  <div className="divide-y divide-gray-200">
                    {fraudAlerts.slice(0, 5).map((alert) => (
                      <Link key={alert.id} to={`/fraud/${alert.id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-semibold text-gray-900">{alert.claimNumber}</span>
                              <Badge variant={alert.riskLevel === 'high' ? 'danger' : alert.riskLevel === 'medium' ? 'warning' : 'success'}>
                                {alert.riskLevel} risk
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-600 mt-1">{alert.customerName}</p>
                            <p className="text-xs text-gray-500">Score: {alert.fraudRiskScore}% â€¢ {formatRelativeTime(alert.createdAt)}</p>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <span className="text-lg font-bold text-gray-900">{alert.fraudRiskScore}%</span>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<Shield className="w-12 h-12" />}
                    title="No fraud alerts"
                    description="No high-risk claims detected at this time."
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
            </CardContent>
          </Link>
        ))}
      </div>
    </div>
  )
}


export default EmployeeDashboard

