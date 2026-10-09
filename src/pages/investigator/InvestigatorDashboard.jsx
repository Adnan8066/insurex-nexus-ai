import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Users,
  Shield,
  Search,
  Filter,
  AlertTriangle,
  Clock,
  CheckCircle2,
  FileText,
  UserCheck,
  Eye,
  Plus,
  Send,
  MessageSquare,
  BadgeAlert,
  ChevronRight,
  TrendingUp,
} from 'lucide-react'
import { clsx } from 'clsx'
import { mockInvestigators, mockFraudAlerts } from '../../data/operations'
import { mockClaims } from '../../data/claims'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Textarea, Select } from '../../components/forms/FormFields'
import { Modal } from '../../components/ui/Modal'
import { formatCurrency, formatDate, formatRelativeTime } from '../../utils/helpers'

export function InvestigatorDashboard() {
  const [investigators] = useState(mockInvestigators)
  const [selectedInvestigatorId, setSelectedInvestigatorId] = useState(1)
  const [investigator, setInvestigator] = useState(mockInvestigators[0])
  const [search, setSearch] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')

  // Notes state
  const [notesModalOpen, setNotesModalOpen] = useState(false)
  const [activeCaseForNotes, setActiveCaseForNotes] = useState(null)
  const [newNoteText, setNewNoteText] = useState('')
  const [caseNotes, setCaseNotes] = useState({
    'CLM-2024-001235': [
      { id: 1, author: 'Emily Rodriguez', text: 'Contacted towing company. Vehicle odometer discrepancy noted between tow slip and claim form.', timestamp: '2024-02-12 11:30' },
      { id: 2, author: 'Emily Rodriguez', text: 'Scheduled recorded audio interview with driver for Feb 16th.', timestamp: '2024-02-13 15:45' },
    ],
    'CLM-2023-000456': [
      { id: 1, author: 'Emily Rodriguez', text: 'Obtained dashcam recording from witness vehicle. Liability completely confirmed in favor of claimant.', timestamp: '2023-06-14 09:15' },
      { id: 2, author: 'Emily Rodriguez', text: 'SIU clear endorsement submitted to senior adjuster.', timestamp: '2023-06-15 14:00' },
    ],
  })

  useEffect(() => {
    const inv = investigators.find((i) => i.id === Number(selectedInvestigatorId)) || investigators[0]
    setInvestigator(inv)
  }, [selectedInvestigatorId, investigators])

  // Get claims assigned to this investigator
  const assignedClaims = mockClaims.filter((c) =>
    investigator.assignedClaims.includes(c.id) ||
    c.assignedInvestigator === investigator.name ||
    mockFraudAlerts.some((f) => f.claimId === c.id && f.assignedInvestigator === investigator.name)
  )

  const handleOpenNotes = (claim) => {
    setActiveCaseForNotes(claim)
    setNotesModalOpen(true)
  }

  const handleAddNote = (e) => {
    e.preventDefault()
    if (!newNoteText.trim() || !activeCaseForNotes) return
    const currentList = caseNotes[activeCaseForNotes.id] || []
    setCaseNotes({
      ...caseNotes,
      [activeCaseForNotes.id]: [
        ...currentList,
        {
          id: Date.now(),
          author: investigator.name,
          text: newNoteText.trim(),
          timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
        },
      ],
    })
    setNewNoteText('')
  }

  const filteredCases = assignedClaims.filter((c) => {
    const q = search.toLowerCase()
    const matchSearch = c.claimNumber.toLowerCase().includes(q) || c.customerName.toLowerCase().includes(q)
    const matchPriority = !priorityFilter || c.aiAssessment?.claimPriority?.toLowerCase() === priorityFilter.toLowerCase()
    return matchSearch && matchPriority
  })

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              <Shield className="w-3.5 h-3.5 text-blue-600" />
              SIU Investigator Console
            </span>
          </div>
          <h1 className="page-title">Investigator Workspace</h1>
          <p className="page-subtitle">
            Manage assigned special investigations, log evidentiary interview notes, and review AI fraud indicators
          </p>
        </div>

        {/* Investigator Switcher */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-gray-500 uppercase">Investigator:</label>
          <select
            value={selectedInvestigatorId}
            onChange={(e) => setSelectedInvestigatorId(e.target.value)}
            className="input-field text-sm font-semibold py-2 px-3 border border-gray-300 rounded-lg bg-white"
            aria-label="Active Investigator"
          >
            {investigators.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name} ({i.badgeNumber})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Investigator Profile Banner */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-primary text-white flex items-center justify-center font-bold text-xl shadow-md">
            {investigator.name.split(' ').map((n) => n[0]).join('')}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-gray-900">{investigator.name}</h2>
              <span className="text-xs font-mono font-semibold bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                {investigator.badgeNumber}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{investigator.department} • {investigator.email}</p>
            <div className="flex gap-1.5 mt-2 flex-wrap">
              {investigator.specialties.map((s, i) => (
                <span key={i} className="text-[11px] font-medium bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-6 border-t md:border-t-0 md:border-l pt-4 md:pt-0 md:pl-6 text-sm">
          <div>
            <span className="text-xs text-gray-400 block font-medium">Lifetime Cases</span>
            <span className="text-xl font-bold text-gray-900">{investigator.performance.totalCases}</span>
          </div>
          <div>
            <span className="text-xs text-gray-400 block font-medium">Resolved</span>
            <span className="text-xl font-bold text-emerald-600">{investigator.performance.resolvedCases}</span>
          </div>
          <div>
            <span className="text-xs text-gray-400 block font-medium">Avg Resolution</span>
            <span className="text-xl font-bold text-gray-900">{investigator.performance.averageResolutionDays}d</span>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Assigned Claims</p>
            <p className="text-2xl font-black text-gray-900 mt-1">{assignedClaims.length}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <FileText className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">High-Priority Cases</p>
            <p className="text-2xl font-black text-red-600 mt-1">
              {assignedClaims.filter((c) => c.aiAssessment?.claimPriority === 'High').length || 1}
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">In Active Review</p>
            <p className="text-2xl font-black text-amber-600 mt-1">
              {assignedClaims.filter((c) => c.status !== 'closed').length}
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Investigation Notes</p>
            <p className="text-2xl font-black text-primary mt-1">
              {Object.values(caseNotes).flat().length}
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <MessageSquare className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Assigned Claims Docket */}
      <Card>
        <CardHeader
          title="Assigned Investigation Docket"
          subtitle="Cases assigned to your badge number requiring SIU action"
        />
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search assigned claims or policyholders..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              options={[
                { value: '', label: 'All Priorities' },
                { value: 'high', label: 'High Priority' },
                { value: 'medium', label: 'Medium Priority' },
                { value: 'low', label: 'Low Priority' },
              ]}
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="w-48"
            />
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Claim ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Incident Type & Date</TableHead>
                  <TableHead>AI Fraud Risk</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Investigation Status</TableHead>
                  <TableHead>Notes Count</TableHead>
                  <TableHead className="w-36 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCases.map((claim) => {
                  const fraudAlert = mockFraudAlerts.find((f) => f.claimId === claim.id)
                  const fraudScore = fraudAlert?.fraudRiskScore || claim.aiAssessment?.fraudRiskScore || 20
                  const notes = caseNotes[claim.id] || []

                  return (
                    <TableRow key={claim.id} hover>
                      <TableCell>
                        <Link to={`/claims/${claim.id}`} className="font-mono font-bold text-primary hover:underline">
                          {claim.claimNumber}
                        </Link>
                        <div className="text-[11px] text-gray-500 font-mono">{claim.policyNumber}</div>
                      </TableCell>
                      <TableCell>
                        <div className="font-semibold text-gray-900">{claim.customerName}</div>
                        <div className="text-xs text-gray-500">{claim.vehicle?.make} {claim.vehicle?.model}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-gray-900">{claim.incidentType}</div>
                        <div className="text-xs text-gray-500">{formatDate(claim.incidentDate)}</div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className={clsx(
                            'font-black text-sm',
                            fraudScore >= 70 ? 'text-red-600' : fraudScore >= 40 ? 'text-amber-600' : 'text-emerald-600'
                          )}>
                            {fraudScore}%
                          </span>
                          <span className="text-xs text-gray-500">
                            {fraudScore >= 70 ? 'High' : fraudScore >= 40 ? 'Medium' : 'Low'}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            claim.aiAssessment?.claimPriority === 'High' ? 'danger' :
                            claim.aiAssessment?.claimPriority === 'Medium' ? 'warning' : 'success'
                          }
                        >
                          {claim.aiAssessment?.claimPriority || 'Medium'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={claim.status} />
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1 text-xs text-gray-600 bg-gray-100 px-2.5 py-1 rounded-full font-medium">
                          <MessageSquare className="w-3 h-3 text-primary" />
                          {notes.length} note(s)
                        </span>
                      </TableCell>
                      <TableCell align="right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleOpenNotes(claim)}
                            title="Investigation Notes"
                          >
                            <MessageSquare className="w-3.5 h-3.5 mr-1" />
                            Notes
                          </Button>
                          <Link to={`/claims/${claim.id}`}>
                            <Button variant="outline" size="sm">
                              Details
                            </Button>
                          </Link>
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

      {/* Case Notes Modal */}
      {notesModalOpen && activeCaseForNotes && (
        <Modal
          isOpen={notesModalOpen}
          onClose={() => setNotesModalOpen(false)}
          title={`Investigation Log: ${activeCaseForNotes.claimNumber}`}
          size="lg"
        >
          <div className="space-y-5">
            <div className="p-3.5 bg-gray-50 rounded-xl flex items-center justify-between text-xs text-gray-600">
              <div>
                Subject: <strong className="text-gray-900">{activeCaseForNotes.customerName}</strong> • Policy: <span className="font-mono">{activeCaseForNotes.policyNumber}</span>
              </div>
              <div>
                Incident: <strong>{activeCaseForNotes.incidentType}</strong> ({formatDate(activeCaseForNotes.incidentDate)})
              </div>
            </div>

            {/* Note History */}
            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {(caseNotes[activeCaseForNotes.id] || []).length > 0 ? (
                (caseNotes[activeCaseForNotes.id] || []).map((note) => (
                  <div key={note.id} className="p-3.5 rounded-xl border border-gray-200 bg-white space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-gray-900 flex items-center gap-1.5">
                        <Shield className="w-3.5 h-3.5 text-primary" />
                        {note.author}
                      </span>
                      <span className="text-gray-400 font-mono">{note.timestamp}</span>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed pt-1">{note.text}</p>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-gray-400 text-sm">
                  No investigation notes recorded yet for this claim.
                </div>
              )}
            </div>

            {/* Add Note Form */}
            <form onSubmit={handleAddNote} className="space-y-3 pt-3 border-t">
              <Textarea
                placeholder="Type field note, witness interview transcript summary, or surveillance observation..."
                rows={3}
                value={newNoteText}
                onChange={(e) => setNewNoteText(e.target.value)}
                required
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">Notes are timestamped and permanently audited.</span>
                <Button variant="primary" size="sm" type="submit">
                  <Send className="w-3.5 h-3.5 mr-1.5" />
                  Save Note
                </Button>
              </div>
            </form>
          </div>
        </Modal>
      )}
    </div>
  )
}

export default InvestigatorDashboard
