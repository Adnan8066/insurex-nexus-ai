import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
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
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { mockPolicies, mockPolicyStats } from '../../data/policies'
import { mockClaims, mockClaimStats } from '../../data/claims'
import { mockVehicles } from '../../data/vehicles'
import { mockSettlements, mockSettlementStats } from '../../data/settlements'
import { mockInvestigators } from '../../data/operations'
import { mockFraudAlerts } from '../../data/operations'
import { mockUser } from '../../data/users'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ChartCard, MetricChart, AreaChart, BarChart, DoughnutChart } from '../../components/charts/ChartComponents'
import { EmptyState } from '../../components/ui/EmptyState'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'

const claimStatusConfig = {
  submitted: { label: 'Submitted', color: 'info' },
  'under-review': { label: 'Under Review', color: 'warning' },
  'ai-assessment': { label: 'AI Assessment', color: 'primary' },
  investigation: { label: 'Investigation', color: 'warning' },
  approved: { label: 'Approved', color: 'success' },
  rejected: { label: 'Rejected', color: 'danger' },
  'repair-settlement': { label: 'Repair/Settlement', color: 'primary' },
  closed: { label: 'Closed', color: 'neutral' },
}

export function EmployeeDashboard() {
  const [loading, setLoading] = useState(true)
  const [claims, setClaims] = useState([])
  const [policies, setPolicies] = useState([])
  const [fraudAlerts, setFraudAlerts] = useState([])
  const [recentActivity, setRecentActivity] = useState([])

  useEffect(() => {
    const timer = setTimeout(() => {
      setClaims(mockClaims)
      setPolicies(mockPolicies)
      setFraudAlerts(mockFraudAlerts)
      setRecentActivity([
        { id: 1, type: 'claim', title: 'New claim submitted', detail: 'CLM-2024-001234 by John Anderson', time: '15 min ago', icon: Briefcase, color: 'text-blue-600 bg-blue-50' },
        { id: 2, type: 'fraud', title: 'High fraud risk detected', detail: 'CLM-2024-001235 scored 87%', time: '1 hour ago', icon: AlertTriangle, color: 'text-red-600 bg-red-50' },
        { id: 3, type: 'policy', title: 'Policy renewed', detail: 'POL-2024-005679 renewed for John Anderson', time: '3 hours ago', icon: FileText, color: 'text-green-600 bg-green-50' },
        { id: 4, type: 'settlement', title: 'Settlement approved', detail: 'SET-2024-008901 approved for $8,000', time: '5 hours ago', icon: Gavel, color: 'text-purple-600 bg-purple-50' },
        { id: 5, type: 'claim', title: 'AI assessment complete', detail: 'CLM-2024-001230 ready for review', time: '6 hours ago', icon: Brain, color: 'text-indigo-600 bg-indigo-50' },
      ])
      setLoading(false)
    }, 600)
    return () => clearTimeout(timer)
  }, [])

  const activePolicies = policies.filter((p) => p.status === 'active')
  const activeClaims = claims.filter((c) => !['closed', 'rejected'].includes(c.status))
  const pendingClaims = claims.filter((c) => ['submitted', 'under-review', 'ai-assessment', 'investigation'].includes(c.status))
  const highRiskClaims = fraudAlerts.filter((f) => f.riskLevel === 'high')
  const totalClaimAmount = claims.reduce((sum, c) => sum + c.claimAmount, 0)
  const avgClaimCost = claims.length > 0 ? totalClaimAmount / claims.length : 0

  const claimsByStatus = claims.reduce((acc, claim) => {
    acc[claim.status] = (acc[claim.status] || 0) + 1
    return acc
  }, {})

  const claimStatusData = {
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
  }

  const fraudRiskData = {
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
  }

  const monthlyData = {
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
  }

  const recentClaims = [...claims].sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt)).slice(0, 5)

  const metricCards = [
    {
      title: 'Total Policies',
      value: policies.length,
      icon: FileText,
      iconColor: 'text-blue-600',
      bgColor: 'bg-blue-50',
      trend: '+12%',
      trendLabel: 'vs last month',
    },
    {
      title: 'Active Claims',
      value: activeClaims.length,
      icon: Briefcase,
      iconColor: 'text-purple-600',
      bgColor: 'bg-purple-50',
      trend: '+3',
      trendLabel: 'this week',
    },
    {
      title: 'Fraud Alerts',
      value: highRiskClaims.length,
      icon: AlertTriangle,
      iconColor: 'text-red-600',
      bgColor: 'bg-red-50',
      trend: '+2',
      trendLabel: 'high risk',
    },
    {
      title: 'Avg Claim Cost',
      value: formatCurrencyCompact(avgClaimCost),
      icon: DollarSign,
      iconColor: 'text-green-600',
      bgColor: 'bg-green-50',
      trend: '-5%',
      trendLabel: 'vs last quarter',
    },
  ]

  const quickActions = [
    { label: 'Review Claims', href: '/claims', icon: Briefcase, color: 'bg-blue-50 text-blue-600 hover:bg-blue-100' },
    { label: 'Fraud Investigation', href: '/fraud', icon: AlertTriangle, color: 'bg-red-50 text-red-600 hover:bg-red-100' },
    { label: 'AI Assessment', href: '/ai-assessment', icon: Brain, color: 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100' },
    { label: 'Analytics', href: '/analytics', icon: BarChart3, color: 'bg-green-50 text-green-600 hover:bg-green-100' },
  ]

  if (loading) {
    return (
      <div className="page animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card p-6">
              <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
              <div className="h-10 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Employee Dashboard</h1>
          <p className="page-subtitle">Insurance operations overview and key metrics</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="relative">
            <Bell className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs font-semibold rounded-full flex items-center justify-center">3</span>
          </Button>
          <Button variant="primary" size="sm">
            Export Report
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metricCards.map((metric) => (
          <Card key={metric.title} hover className="group">
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
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <ChartCard title="Claims Trend" subtitle="New vs resolved claims over 7 months">
          <AreaChart data={monthlyData} height={300} />
        </ChartCard>
        <div className="grid grid-cols-1 gap-6">
          <ChartCard title="Claim Status Distribution" subtitle="Current pipeline status">
            <DoughnutChart data={claimStatusData} height={250} />
          </ChartCard>
          <ChartCard title="Fraud Risk Distribution" subtitle="Risk levels across flagged claims">
            <DoughnutChart data={fraudRiskData} height={250} />
          </ChartCard>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
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
                    <TableRow key={claim.id} clickable onClick={() => window.location.href = `/claims/${claim.id}`}>
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
            </CardContent>
          </Card>
        </div>
        <div>
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
                          <p className="text-xs text-gray-500">Score: {alert.fraudRiskScore}% • {formatRelativeTime(alert.createdAt)}</p>
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

function formatCurrencyCompact(amount) {
  if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`
  if (amount >= 1000) return `$${(amount / 1000).toFixed(0)}K`
  return `$${amount.toFixed(0)}`
}

export default EmployeeDashboard