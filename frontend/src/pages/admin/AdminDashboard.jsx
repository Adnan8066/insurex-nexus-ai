import { useState, useEffect, useCallback } from 'react'
import { Download, AlertCircle, RefreshCw } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { useLocation } from 'react-router-dom'
import { analyticsService } from '../../services'
import { Button } from '../../components/ui/Button'
import {
  ChartCard,
  BarChart,
  ComboChart,
  DoughnutChart,
  ChartLegend,
} from '../../components/charts/ChartComponents'
import { countAndPercentLabel } from '../../components/charts/chartUtils'
import { formatCurrency, formatCurrencyCompact } from '../../utils/helpers'
import { formatApiError } from '../../services/api'

const PENDING_STATUSES = ['submitted', 'under_review', 'ai_assessment', 'investigation']

const DATE_RANGES = [
  { value: 'week', label: 'Last 7 Days' },
  { value: 'month', label: 'Last 30 Days' },
  { value: 'quarter', label: 'Current Quarter' },
  { value: 'ytd', label: 'Year to Date' },
  { value: 'year', label: 'Last Year' },
]

// Short ranges are shown per day; longer ones per month.
const TREND_GRANULARITY = { week: 'day', month: 'day', quarter: 'month', ytd: 'month', year: 'month' }

const FRAUD_BAND_COLORS = { low: '#15803d', medium: '#d97706', high: '#dc2626' }
const TOTAL_LOSS_COLORS = { repairable: '#2563eb', totalLoss: '#dc2626' }

const CHART_HEIGHT = 280
const SIDE_CHART_HEIGHT = 180

function formatPeriod(period) {
  if (!period?.start) return 'All time'
  const start = parseISO(period.start)
  const end = parseISO(period.end)
  const sameYear = start.getFullYear() === end.getFullYear()
  return `${format(start, sameYear ? 'd MMM' : 'd MMM yyyy')} – ${format(end, 'd MMM yyyy')}`
}

function StatTile({ label, value, caption, valueClassName = 'text-gray-900', captionClassName = 'text-gray-500' }) {
  return (
    <div className="flex h-full min-w-0 flex-col rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <span className="text-[11px] font-bold uppercase leading-snug tracking-wider text-gray-500">{label}</span>
      <p className="mt-1 break-words text-2xl font-black leading-tight">
        <span className={valueClassName}>{value}</span>
      </p>
      <span className={`mt-auto pt-1 text-[11px] leading-snug ${captionClassName}`}>{caption}</span>
    </div>
  )
}

function EmptyChart({ height, message }) {
  return (
    <div className="flex items-center justify-center text-center text-sm text-gray-400" style={{ height }}>
      {message}
    </div>
  )
}

export function AdminDashboard() {
  // The admin's dashboard and the staff Analytics page share this component.
  const pageTitle = useLocation().pathname === '/analytics' ? 'Analytics' : 'Dashboard'
  const [dateRange, setDateRange] = useState('quarter')
  const [summary, setSummary] = useState(null)
  const [fraudRisk, setFraudRisk] = useState(null)
  const [trend, setTrend] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const granularity = TREND_GRANULARITY[dateRange] || 'day'

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryRes, fraudRes, trendRes] = await Promise.all([
        analyticsService.getDashboardSummary(dateRange),
        analyticsService.getFraudRiskDistribution(dateRange),
        analyticsService.getClaimsTrendForTimeframe(dateRange, granularity),
      ])
      setSummary(summaryRes)
      setFraudRisk(fraudRes)
      setTrend(Array.isArray(trendRes) ? trendRes : [])
    } catch (err) {
      console.error('Failed to load analytics:', err)
      setError(formatApiError(err, 'Failed to load dashboard analytics.'))
    } finally {
      setLoading(false)
    }
  }, [dateRange, granularity])

  useEffect(() => {
    loadData()
  }, [loadData])

  const claims = summary?.claims || {}
  const policies = summary?.policies || {}
  const fraud = summary?.fraud || {}
  const period = summary?.period
  const rangeLabel = DATE_RANGES.find((r) => r.value === dateRange)?.label || 'Selected period'
  const periodText = formatPeriod(period)

  const statusDistribution = claims.status_distribution || []
  const byIncidentType = claims.by_incident_type || {}
  const pendingClaims = statusDistribution
    .filter((s) => PENDING_STATUSES.includes(s.status))
    .reduce((sum, s) => sum + s.count, 0)
  const totalClaims = claims.total || 0
  const totalLossCases = claims.total_loss_cases || 0
  const repairableCases = claims.repairable_cases ?? Math.max(totalClaims - totalLossCases, 0)
  const totalClaimAmount = Number(claims.total_amount) || 0
  const averageClaimCost = totalClaims > 0 ? Math.round(totalClaimAmount / totalClaims) : 0

  // 1. Claims over time: bars for intake (left axis), line for amount (right axis)
  const trendLabels = trend.map((d) => format(parseISO(String(d.date)), granularity === 'month' ? 'MMM yyyy' : 'd MMM'))
  const hasTrendData = trend.some((d) => d.count > 0)
  const claimsOverTimeData = {
    labels: trendLabels,
    datasets: [
      {
        type: 'bar',
        label: 'Claims Submitted',
        data: trend.map((d) => d.count),
        backgroundColor: '#1e3a5f',
        borderRadius: 4,
        maxBarThickness: 36,
        yAxisID: 'y',
        order: 2,
      },
      {
        type: 'line',
        label: 'Claim Amount (INR)',
        data: trend.map((d) => Math.round(Number(d.total_amount) || 0)),
        borderColor: '#10b981',
        backgroundColor: '#10b981',
        pointRadius: 3,
        pointHoverRadius: 6,
        tension: 0.3,
        yAxisID: 'y1',
        order: 1,
      },
    ],
  }
  const claimsOverTimeOptions = {
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'Claims', color: '#64748b' }, ticks: { precision: 0, color: '#94a3b8' }, grid: { color: '#e2e8f0' } },
      y1: {
        beginAtZero: true,
        position: 'right',
        grid: { drawOnChartArea: false },
        title: { display: true, text: 'Amount (INR)', color: '#64748b' },
        ticks: { color: '#94a3b8', callback: (value) => formatCurrencyCompact(value) },
      },
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) => ctx.dataset.yAxisID === 'y1'
            ? `${ctx.dataset.label}: ${formatCurrency(ctx.raw)}`
            : `${ctx.dataset.label}: ${ctx.raw}`,
        },
      },
    },
  }

  // 2. Fraud risk distribution (horizontal bars so small bands stay readable)
  const fraudBands = fraudRisk?.bands || []
  const fraudScoredTotal = fraudBands.reduce((sum, b) => sum + b.count, 0)
  const fraudDistributionData = {
    labels: fraudBands.map((b) => b.label),
    datasets: [
      {
        label: 'Claims',
        data: fraudBands.map((b) => b.count),
        backgroundColor: fraudBands.map((b) => FRAUD_BAND_COLORS[b.level]),
        borderRadius: 4,
        maxBarThickness: 28,
      },
    ],
  }
  const fraudDistributionOptions = {
    indexAxis: 'y',
    scales: {
      x: { beginAtZero: true, ticks: { precision: 0, color: '#94a3b8' }, grid: { color: '#e2e8f0' } },
      y: { grid: { display: false }, ticks: { display: false } },
    },
    plugins: { tooltip: { callbacks: { label: countAndPercentLabel } } },
  }

  // 3. Claim status distribution: actual counts for every lifecycle status
  const claimStatusDistributionData = {
    labels: statusDistribution.map((s) => s.label),
    datasets: [
      {
        label: 'Claims',
        data: statusDistribution.map((s) => s.count),
        backgroundColor: '#1e3a5f',
        borderRadius: 4,
        maxBarThickness: 48,
      },
    ],
  }
  const countTooltipOptions = { plugins: { tooltip: { callbacks: { label: countAndPercentLabel } } } }

  // 4. Total-loss cases vs repairable
  const totalLossData = {
    labels: ['Repairable', 'Total Loss'],
    datasets: [
      {
        data: [repairableCases, totalLossCases],
        backgroundColor: [TOTAL_LOSS_COLORS.repairable, TOTAL_LOSS_COLORS.totalLoss],
        borderWidth: 0,
      },
    ],
  }
  const totalLossOptions = {
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: countAndPercentLabel } } },
  }

  // 5. Claims by incident type
  const incidentLabels = Object.keys(byIncidentType)
  const incidentTypeData = {
    labels: incidentLabels.map((t) => (t || 'unknown').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())),
    datasets: [
      {
        label: 'Claims',
        data: incidentLabels.map((t) => byIncidentType[t]),
        backgroundColor: '#007bff',
        borderRadius: 4,
        maxBarThickness: 48,
      },
    ],
  }

  const noClaimsMessage = `No claims submitted in this period (${periodText}).`

  const handleExport = () => {
    const rows = [
      ['Metric', 'Value'],
      ['Period', `${rangeLabel} (${periodText})`],
      ['New Policies', policies.total || 0],
      ['Active Policies', policies.active || 0],
      ['Expiring Soon (30d)', policies.expiring_soon || 0],
      ['Total Claims', totalClaims],
      ['Pending Claims', pendingClaims],
      ['Total Loss Cases', totalLossCases],
      ['Total Claim Amount', totalClaimAmount],
      ['Average Claim Cost', averageClaimCost],
      ['High Fraud Risk Claims', fraud.high_risk_claims || 0],
      ['High Fraud Risk Rate (%)', fraud.flag_rate || 0],
      ['SIU Referrals', fraud.siu_referrals || 0],
    ]
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `executive-report-${dateRange}-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="min-w-0">
          <h1 className="page-title">{pageTitle}</h1>
          <p className="page-subtitle">
            Showing <span className="font-semibold text-gray-700">{rangeLabel}</span> · {periodText}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="input-field py-2 text-sm font-semibold"
            aria-label="Reporting Interval"
          >
            {DATE_RANGES.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>

          <Button variant="outline" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" />
            Export Report
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

      {/* KPI tiles: labels wrap instead of truncating */}
      <div className={`grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3 transition-opacity ${loading && summary ? 'opacity-60' : ''}`}>
        <StatTile label="New Policies" value={policies.total || 0} caption={`Started · ${rangeLabel}`} />
        <StatTile label="Active Policies" value={policies.active || 0} caption="In force during period" valueClassName="text-blue-700" />
        <StatTile label="Total Claims" value={totalClaims} caption={`Submitted · ${rangeLabel}`} captionClassName="text-blue-600 font-semibold" />
        <StatTile label="Pending Claims" value={pendingClaims} caption="Awaiting decision" valueClassName="text-amber-600" captionClassName="text-amber-600" />
        <StatTile
          label="High Fraud Risk"
          value={fraud.high_risk_claims || 0}
          caption={`${fraud.flag_rate || 0}% of claims · ${fraud.siu_referrals || 0} SIU referral${fraud.siu_referrals === 1 ? '' : 's'}`}
          valueClassName="text-red-600"
          captionClassName="text-red-600"
        />
        <StatTile
          label="Total Loss Cases"
          value={totalLossCases}
          caption={`≥${claims.total_loss_threshold ?? 50}% total-loss probability`}
          valueClassName="text-purple-700"
        />
        <StatTile label="Avg Claim Cost" value={formatCurrency(averageClaimCost)} caption={`Per claim · ${rangeLabel}`} valueClassName="text-emerald-700" />
      </div>

      {/* Row 1: Claims Over Time + Fraud Risk Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="min-w-0 lg:col-span-2">
          <ChartCard
            title="1. Claims Over Time"
            subtitle={`${granularity === 'month' ? 'Monthly' : 'Daily'} claim intake vs claim amount · ${periodText}`}
          >
            {hasTrendData
              ? <ComboChart data={claimsOverTimeData} options={claimsOverTimeOptions} height={CHART_HEIGHT} />
              : <EmptyChart height={CHART_HEIGHT} message={noClaimsMessage} />}
          </ChartCard>
        </div>

        <div className="min-w-0">
          <ChartCard
            title="2. Fraud Risk Distribution"
            subtitle={`Claims by fraud score band · ${fraudScoredTotal} claim${fraudScoredTotal === 1 ? '' : 's'}`}
          >
            {fraudScoredTotal > 0 ? (
              <>
                <BarChart data={fraudDistributionData} options={fraudDistributionOptions} height={SIDE_CHART_HEIGHT - 40} />
                <ChartLegend items={fraudBands.map((b) => ({ label: b.label, value: b.count, color: FRAUD_BAND_COLORS[b.level] }))} />
              </>
            ) : (
              <EmptyChart height={CHART_HEIGHT} message={noClaimsMessage} />
            )}
          </ChartCard>
        </div>
      </div>

      {/* Row 2: Claim Status Distribution + Total Loss */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="min-w-0 lg:col-span-2">
          <ChartCard
            title="3. Claim Status Distribution"
            subtitle={`Number of claims at each lifecycle stage · ${periodText}`}
          >
            {totalClaims > 0
              ? <BarChart data={claimStatusDistributionData} options={countTooltipOptions} height={CHART_HEIGHT} />
              : <EmptyChart height={CHART_HEIGHT} message={noClaimsMessage} />}
          </ChartCard>
        </div>

        <div className="min-w-0">
          <ChartCard
            title="4. Total-Loss Cases vs Repairable"
            subtitle={`Total loss = ≥${claims.total_loss_threshold ?? 50}% total-loss probability`}
          >
            {totalClaims > 0 ? (
              <>
                <DoughnutChart data={totalLossData} options={totalLossOptions} height={SIDE_CHART_HEIGHT} />
                <ChartLegend
                  items={[
                    { label: 'Repairable', value: repairableCases, color: TOTAL_LOSS_COLORS.repairable },
                    { label: 'Total Loss', value: totalLossCases, color: TOTAL_LOSS_COLORS.totalLoss },
                  ]}
                />
              </>
            ) : (
              <EmptyChart height={CHART_HEIGHT} message={noClaimsMessage} />
            )}
          </ChartCard>
        </div>
      </div>

      {/* Row 3: Claims by Incident Type */}
      <ChartCard
        title="5. Claims by Incident Type"
        subtitle={`Distribution of filed claims by loss cause · ${periodText}`}
      >
        {incidentLabels.length > 0
          ? <BarChart data={incidentTypeData} options={countTooltipOptions} height={260} />
          : <EmptyChart height={260} message={noClaimsMessage} />}
      </ChartCard>
    </div>
  )
}

export default AdminDashboard
