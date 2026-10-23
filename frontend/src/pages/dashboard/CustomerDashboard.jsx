import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
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
  WifiOff,
  FilePlus2,
  Car,
} from 'lucide-react'
import { clsx } from 'clsx'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'
import { policyService, claimService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'

import ErrorBoundary, {
  DataTableErrorFallback,
} from '../../components/ui/ErrorBoundary'

import { DashboardSkeleton } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/toastHooks'

const createPdfBlob = (reportLines) => {
  const pages = [[]]
  let y = 750
  reportLines.forEach(({ text, style = 'body' }) => {
    const normalized = String(text ?? '—')
      .replace(/₹/g, 'INR ')
      .normalize('NFKD')
      .replace(/[^\x20-\x7E]/g, '')
    const maxLength = style === 'title' ? 58 : 92
    const words = normalized.split(/\s+/)
    const wrapped = []
    let line = ''
    words.forEach((word) => {
      if (line && `${line} ${word}`.length > maxLength) {
        wrapped.push(line)
        line = word
      } else {
        line = line ? `${line} ${word}` : word
      }
    })
    if (line) wrapped.push(line)

    wrapped.forEach((wrappedLine) => {
      if (y < 48) {
        pages.push([])
        y = 750
      }
      pages[pages.length - 1].push({ text: wrappedLine, style, y })
      y -= style === 'title' ? 30 : style === 'section' ? 23 : 17
    })
    if (style === 'section') y -= 4
  })

  const escapePdfText = (text) => text.replace(/([\\()])/g, '\\$1')
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${pages.map((_, index) => `${5 + index * 2} 0 R`).join(' ')}] /Count ${pages.length} >>`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
  ]

  pages.forEach((page, index) => {
    const pageObjectId = 5 + index * 2
    const contentObjectId = pageObjectId + 1
    const commands = page.map(({ text, style, y: lineY }) => {
      const bold = style === 'title' || style === 'section'
      const font = bold ? 'F2' : 'F1'
      const size = style === 'title' ? 18 : style === 'section' ? 13 : 10
      return `BT /${font} ${size} Tf 50 ${lineY} Td (${escapePdfText(text)}) Tj ET`
    }).join('\n')
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${contentObjectId} 0 R >>`)
    objects.push(`<< /Length ${commands.length} >>\nstream\n${commands}\nendstream`)
  })

  let pdf = '%PDF-1.4\n'
  const offsets = [0]
  objects.forEach((object, index) => {
    offsets.push(pdf.length)
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`
  })
  const xrefOffset = pdf.length
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  offsets.slice(1).forEach((offset) => { pdf += `${String(offset).padStart(10, '0')} 00000 n \n` })
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`
  return new Blob([pdf], { type: 'application/pdf' })
}

export function CustomerDashboard() {
  const { user } = useAuth()
  const toast = useToast()

  const [loading, setLoading] = useState(true)
  const [policies, setPolicies] = useState([])
  const [claims, setClaims] = useState([])
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
    status: c.status === 'ai_assessment' ? 'under_review' : c.status,
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

  const activePolicies = policies.filter((p) => p.status === 'active')
  const pendingClaims = claims.filter((c) => ['submitted', 'under_review', 'ai_assessment', 'investigation'].includes(c.status))
  const approvedClaims = claims.filter((c) => c.status === 'approved')
  const recentClaims = [...claims].sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt)).slice(0, 5)

  const handleExport = () => {
    try {
      const customerName = user?.name || user?.first_name || user?.email || 'Customer'
      const reportLines = [
        { text: 'InsureX Customer Report', style: 'title' },
        { text: `Customer: ${customerName}` },
        { text: `Generated: ${new Date().toLocaleString()}` },
        { text: 'Account Summary', style: 'section' },
        { text: `Active policies: ${activePolicies.length}    Total claims: ${claims.length}    Being reviewed: ${pendingClaims.length}    Approved: ${approvedClaims.length}` },
        { text: 'Policies', style: 'section' },
        ...(policies.length ? policies.flatMap((policy) => [
          { text: `${policy.policyNumber || 'Policy'} — ${policy.type || 'Insurance policy'}`, style: 'body' },
          { text: `Status: ${policy.status || 'Unknown'} | Coverage: ${formatDate(policy.startDate)} to ${formatDate(policy.endDate)} | Premium: ${formatCurrency(policy.premium)} | Deductible: ${formatCurrency(policy.deductible)}` },
        ]) : [{ text: 'No policies found.' }]),
        { text: 'Claims', style: 'section' },
        ...(claims.length ? claims.flatMap((claim) => [
          { text: `${claim.claimNumber || 'Claim'} — ${claim.status || 'Unknown status'}`, style: 'body' },
          { text: `Policy: ${claim.policyNumber || '—'} | Incident: ${(claim.incidentType || '—').replace(/_/g, ' ')} | Date: ${formatDate(claim.incidentDate)} | Amount: ${formatCurrency(claim.claimAmount)}` },
        ]) : [{ text: 'No claims found.' }]),
      ]
      const blob = createPdfBlob(reportLines)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `customer-report-${new Date().toISOString().split('T')[0]}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      toast.showSuccess('PDF report downloaded successfully')
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
    { label: 'View Payments', href: '/settlements', icon: DollarSign, color: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100', description: 'Review your claim payment and settlement records' },
    { label: 'Get Support', href: '/support', icon: Headphones, color: 'bg-violet-50 text-violet-700 hover:bg-violet-100', description: 'Email or call our support team' },
  ]

  const firstName = user?.first_name || user?.firstName || user?.name?.trim().split(/\s+/)[0] || user?.get_full_name?.call(user)?.trim().split(/\s+/)[0] || user?.email?.split('@')[0] || 'there'

  if (loading) {
    return <DashboardSkeleton />
  }

  return (
    <div className="page">
      <div className="page-header flex-col items-stretch">
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
        <nav className="mx-auto grid w-full grid-cols-1 gap-3 sm:w-auto sm:grid-cols-3" aria-label="Your insurance">
          {[
            { label: 'Policies', description: 'View your coverage and policy details.', href: '/policies', icon: FileText, visual: 'from-blue-700 via-blue-500 to-cyan-400' },
            { label: 'Claims', description: 'Follow your claims and see the latest updates.', href: '/claims', icon: Briefcase, visual: 'from-violet-700 via-violet-500 to-fuchsia-400' },
            { label: 'Vehicles', description: 'View the vehicles protected by your policies.', href: '/vehicles', icon: Car, visual: 'from-emerald-700 via-emerald-500 to-teal-300' },
          ].map((item) => (
            <Link key={item.label} to={item.href} className="card group w-full overflow-hidden transition hover:-translate-y-1 hover:shadow-lg sm:w-[172px]">
              <span className={clsx('relative flex h-20 items-center justify-center overflow-hidden bg-gradient-to-br', item.visual)}>
                <span className="absolute -right-3 -top-8 h-24 w-24 rounded-full border border-white/20" aria-hidden="true" />
                <span className="absolute -bottom-12 -left-5 h-24 w-24 rounded-full border border-white/20" aria-hidden="true" />
                <span className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-white/20 text-white shadow-lg backdrop-blur-sm">
                  <item.icon className="h-6 w-6" aria-hidden="true" />
                </span>
              </span>
              <span className="block p-3">
                <span className="block font-semibold text-gray-900 group-hover:text-blue-700">{item.label}</span>
                <span className="mt-1 block min-h-9 text-xs leading-4 text-gray-500">{item.description}</span>
                <span className="mt-2 block text-xs font-semibold text-blue-700">Explore <ArrowRight className="ml-1 inline h-3.5 w-3.5 transition-transform group-hover:translate-x-1" aria-hidden="true" /></span>
              </span>
            </Link>
          ))}
        </nav>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm mb-6">
        <p className="text-sm text-slate-500">Your coverage and claims, at a glance</p>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ghost" size="sm" className="relative" onClick={() => fetchData()} loading={refreshing} aria-label="Refresh dashboard" title="Refresh dashboard">
            <RefreshCw className="w-4 h-4" />
          </Button>

          <Button variant="primary" size="sm" onClick={handleExport} loading={refreshing}>
            <Download className="w-4 h-4 mr-2" />
            Export PDF
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
        <Card className="mb-8">
          <CardHeader
            title="Your claims at a glance"
            subtitle="A simple summary of where things stand"
            action={(
              <Button variant="ghost" size="sm" asChild>
                <Link to="/claims">Track your claims <ArrowRight className="ml-1 h-4 w-4" /></Link>
              </Button>
            )}
          />
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-xl bg-amber-50 p-4">
                <p className="text-sm font-medium text-amber-800">Being reviewed</p>
                <p className="mt-1 text-2xl font-semibold text-amber-950 dark:text-slate-100">{pendingClaims.length}</p>
                <p className="mt-1 text-sm text-amber-800">We&apos;ll share updates as soon as they&apos;re available.</p>
              </div>
              <div className="rounded-xl bg-emerald-50 p-4">
                <p className="text-sm font-medium text-emerald-800">Approved</p>
                <p className="mt-1 text-2xl font-semibold text-emerald-950 dark:text-slate-100">{approvedClaims.length}</p>
                <p className="mt-1 text-sm text-emerald-800">See your claim details for the next steps.</p>
              </div>
              <div className="rounded-xl bg-blue-50 p-4">
                <p className="text-sm font-medium text-blue-800">Total claims</p>
                <p className="mt-1 text-2xl font-semibold text-blue-950 dark:text-slate-100">{claims.length}</p>
                <p className="mt-1 text-sm text-blue-800">Your latest updates are listed below.</p>
              </div>
            </div>
          </CardContent>
        </Card>
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
