import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  Shield,
  Search,
  Filter,
  UserCheck,
  CheckCircle2,
  Clock,
  Eye,
  TrendingUp,
  FileText,
  User,
  ArrowRight,
  ExternalLink,
} from 'lucide-react'
import { clsx } from 'clsx'
import { mockFraudAlerts, mockInvestigators } from '../../data/operations'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/forms/FormFields'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import { Modal } from '../../components/ui/Modal'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'

export function FraudDashboard() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [targetAlertForAssign, setTargetAlertForAssign] = useState(null)
  const [selectedInvestigator, setSelectedInvestigator] = useState('')
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setAlerts(mockFraudAlerts)
      setLoading(false)
    }, 300)
    return () => clearTimeout(timer)
  }, [])

  const handleAssign = (alert) => {
    setTargetAlertForAssign(alert)
    setSelectedInvestigator(alert.assignedInvestigator || mockInvestigators[0].name)
    setAssignModalOpen(true)
  }

  const handleSaveAssignment = () => {
    if (!targetAlertForAssign) return
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === targetAlertForAssign.id
          ? { ...a, assignedInvestigator: selectedInvestigator, status: 'investigation' }
          : a
      )
    )
    setAssignModalOpen(false)
    setTargetAlertForAssign(null)
  }

  const filteredAlerts = alerts.filter((a) => {
    const matchesSearch =
      a.claimNumber.toLowerCase().includes(search.toLowerCase()) ||
      a.customerName.toLowerCase().includes(search.toLowerCase()) ||
      a.policyNumber.toLowerCase().includes(search.toLowerCase())
    const matchesRisk = !riskFilter || a.riskLevel === riskFilter
    return matchesSearch && matchesRisk
  })

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
          <Link to="/investigators">
            <Button variant="outline">
              <UserCheck className="w-4 h-4 mr-2" />
              View Investigators
            </Button>
          </Link>
          <Link to="/ai-decision">
            <Button variant="primary">
              AI Decision Center
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">High Fraud Risk Claims</p>
            <p className="text-2xl font-black text-red-600 mt-1">
              {alerts.filter((a) => a.riskLevel === 'high').length}
            </p>
            <span className="text-xs text-gray-400">Investigation Recommended</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Moderate Fraud Risk</p>
            <p className="text-2xl font-black text-amber-600 mt-1">
              {alerts.filter((a) => a.riskLevel === 'medium').length}
            </p>
            <span className="text-xs text-gray-400">Enhanced Review</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active Investigations</p>
            <p className="text-2xl font-black text-primary mt-1">
              {alerts.filter((a) => a.assignedInvestigator).length}
            </p>
            <span className="text-xs text-gray-400">Assigned to SIU Officers</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <UserCheck className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Average Fraud Risk Score</p>
            <p className="text-2xl font-black text-gray-900 mt-1">
              {alerts.length ? Math.round(alerts.reduce((acc, a) => acc + a.fraudRiskScore, 0) / alerts.length) : 0}%
            </p>
            <span className="text-xs text-emerald-600 font-medium">94.7% Model Accuracy</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Table Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search high risk claims, policyholders, policy numbers..."
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
                {filteredAlerts.map((alert) => (
                  <TableRow key={alert.id} hover>
                    <TableCell>
                      <Link to={`/claims/${alert.claimId}`} className="font-mono font-bold text-primary hover:underline">
                        {alert.claimNumber}
                      </Link>
                      <div className="text-[11px] text-gray-500 font-mono">{alert.policyNumber}</div>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium text-gray-900">{alert.customerName}</div>
                      <div className="text-xs text-gray-500">Flagged {formatRelativeTime(alert.createdAt)}</div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className={clsx(
                          'text-lg font-black',
                          alert.fraudRiskScore >= 75 ? 'text-red-600' :
                          alert.fraudRiskScore >= 50 ? 'text-amber-600' : 'text-emerald-600'
                        )}>
                          {alert.fraudRiskScore}%
                        </span>
                        <Badge variant={alert.riskLevel === 'high' ? 'danger' : alert.riskLevel === 'medium' ? 'warning' : 'success'}>
                          {alert.riskLevel === 'high' ? 'High Risk' : alert.riskLevel === 'medium' ? 'Moderate' : 'Low'}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        {alert.riskFactors.slice(0, 2).map((rf, i) => (
                          <div key={i} className="text-xs text-gray-700 flex items-center gap-1.5">
                            <span className={clsx(
                              'w-1.5 h-1.5 rounded-full',
                              rf.severity === 'high' ? 'bg-red-500' : 'bg-amber-500'
                            )} />
                            <span>{rf.factor}</span>
                          </div>
                        ))}
                        {alert.riskFactors.length > 2 && (
                          <button
                            type="button"
                            onClick={() => setSelectedAlert(alert)}
                            className="text-[11px] text-primary hover:underline font-medium"
                          >
                            +{alert.riskFactors.length - 2} more factors
                          </button>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={alert.status === 'investigation' ? 'warning' : 'neutral'}>
                        {alert.status === 'investigation' ? 'Under Investigation' : 'Investigation Recommended'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {alert.assignedInvestigator ? (
                        <span className="font-medium text-gray-900 text-sm flex items-center gap-1.5">
                          <UserCheck className="w-4 h-4 text-primary" />
                          {alert.assignedInvestigator}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400 italic">Unassigned</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <p className="text-xs text-gray-700 font-medium line-clamp-2 max-w-xs">
                        {alert.aiRecommendation}
                      </p>
                    </TableCell>
                    <TableCell align="right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setSelectedAlert(alert)}
                          title="View Risk Breakdown"
                        >
                          <Eye className="w-3.5 h-3.5 mr-1" />
                          Examine
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleAssign(alert)}
                          title="Assign Investigator"
                        >
                          Assign
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
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
          title={`Fraud Risk Assessment: ${selectedAlert.claimNumber}`}
          size="lg"
        >
          <div className="space-y-6">
            <div className="p-4 bg-gray-50 rounded-xl flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-gray-500 uppercase">Customer Profile</span>
                <h4 className="font-bold text-gray-900 text-base">{selectedAlert.customerName}</h4>
                <p className="text-xs text-gray-500 font-mono">Policy: {selectedAlert.policyNumber}</p>
              </div>
              <div className="text-right">
                <span className="text-xs font-semibold text-gray-500 uppercase block">Fraud Risk Score</span>
                <span className="text-3xl font-black text-red-600">{selectedAlert.fraudRiskScore}%</span>
              </div>
            </div>

            <div>
              <h4 className="font-bold text-gray-900 text-sm mb-3">Detected Risk Factors & Evidence</h4>
              <div className="space-y-2.5">
                {selectedAlert.riskFactors.map((rf, i) => (
                  <div key={i} className="p-3 border border-gray-200 rounded-xl bg-white space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-gray-900">{rf.factor}</span>
                      <Badge variant={rf.severity === 'high' ? 'danger' : rf.severity === 'medium' ? 'warning' : 'neutral'}>
                        {rf.severity.toUpperCase()} SEVERITY
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-600">{rf.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl">
              <span className="text-xs font-bold text-amber-800 uppercase block mb-1">
                Recommended Action Plan (AI Decision)
              </span>
              <p className="text-sm font-medium text-amber-950">{selectedAlert.aiRecommendation}</p>
            </div>

            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-xs text-gray-500">
                Assigned: <strong>{selectedAlert.assignedInvestigator || 'None'}</strong>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setSelectedAlert(null)}>
                  Close
                </Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    const a = selectedAlert
                    setSelectedAlert(null)
                    handleAssign(a)
                  }}
                >
                  Assign Investigator
                </Button>
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Assign Investigator Modal */}
      {assignModalOpen && (
        <Modal
          isOpen={assignModalOpen}
          onClose={() => setAssignModalOpen(false)}
          title={`Assign Investigator: ${targetAlertForAssign?.claimNumber}`}
          size="md"
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Select an investigator from the Special Investigations Unit to handle this flagged claim.
            </p>

            <div className="space-y-2">
              {mockInvestigators.map((inv) => (
                <label
                  key={inv.id}
                  className={clsx(
                    'flex items-center justify-between p-3.5 border rounded-xl cursor-pointer transition',
                    selectedInvestigator === inv.name ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : 'border-gray-200 hover:bg-gray-50'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="radio"
                      name="investigator"
                      value={inv.name}
                      checked={selectedInvestigator === inv.name}
                      onChange={(e) => setSelectedInvestigator(e.target.value)}
                      className="text-primary"
                    />
                    <div>
                      <span className="font-semibold text-gray-900 text-sm block">{inv.name}</span>
                      <span className="text-xs text-gray-500">{inv.department} • {inv.badgeNumber}</span>
                    </div>
                  </div>
                  <div className="text-right text-xs">
                    <span className="text-gray-500 block">Active Cases: {inv.assignedClaims.length}</span>
                    <span className="text-emerald-600 font-semibold">{inv.performance.resolvedCases} resolved</span>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="secondary" onClick={() => setAssignModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveAssignment}>
                Confirm Assignment
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default FraudDashboard
