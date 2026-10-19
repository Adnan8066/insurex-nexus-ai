import { useState, useEffect, useCallback } from 'react'
import { BarChart3, Download, AlertCircle, RefreshCw } from 'lucide-react'
import { analyticsService } from '../../services'
import { Button } from '../../components/ui/Button'
import { ChartCard, BarChart, AreaChart, DoughnutChart, PieChart } from '../../components/charts/ChartComponents'
import { formatCurrency } from '../../utils/helpers'

const PENDING_STATUSES = ['submitted', 'under_review', 'ai_assessment', 'investigation']

const STATUS_LABELS = {
  submitted: 'Submitted',
  under_review: 'Under Review',
  ai_assessment: 'AI Assessment',
  investigation: 'Investigation',
  approved: 'Approved',
  repair_settlement: 'Repair Settlement',
  closed: 'Closed',
  rejected: 'Rejected',
}

export function AdminDashboard() {
  const [dateRange, setDateRange] = useState('quarter')
  const [summary, setSummary] = useState(null)
  const [fraudRisk, setFraudRisk] = useState(null)
  const [trend, setTrend] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryRes, fraudRes, trendRes] = await Promise.all([
        analyticsService.getDashboardSummary(dateRange),
        analyticsService.getFraudRiskDistribution(dateRange),
        analyticsService.getClaimsTrend(180),
      ])
      setSummary(summaryRes)
      setFraudRisk(fraudRes)
      setTrend(Array.isArray(trendRes) ? trendRes : [])
    } catch (err) {
      console.error('Failed to load analytics:', err)
      setError(err.message || 'Failed to load dashboard analytics.')
    } finally {
      setLoading(false)
    }
  }, [dateRange])

  useEffect(() => {
    loadData()
  }, [loadData])

  const claims = summary?.claims || {}
  const policies = summary?.policies || {}
  const fraud = summary?.fraud || {}
  const settlements = summary?.settlements || {}

  const byStatus = claims.by_status || {}
  const byIncidentType = claims.by_incident_type || {}
  const pendingClaims = PENDING_STATUSES.reduce((sum, s) => sum + (byStatus[s] || 0), 0)
  const totalClaims = claims.total || 0
  const totalLossCases = claims.total_loss_cases || 0
  const totalClaimAmount = Number(claims.total_amount) || 0
  const averageClaimCost = totalClaims > 0 ? Math.round(totalClaimAmount / totalClaims) : 0

  // 1. Claims over time (group daily trend by month)
  const monthly = {}
  trend.forEach((d) => {
    const month = (d.date || '').slice(0, 7)
    if (!month) return
    if (!monthly[month]) monthly[month] = { count: 0, amount: 0 }
    monthly[month].count += d.count || 0
    monthly[month].amount += Number(d.total_amount) || 0
  })
  const trendLabels = Object.keys(monthly).sort()
  const claimsOverTimeData = {
    labels: trendLabels,
    datasets: [
      {
        label: 'Claims Submitted',
        data: trendLabels.map((m) => monthly[m].count),
        borderColor: '#1e3a5f',
        backgroundColor: 'rgba(30, 58, 95, 0.12)',
        fill: true,
        tension: 0.35,
      },
      {
        label: 'Claim Amount (INR)',
        data: trendLabels.map((m) => Math.round(monthly[m].amount)),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.08)',
        fill: true,
        tension: 0.35,
      },
    ],
  }

  // 2. Fraud risk distribution
  const byLevel = fraudRisk?.by_level || {}
  const fraudDistributionData = {
    labels: ['Low Risk (<30%)', 'Moderate Risk (30-65%)', 'High Risk (>65%)'],
    datasets: [
      {
        data: [byLevel.low || 0, byLevel.medium || 0, byLevel.high || 0],
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
        borderWidth: 0,
      },
    ],
  }

  // 3. Claim status distribution
  const statusLabels = Object.keys(byStatus)
  const claimStatusDistributionData = {
    labels: statusLabels.map((s) => STATUS_LABELS[s] || s),
    datasets: [
      {
        label: 'Claim Count',
        data: statusLabels.map((s) => byStatus[s]),
        backgroundColor: '#1e3a5f',
        borderRadius: 4,
      },
    ],
  }

  // 4. Total-loss cases vs repairable
  const totalLossData = {
    labels: ['Repairable Claims', 'Total Loss Vehicles'],
    datasets: [
      {
        data: [Math.max(totalClaims - totalLossCases, 0), totalLossCases],
        backgroundColor: ['#10b981', '#ef4444'],
        borderWidth: 0,
      },
    ],
  }

  // 5. Claims by incident type
  const incidentLabels = Object.keys(byIncidentType)
  const incidentTypeData = {
    labels: incidentLabels.map((t) => (t || 'unknown').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())),
    datasets: [
      {
        label: 'Claim Count',
        data: incidentLabels.map((t) => byIncidentType[t]),
        backgroundColor: '#007bff',
        borderRadius: 4,
      },
    ],
  }

  const handleExport = () => {
    const rows = [
      ['Metric', 'Value'],
      ['Total Policies', policies.total || 0],
      ['Active Policies', policies.active || 0],
      ['Expiring Soon (30d)', policies.expiring_soon || 0],
      ['Total Claims', totalClaims],
      ['Pending Claims', pendingClaims],
      ['Total Loss Cases', totalLossCases],
      ['Total Claim Amount', totalClaimAmount],
      ['Average Claim Cost', averageClaimCost],
      ['Fraud Alerts', fraud.total_alerts || 0],
      ['High Risk Alerts', fraud.high_risk || 0],
      ['Settlements Total', settlements.total || 0],
      ['Settlements Pending Approval', settlements.pending_approval || 0],
      ['Settlements Pending Payment', settlements.pending_payment || 0],
      ['Settlements Total Paid', settlements.total_paid || 0],
    ]
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `executive-report-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              <BarChart3 className="w-3.5 h-3.5 text-primary" />
              Executive Business Intelligence
            </span>
          </div>
          <h1 className="page-title">Enterprise Analytics Dashboard</h1>
          <p className="page-subtitle">
            Comprehensive insurance portfolio performance, loss ratio analysis, and AI automation metrics
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="input-field py-2 text-sm font-semibold"
            aria-label="Reporting Interval"
          >
            <option value="week">Last 7 Days</option>
            <option value="month">Last 30 Days</option>
            <option value="quarter">Current Quarter</option>
            <option value="ytd">Year to Date</option>
            <option value="year">Last Year</option>
          </select>

          <Button variant="outline" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" />
            Export Executive Report
          </Button>
        </div>
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

      {loading && !summary && (
        <div className="p-8 text-center text-sm text-gray-400">Loading analytics...</div>
      )}

      {/* 7 KPI Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Total Policies</span>
          <p className="text-2xl font-black text-gray-900 mt-1">{policies.total || 0}</p>
          <span className="text-[11px] text-gray-500">In Portfolio</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Active Policies</span>
          <p className="text-2xl font-black text-blue-700 mt-1">{policies.active || 0}</p>
          <span className="text-[11px] text-gray-500">In Force</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Total Claims</span>
          <p className="text-2xl font-black text-gray-900 mt-1">{totalClaims}</p>
          <span className="text-[11px] text-blue-600 font-semibold">Intake All-Time</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Pending Claims</span>
          <p className="text-2xl font-black text-amber-600 mt-1">{pendingClaims}</p>
          <span className="text-[11px] text-amber-600">Action Needed</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Fraud Alerts</span>
          <p className="text-2xl font-black text-red-600 mt-1">{fraud.total_alerts || 0}</p>
          <span className="text-[11px] text-red-600">SIU Flagged</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Total Loss Cases</span>
          <p className="text-2xl font-black text-purple-700 mt-1">{totalLossCases}</p>
          <span className="text-[11px] text-gray-500">Salvage/Scrap</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm col-span-2 md:col-span-1">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Avg Claim Cost</span>
          <p className="text-2xl font-black text-emerald-700 mt-1">{formatCurrency(averageClaimCost)}</p>
          <span className="text-[11px] text-gray-500">Per Claim</span>
        </div>
      </div>

      {/* Row 1 Charts: Claims Over Time + Fraud Risk Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ChartCard
            title="1. Claims Over Time"
            subtitle="Monthly claim intake vs claim amount (6 Month Historical Trend)"
          >
            <AreaChart data={claimsOverTimeData} height={290} />
          </ChartCard>
        </div>

        <div>
          <ChartCard
            title="2. Fraud Risk Distribution"
            subtitle="Risk stratification across all evaluated claims"
          >
            <DoughnutChart data={fraudDistributionData} height={290} />
          </ChartCard>
        </div>
      </div>

      {/* Row 2 Charts: Claim Status Distribution + Total Loss */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ChartCard
            title="3. Claim Status Distribution"
            subtitle="Current claims inventory across lifecycle pipeline"
          >
            <BarChart data={claimStatusDistributionData} height={280} />
          </ChartCard>
        </div>

        <div>
          <ChartCard
            title="4. Total-Loss Cases vs Repairable"
            subtitle="Ratio of constructive total loss vs standard repairs"
          >
            <PieChart data={totalLossData} height={280} />
          </ChartCard>
        </div>
      </div>

      {/* Row 3 Chart: Claims by Incident Type */}
      <ChartCard
        title="5. Claims by Incident Type"
        subtitle="Distribution of filed claims by loss cause"
      >
        <BarChart data={incidentTypeData} height={260} />
      </ChartCard>
    </div>
  )
}

export default AdminDashboard
