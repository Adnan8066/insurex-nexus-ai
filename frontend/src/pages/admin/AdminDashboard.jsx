import { useState, useEffect, useCallback } from 'react'
import { Download, AlertCircle, RefreshCw } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { useLocation } from 'react-router-dom'
import { analyticsService, claimService } from '../../services'
import { Button } from '../../components/ui/Button'
import { ChartCard, ComboChart } from '../../components/charts/ChartComponents'
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

const CHART_HEIGHT = 280

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
  const [trend, setTrend] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [assignment, setAssignment] = useState(null)
  const [assignmentBusy, setAssignmentBusy] = useState(false)
  const isAdminDashboard = useLocation().pathname === '/dashboard'

  const granularity = TREND_GRANULARITY[dateRange] || 'day'

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryRes, trendRes] = await Promise.all([
        analyticsService.getDashboardSummary(dateRange),
        analyticsService.getClaimsTrendForTimeframe(dateRange, granularity),
      ])
      setSummary(summaryRes)
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

  const loadAssignments = useCallback(async () => {
    if (!isAdminDashboard) return
    try { setAssignment(await claimService.getAssignmentDashboard()) } catch (err) { console.error('Failed to load assignments:', err) }
  }, [isAdminDashboard])
  useEffect(() => { loadAssignments() }, [loadAssignments])

  const updateAutoAssignment = async (enabled) => {
    setAssignmentBusy(true)
    try { setAssignment(await claimService.updateAssignmentSettings({ enabled })) } catch (err) { console.error('Failed to update assignment settings:', err) }
    finally { setAssignmentBusy(false) }
  }
  const updatePpoPreference = async (prefer_qualified_ppo) => {
    setAssignmentBusy(true)
    try { setAssignment(await claimService.updateAssignmentSettings({ prefer_qualified_ppo })) } catch (err) { console.error('Failed to update PPO preference:', err) }
    finally { setAssignmentBusy(false) }
  }
  const retryAssignments = async () => {
    setAssignmentBusy(true)
    try { await claimService.retryPendingAssignments(); await loadAssignments() } catch (err) { console.error('Failed to retry assignments:', err) }
    finally { setAssignmentBusy(false) }
  }

  const claims = summary?.claims || {}
  const policies = summary?.policies || {}
  const fraud = summary?.fraud || {}
  const period = summary?.period
  const rangeLabel = DATE_RANGES.find((r) => r.value === dateRange)?.label || 'Selected period'
  const periodText = formatPeriod(period)

  const statusDistribution = claims.status_distribution || []
  const pendingClaims = statusDistribution
    .filter((s) => PENDING_STATUSES.includes(s.status))
    .reduce((sum, s) => sum + s.count, 0)
  const totalClaims = claims.total || 0
  const totalLossCases = claims.total_loss_cases || 0
  const totalClaimAmount = Number(claims.total_amount) || 0
  const averageClaimCost = totalClaims > 0 ? Math.round(totalClaimAmount / totalClaims) : 0

  // Claims over time: bars for intake (left axis), line for amount (right axis)
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

      {isAdminDashboard && assignment && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Automatic claim assignment</h2>
              <p className="text-sm text-gray-500">Current routing: expertise-aware workload balance. PPO is eligible only after a profile-v2 evaluation passes.</p>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                <input type="checkbox" checked={assignment.enabled} disabled={assignmentBusy} onChange={(e) => updateAutoAssignment(e.target.checked)} />
                Automatic assignment {assignment.enabled ? 'on' : 'off'}
              </label>
              <label className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                <input type="checkbox" checked={assignment.prefer_qualified_ppo} disabled={assignmentBusy} onChange={(e) => updatePpoPreference(e.target.checked)} />
                Use PPO after qualification
              </label>
              <Button variant="outline" size="sm" disabled={assignmentBusy || !assignment.pending_unassigned} onClick={retryAssignments}>Retry pending ({assignment.pending_unassigned})</Button>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Auto assigned" value={assignment.automatically_assigned} caption="Assignment history" valueClassName="text-blue-700" />
            <StatTile label="Pending unassigned" value={assignment.pending_unassigned} caption="Waiting for eligible expertise" valueClassName="text-amber-600" />
            <StatTile label="Failed attempts" value={assignment.failed_attempts} caption="Requires admin review" valueClassName="text-red-600" />
            <StatTile label="PPO qualification" value={assignment.ppo_qualified ? `Qualified · ${assignment.ppo_model_version}` : 'Not qualified'} caption="Production gate status" valueClassName={assignment.ppo_qualified ? 'text-emerald-700' : 'text-gray-600'} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <h3 className="mb-2 text-sm font-bold text-gray-700">Current employee workload</h3>
              <div className="space-y-2">{assignment.employees.length ? assignment.employees.map((employee) => <div key={employee.assigned_adjuster_id} className="flex justify-between rounded-lg bg-gray-50 px-3 py-2 text-sm"><span>{employee.assigned_adjuster__first_name} {employee.assigned_adjuster__last_name}</span><span className="font-semibold">{employee.workload} active · {employee.total_assignments} total</span></div>) : <p className="text-sm text-gray-500">No employee assignments yet.</p>}</div>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-bold text-gray-700">Recent assignment history</h3>
              <div className="space-y-2">{assignment.history.slice(0, 5).map((event) => <div key={event.id} className="rounded-lg bg-gray-50 px-3 py-2 text-sm"><div className="flex justify-between gap-2"><span className="font-semibold">{event.claim_number} · {event.event_type}</span><span className="text-gray-500">{event.strategy}</span></div><p className="text-gray-500">{event.employee_name || 'Unassigned'} · {event.reason}</p></div>)}</div>
            </div>
          </div>
        </section>
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

      <ChartCard
        title="Claims Over Time"
        subtitle={`${granularity === 'month' ? 'Monthly' : 'Daily'} claim intake vs claim amount · ${periodText}`}
      >
        {hasTrendData
          ? <ComboChart data={claimsOverTimeData} options={claimsOverTimeOptions} height={CHART_HEIGHT} />
          : <EmptyChart height={CHART_HEIGHT} message={noClaimsMessage} />}
      </ChartCard>
    </div>
  )
}

export default AdminDashboard
