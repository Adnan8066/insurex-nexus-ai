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
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { mockPolicies, mockPolicyStats } from '../../data/policies'
import { mockClaims, mockClaimStats } from '../../data/claims'
import { mockVehicles } from '../../data/vehicles'
import { mockUser } from '../../data/users'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ChartCard, MetricChart, AreaChart, DoughnutChart } from '../../components/charts/ChartComponents'
import { EmptyState } from '../../components/ui/EmptyState'
import { LoadingSpinner } from '../../components/ui/LoadingSpinner'

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

export function CustomerDashboard() {
  const [loading, setLoading] = useState(true)
  const [policies, setPolicies] = useState([])
  const [claims, setClaims] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [notifications, setNotifications] = useState([])

  useEffect(() => {
    const timer = setTimeout(() => {
      setPolicies(mockPolicies)
      setClaims(mockClaims)
      setVehicles(mockVehicles)
      setNotifications([
        { id: 1, title: 'Claim Update', message: 'Your claim #CLM-2024-001234 is now under review', time: '2 hours ago', read: false, type: 'claim' },
        { id: 2, title: 'Payment Processed', message: 'Settlement payment for #SET-2023-008231 has been completed', time: '1 day ago', read: false, type: 'payment' },
        { id: 3, title: 'Policy Renewal', message: 'Your auto policy #POL-2024-005678 renews in 30 days', time: '3 days ago', read: true, type: 'policy' },
        { id: 4, title: 'Document Required', message: 'Additional documentation needed for claim #CLM-2024-001230', time: '5 days ago', read: true, type: 'document' },
      ])
      setLoading(false)
    }, 800)
    return () => clearTimeout(timer)
  }, [])

  const activePolicies = policies.filter((p) => p.status === 'active')
  const activeClaims = claims.filter((c) => !['closed', 'rejected'].includes(c.status))
  const pendingClaims = claims.filter((c) => ['submitted', 'under-review', 'ai-assessment', 'investigation'].includes(c.status))
  const approvedClaims = claims.filter((c) => c.status === 'approved')
  const recentClaims = [...claims].sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt)).slice(0, 5)

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
          '#3b82f6', // info
          '#f59e0b', // warning
          '#1e3a5f', // primary
          '#f59e0b', // warning
          '#10b981', // success
          '#ef4444', // danger
          '#1e3a5f', // primary
          '#94a3b8', // neutral
        ],
        borderWidth: 0,
      },
    ],
  }

  const monthlyClaimsData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Claims Submitted',
        data: [2, 1, 3, 0, 2, 1],
        borderColor: '#1e3a5f',
        backgroundColor: 'rgba(30, 58, 95, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
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
    { label: 'File New Claim', href: '/claims/new', icon: AlertTriangle, color: 'bg-red-50 text-red-600 hover:bg-red-100' },
    { label: 'View Policies', href: '/policies', icon: FileText, color: 'bg-blue-50 text-blue-600 hover:bg-blue-100' },
    { label: 'Manage Vehicles', href: '/vehicles', icon: Car, color: 'bg-green-50 text-green-600 hover:bg-green-100' },
    { label: 'Make Payment', href: '/settlements', icon: DollarSign, color: 'bg-purple-50 text-purple-600 hover:bg-purple-100' },
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="card lg:col-span-2 p-6 h-96"><div className="h-full bg-gray-100 rounded"></div></div>
          <div className="card p-6 h-96"><div className="h-full bg-gray-100 rounded"></div></div>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Welcome back, {mockUser.name.split(' ')[0]}! Here's an overview of your insurance portfolio.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="relative">
            <Bell className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs font-semibold rounded-full flex items-center justify-center">3</span>
          </Button>
          <Button variant="primary" size="sm" asChild>
            <Link to="/claims/new">
              <AlertTriangle className="w-4 h-4 mr-2" />
              File Claim
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metricCards.map((metric) => (
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
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <ChartCard title="Claims Overview" subtitle="Monthly claims submitted over the past 6 months">
            <AreaChart data={monthlyClaimsData} height={300} />
          </ChartCard>
        </div>
        <div>
          <ChartCard title="Claim Status Distribution" subtitle="Current status of all your claims">
            <DoughnutChart data={claimStatusData} height={300} />
          </ChartCard>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
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
                          <p className="text-sm text-gray-600 mt-1 truncate">{claim.incidentType} • {claim.vehicle.make} {claim.vehicle.model}</p>
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
        </div>
        <div>
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