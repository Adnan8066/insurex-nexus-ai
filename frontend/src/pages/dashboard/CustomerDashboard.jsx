import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  FileText,
  Briefcase,
  Clock,
  CheckCircle,
  Headphones,
  ArrowRight,
  RefreshCw,
  Download,
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
import { EmptyState } from '../../components/ui/EmptyState'

import ErrorBoundary, {
  DataTableErrorFallback,
} from '../../components/ui/ErrorBoundary'

import { DashboardSkeleton } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/toastHooks'
import { PENDING_CLAIM_STATUSES, POLICY_TYPES, labelFor } from '../../constants/domain'

// Customers see internal review stages as "Under review".
const CUSTOMER_STATUS = { ai_assessment: 'under_review', investigation: 'under_review' }

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
    status: CUSTOMER_STATUS[c.status] || c.status,
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
      toast.error('We could not load your dashboard.', {
        persistent: true,
        action: { label: 'Retry', onClick: () => fetchData() },
      })
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const activePolicies = policies.filter((p) => p.status === 'active')
  const pendingClaims = claims.filter((c) => PENDING_CLAIM_STATUSES.includes(c.status))
  const approvedClaims = claims.filter((c) => ['approved', 'repair_settlement'].includes(c.status))
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
      toast.success('Your summary PDF has been downloaded.')
    } catch {
      toast.error('We could not create the PDF. Please try again.')
    }
  }

  const metricCards = [
    { title: 'Active policies', value: activePolicies.length, icon: FileText, iconColor: 'text-blue-600', bgColor: 'bg-blue-50', link: '/policies', hint: 'View your cover' },
    { title: 'Being reviewed', value: pendingClaims.length, icon: Clock, iconColor: 'text-amber-600', bgColor: 'bg-amber-50', link: '/claims?status=pending', hint: 'Claims waiting for a decision' },
    { title: 'Approved', value: approvedClaims.length, icon: CheckCircle, iconColor: 'text-green-600', bgColor: 'bg-green-50', link: '/claims?status=approved', hint: 'Approved or being paid' },
    { title: 'All claims', value: claims.length, icon: Briefcase, iconColor: 'text-purple-600', bgColor: 'bg-purple-50', link: '/claims', hint: 'Your full claim history' },
  ]

  if (loading) {
    return <DashboardSkeleton />
  }

  return (
    <div className="page space-y-6">
      {connectionError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">
          <WifiOff className="w-4 h-4 shrink-0" />
          <span>We couldn&apos;t reach our servers, so this information may be out of date.</span>
          <Button variant="ghost" size="sm" className="ml-auto" onClick={() => fetchData()}>Try again</Button>
        </div>
      )}

      {/* Main actions first: filing a claim is the most common task. */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Need to make a claim?</h2>
          <p className="text-sm text-slate-500">It takes about 5 minutes. You can add photos now or later.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button asChild variant="primary">
            <Link to="/claims/new"><FilePlus2 className="mr-2 h-4 w-4" />File a claim</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to="/support"><Headphones className="mr-2 h-4 w-4" />Get help</Link>
          </Button>
          <Button variant="ghost" size="sm" className="whitespace-nowrap" onClick={handleExport} disabled={refreshing} title="Download a PDF summary of your policies and claims">
            <Download className="mr-2 h-4 w-4" />
            Download summary
          </Button>
          <Button variant="ghost" size="sm" onClick={() => fetchData()} loading={refreshing} aria-label="Refresh" title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {metricCards.map((metric) => (
          <Link key={metric.title} to={metric.link} className="card group p-4 transition-shadow hover:shadow-lg sm:p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-500">{metric.title}</p>
                <p className="mt-1 text-3xl font-bold text-gray-900">{metric.value}</p>
              </div>
              <div className={clsx('hidden h-11 w-11 shrink-0 items-center justify-center rounded-xl sm:flex', metric.bgColor, metric.iconColor)}>
                <metric.icon className="h-5 w-5" aria-hidden="true" />
              </div>
            </div>
            <p className="mt-2 flex items-center text-xs text-gray-500 group-hover:text-primary">
              {metric.hint}
              <ArrowRight className="ml-1 h-3.5 w-3.5" aria-hidden="true" />
            </p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <DataTableErrorFallback title="Your claims" resetError={resetError} retryCount={retryCount} />
          )}>
            <Card>
              <CardHeader
                title="Your recent claims"
                subtitle="Select a claim to see its progress"
                action={claims.length > 0 && (
                  <Button variant="ghost" size="sm" asChild>
                    <Link to="/claims">View all <ArrowRight className="w-4 h-4 ml-1" /></Link>
                  </Button>
                )}
              />
              <CardContent className="p-0">
                {recentClaims.length > 0 ? (
                  <ul className="divide-y divide-gray-200">
                    {recentClaims.map((claim) => (
                      <li key={claim.id}>
                        <Link to={`/claims/${claim.id}/tracking`} className="block p-4 transition-colors hover:bg-gray-50">
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-semibold text-gray-900">{claim.claimNumber}</span>
                                <StatusBadge status={claim.status} />
                              </div>
                              <p className="mt-1 truncate text-sm text-gray-600">
                                {(claim.incidentType || 'Incident').replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())}
                                {claim.vehicle ? ` · ${claim.vehicle.make} ${claim.vehicle.model}` : ''}
                                {' · '}{formatDate(claim.incidentDate)}
                              </p>
                              <p className="mt-1 text-xs font-medium text-primary">Track progress →</p>
                            </div>
                            <div className="shrink-0 text-right">
                              <p className="font-semibold text-gray-900">{formatCurrency(claim.claimAmount)}</p>
                              <p className="text-xs text-gray-500">{formatRelativeTime(claim.submittedAt)}</p>
                            </div>
                          </div>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState
                    icon={<FilePlus2 className="w-12 h-12" />}
                    title="No claims yet"
                    description="When you file a claim, you can follow every step of it here."
                    action={<Button asChild variant="primary"><Link to="/claims/new">File a claim</Link></Button>}
                  />
                )}
              </CardContent>
            </Card>
          </ErrorBoundary>
        </div>
        <div>
          <ErrorBoundary fallback={({ resetError, retryCount }) => (
            <DataTableErrorFallback title="Your policies" resetError={resetError} retryCount={retryCount} />
          )}>
            <Card>
              <CardHeader
                title="Your cover"
                subtitle="Active policies"
                action={policies.length > 0 && (
                  <Button variant="ghost" size="sm" asChild>
                    <Link to="/policies">View all</Link>
                  </Button>
                )}
              />
              <CardContent className="p-0">
                {activePolicies.length > 0 ? (
                  <ul className="divide-y divide-gray-200">
                    {activePolicies.map((policy) => (
                      <li key={policy.id}>
                        <Link to={`/policies/${policy.id}`} className="block p-4 transition-colors hover:bg-gray-50">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{labelFor(POLICY_TYPES, policy.type)}</span>
                            <StatusBadge status={policy.status} />
                          </div>
                          <p className="mt-1 truncate text-sm text-gray-500">
                            {policy.vehicle ? `${policy.vehicle.make} ${policy.vehicle.model} (${policy.vehicle.year})` : (policy.property?.address || policy.policyNumber)}
                          </p>
                          <p className="text-sm text-gray-500">Renews or ends {formatDate(policy.endDate)}</p>
                          <p className="mt-1 text-xs text-gray-500">{formatCurrency(policy.premium)} a year · Deductible {formatCurrency(policy.deductible)}</p>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState
                    icon={<FileText className="w-12 h-12" />}
                    title="No active policies"
                    description="You need an active policy to file a claim. Contact us to set one up."
                    action={<Button asChild variant="secondary"><Link to="/support">Contact us</Link></Button>}
                  />
                )}
              </CardContent>
            </Card>
          </ErrorBoundary>
        </div>
      </div>
    </div>
  )
}

export default CustomerDashboard
