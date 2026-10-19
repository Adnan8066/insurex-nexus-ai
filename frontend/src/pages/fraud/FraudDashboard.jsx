import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  Shield,
  Search,
  UserCheck,
  CheckCircle2,
  Clock,
  Eye,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  Send,
  XCircle,
} from 'lucide-react'
import { clsx } from 'clsx'
import { investigationService } from '../../services'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import { Modal } from '../../components/ui/Modal'
import { formatDate, formatRelativeTime } from '../../utils/helpers'

const STATUS_LABELS = {
  new: 'New',
  investigation: 'Under Investigation',
  reviewed: 'Reviewed',
  dismissed: 'Dismissed',
  escalated: 'Escalated',
}

const normalizeRiskFactor = (rf) => {
  if (typeof rf === 'string') return { label: rf, severity: null, description: '' }
  if (rf && typeof rf === 'object') {
    return {
      label: rf.factor || rf.name || rf.title || 'Risk factor',
      severity: rf.severity || null,
      description: rf.description || '',
    }
  }
  return { label: String(rf), severity: null, description: '' }
}

export function FraudDashboard() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [actionNotes, setActionNotes] = useState('')
  const [processingAction, setProcessingAction] = useState(false)
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const loadAlerts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await investigationService.getFraudAlerts()
      setAlerts(Array.isArray(data) ? data : data.results || [])
    } catch (err) {
      console.error('Failed to load fraud alerts:', err)
      setError(err.message || 'Failed to load fraud alerts. Please try again.')
      setAlerts([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAlerts()
  }, [loadAlerts])

  const handleAction = async (alert, action) => {
    setProcessingAction(true)
    try {
      if (action === 'escalate') {
        await investigationService.escalateFraudAlert(alert.id)
      } else if (action === 'review') {
        await investigationService.reviewFraudAlert(alert.id, {
          investigator_notes: actionNotes || alert.investigator_notes || '',
        })
      } else if (action === 'dismiss') {
        await investigationService.dismissFraudAlert(alert.id, {
          investigator_notes: actionNotes || '',
        })
      }
      setSelectedAlert(null)
      setActionNotes('')
      await loadAlerts()
    } catch (err) {
      console.error('Fraud alert action failed:', err)
      setError(err.message || 'Action failed. Please try again.')
    } finally {
      setProcessingAction(false)
    }
  }

  const filteredAlerts = alerts.filter((a) => {
    const q = search.toLowerCase()
    const matchesSearch =
      (a.claim_number || '').toLowerCase().includes(q) ||
      (a.customer_name || '').toLowerCase().includes(q)
    const matchesRisk = !riskFilter || a.risk_level === riskFilter
    const matchesStatus = !statusFilter || a.status === statusFilter
    return matchesSearch && matchesRisk && matchesStatus
  })

  const highRisk = alerts.filter((a) => a.risk_level === 'high').length
  const mediumRisk = alerts.filter((a) => a.risk_level === 'medium').length
  const activeInvestigations = alerts.filter(
    (a) => a.status === 'investigation' || a.status === 'escalated' || a.assigned_investigator
  ).length
  const avgRiskScore = alerts.length
    ? Math.round(alerts.reduce((acc, a) => acc + Number(a.risk_score || 0), 0) / alerts.length)
    : 0

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
              <Shield className="w-3.5 h-3.5 text-amber-600" />
              Special Investigations Unit (SIU)
            </span>
          </div>
          <h1 className="page-title">Fraud Investigation Dashboard</h1>
          <p className="page-subtitle">
            AI-assisted anomaly detection, risk factor scoring, and investigative workflow management
          </p>
        </div>

        <div className="flex gap-2">
          <Button asChild variant="outline"><Link to="/investigators"><UserCheck className="w-4 h-4 mr-2" />View Investigations</Link></Button>
          <Button asChild variant="primary"><Link to="/ai-decision">AI Decision Center</Link></Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </span>
          <Button variant="outline" size="sm" onClick={loadAlerts}>
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Retry
          </Button>
        </div>
      )}

      {loading && alerts.length === 0 && (
        <div className="p-8 text-center text-sm text-gray-400">Loading fraud alerts...</div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">High Fraud Risk Claims</p>
            <p className="text-2xl font-black text-red-600 mt-1">{highRisk}</p>
            <span className="text-xs text-gray-400">Investigation Recommended</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Moderate Fraud Risk</p>
            <p className="text-2xl font-black text-amber-600 mt-1">{mediumRisk}</p>
            <span className="text-xs text-gray-400">Enhanced Review</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active Investigations</p>
            <p className="text-2xl font-black text-primary mt-1">{activeInvestigations}</p>
            <span className="text-xs text-gray-400">Assigned to SIU Officers</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <UserCheck className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Average Fraud Risk Score</p>
            <p className="text-2xl font-black text-gray-900 mt-1">{avgRiskScore}%</p>
            <span className="text-xs text-gray-500">Across {alerts.length} alerts</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Table Card */}
      <Card>
        <CardHeader title="Fraud Alert Queue" subtitle="AI-flagged claims requiring SIU triage" />
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search claim number or policyholder..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              options={[
                { value: '', label: 'All Risk Levels' },
                { value: 'high', label: 'High Fraud Risk (>75%)' },
                { value: 'medium', label: 'Medium Fraud Risk (50-75%)' },
                { value: 'low', label: 'Low Fraud Risk (<50%)' },
              ]}
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="w-56"
            />
            <Select
              options={[
                { value: '', label: 'All Statuses' },
                { value: 'new', label: 'New' },
                { value: 'investigation', label: 'Under Investigation' },
                { value: 'reviewed', label: 'Reviewed' },
                { value: 'escalated', label: 'Escalated' },
                { value: 'dismissed', label: 'Dismissed' },
              ]}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-48"
            />
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Claim ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Fraud Risk Score</TableHead>
                  <TableHead>Primary Risk Factors</TableHead>
                  <TableHead>Investigation Status</TableHead>
                  <TableHead>Investigator</TableHead>
                  <TableHead>Recommended Action</TableHead>
                  <TableHead className="w-32 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAlerts.map((alert) => {
                  const riskFactors = (alert.risk_factors || []).map(normalizeRiskFactor)
                  return (
                    <TableRow key={alert.id} hover>
                      <TableCell>
                        <Link
                          to={`/claims/${alert.claim}`}
                          className="font-mono font-bold text-primary hover:underline"
                        >
                          {alert.claim_number}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-gray-900">{alert.customer_name || '—'}</div>
                        <div className="text-xs text-gray-500">
                          Flagged {alert.created_at ? formatRelativeTime(alert.created_at) : '—'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span
                            className={clsx(
                              'text-lg font-black',
                              Number(alert.risk_score) >= 75
                                ? 'text-red-600'
                                : Number(alert.risk_score) >= 50
                                  ? 'text-amber-600'
                                  : 'text-emerald-600'
                            )}
                          >
                            {Math.round(Number(alert.risk_score) || 0)}%
                          </span>
                          <Badge
                            variant={
                              alert.risk_level === 'high'
                                ? 'danger'
                                : alert.risk_level === 'medium'
                                  ? 'warning'
                                  : 'success'
                            }
                          >
                            {alert.risk_level === 'high'
                              ? 'High Risk'
                              : alert.risk_level === 'medium'
                                ? 'Moderate'
                                : 'Low'}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          {riskFactors.slice(0, 2).map((rf, i) => (
                            <div key={i} className="text-xs text-gray-700 flex items-center gap-1.5">
                              <span
                                className={clsx(
                                  'w-1.5 h-1.5 rounded-full',
                                  rf.severity === 'high' ? 'bg-red-500' : 'bg-amber-500'
                                )}
                              />
                              <span>{rf.label}</span>
                            </div>
                          ))}
                          {riskFactors.length > 2 && (
                            <button
                              type="button"
                              onClick={() => setSelectedAlert(alert)}
                              className="text-[11px] text-primary hover:underline font-medium"
                            >
                              +{riskFactors.length - 2} more factors
                            </button>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            alert.status === 'investigation' || alert.status === 'escalated'
                              ? 'warning'
                              : alert.status === 'reviewed'
                                ? 'success'
                                : alert.status === 'dismissed'
                                  ? 'neutral'
                                  : 'primary'
                          }
                        >
                          {STATUS_LABELS[alert.status] || alert.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {alert.assigned_investigator_name ? (
                          <span className="font-medium text-gray-900 text-sm flex items-center gap-1.5">
                            <UserCheck className="w-4 h-4 text-primary" />
                            {alert.assigned_investigator_name}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400 italic">Unassigned</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <p className="text-xs text-gray-700 font-medium line-clamp-2 max-w-xs">
                          {alert.ai_recommendation || '—'}
                        </p>
                      </TableCell>
                      <TableCell align="right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setSelectedAlert(alert)
                              setActionNotes(alert.investigator_notes || '')
                            }}
                            title="View Risk Breakdown"
                          >
                            <Eye className="w-3.5 h-3.5 mr-1" />
                            Examine
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Examine Alert Detail Modal */}
      {selectedAlert && (
        <Modal
          isOpen={!!selectedAlert}
          onClose={() => setSelectedAlert(null)}
          title={`Fraud Risk Assessment: ${selectedAlert.claim_number}`}
          size="lg"
        >
          <div className="space-y-6">
            <div className="p-4 bg-gray-50 rounded-xl flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-gray-500 uppercase">Customer Profile</span>
                <h4 className="font-bold text-gray-900 text-base">{selectedAlert.customer_name || '—'}</h4>
                <p className="text-xs text-gray-500 font-mono">
                  Claim: {selectedAlert.claim_number}
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs font-semibold text-gray-500 uppercase block">Fraud Risk Score</span>
                <span className="text-3xl font-black text-red-600">
                  {Math.round(Number(selectedAlert.risk_score) || 0)}%
                </span>
              </div>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 text-sm mb-3">Detected Risk Factors & Evidence</h4>
              <div className="space-y-2.5">
                {(selectedAlert.risk_factors || []).map((rf, i) => {
                  const factor = normalizeRiskFactor(rf)
                  return (
                    <div key={i} className="p-3 border border-gray-200 rounded-xl bg-white space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-gray-900">{factor.label}</span>
                        {factor.severity && (
                          <Badge
                            variant={
                              factor.severity === 'high'
                                ? 'danger'
                                : factor.severity === 'medium'
                                  ? 'warning'
                                  : 'neutral'
                            }
                          >
                            {String(factor.severity).toUpperCase()} SEVERITY
                          </Badge>
                        )}
                      </div>
                      {factor.description && (
                        <p className="text-xs text-gray-600">{factor.description}</p>
                      )}
                    </div>
                  )
                })}
                {!(selectedAlert.risk_factors || []).length && (
                  <p className="text-sm text-gray-400">No risk factors recorded for this alert.</p>
                )}
              </div>
            </div>

            {(selectedAlert.behavioral_indicators || []).length > 0 && (
              <div>
                <h4 className="font-bold text-gray-900 text-sm mb-2">Behavioral Indicators</h4>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                  {selectedAlert.behavioral_indicators.map((ind, i) => (
                    <li key={i}>{typeof ind === 'string' ? ind : JSON.stringify(ind)}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl">
              <span className="text-xs font-bold text-amber-800 uppercase block mb-1">
                Recommended Action Plan (AI Decision)
              </span>
              <p className="text-sm font-medium text-amber-950">
                {selectedAlert.ai_recommendation || '—'}
              </p>
            </div>

            <div>
              <span className="text-xs font-semibold text-gray-500 uppercase block mb-1">
                Investigator Notes
              </span>
              <Textarea
                rows={2}
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                placeholder="Add triage notes before reviewing or dismissing..."
              />
            </div>

            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-xs text-gray-500">
                Assigned: <strong>{selectedAlert.assigned_investigator_name || 'None'}</strong>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => setSelectedAlert(null)}
                  disabled={processingAction}
                >
                  <XCircle className="w-3.5 h-3.5 mr-1" />
                  Close
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleAction(selectedAlert, 'dismiss')}
                  disabled={processingAction}
                >
                  Dismiss
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => handleAction(selectedAlert, 'review')}
                  disabled={processingAction}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                  Mark Reviewed
                </Button>
                <Button
                  variant="primary"
                  onClick={() => handleAction(selectedAlert, 'escalate')}
                  disabled={processingAction}
                >
                  <Send className="w-3.5 h-3.5 mr-1" />
                  Escalate to Investigator
                </Button>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default FraudDashboard
