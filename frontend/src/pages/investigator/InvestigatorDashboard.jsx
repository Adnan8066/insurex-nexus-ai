import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield,
  Search,
  Filter,
  AlertTriangle,
  Clock,
  FileText,
  UserCheck,
  Eye,
  Send,
  MessageSquare,
  ChevronRight,
  AlertCircle,
  RefreshCw,
  Play,
  CheckCircle2,
} from 'lucide-react'
import { clsx } from 'clsx'
import { investigationService } from '../../services'
import { useAuth } from '../../context/useAuth'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Textarea, Select } from '../../components/forms/FormFields'
import { Modal } from '../../components/ui/Modal'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import { formatDate, formatRelativeTime } from '../../utils/helpers'

const PRIORITY_LABELS = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

const STATUS_LABELS = {
  open: 'Open',
  in_progress: 'In Progress',
  pending_review: 'Pending Review',
  completed: 'Completed',
  closed: 'Closed',
  on_hold: 'On Hold',
}

const ACTIVE_STATUSES = ['open', 'in_progress', 'pending_review']

const RISK_COLORS = {
  high: 'text-red-600',
  medium: 'text-amber-600',
  low: 'text-emerald-600',
}

export function InvestigatorDashboard() {
  const { user } = useAuth()
  const [investigations, setInvestigations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // Notes modal state
  const [notesModalOpen, setNotesModalOpen] = useState(false)
  const [activeInvestigation, setActiveInvestigation] = useState(null)
  const [newNoteText, setNewNoteText] = useState('')
  const [addingNote, setAddingNote] = useState(false)

  const loadInvestigations = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await investigationService.getInvestigations()
      setInvestigations(Array.isArray(data) ? data : data.results || [])
    } catch (err) {
      console.error('Failed to load investigations:', err)
      setError(err.message || 'Failed to load investigations. Please try again.')
      setInvestigations([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadInvestigations()
  }, [loadInvestigations])

  const handleOpenNotes = (investigation) => {
    setActiveInvestigation(investigation)
    setNewNoteText('')
    setNotesModalOpen(true)
  }

  const handleAddNote = async (e) => {
    e.preventDefault()
    if (!newNoteText.trim() || !activeInvestigation) return
    setAddingNote(true)
    try {
      await investigationService.addNote(activeInvestigation.id, {
        content: newNoteText.trim(),
      })
      setNewNoteText('')
      const updated = await investigationService.getInvestigation(activeInvestigation.id)
      setInvestigations((prev) =>
        prev.map((inv) => (inv.id === activeInvestigation.id ? updated : inv))
      )
      setActiveInvestigation(updated)
    } catch (err) {
      console.error('Failed to add investigation note:', err)
      setError(err.message || 'Failed to save note.')
    } finally {
      setAddingNote(false)
    }
  }

  const filteredCases = investigations.filter((inv) => {
    const q = search.toLowerCase()
    const matchesSearch =
      (inv.case_number || '').toLowerCase().includes(q) ||
      (inv.claim_number || '').toLowerCase().includes(q) ||
      (inv.customer_name || '').toLowerCase().includes(q)
    const matchesPriority = !priorityFilter || inv.priority === priorityFilter
    const matchesStatus = !statusFilter || inv.status === statusFilter
    return matchesSearch && matchesPriority && matchesStatus
  })

  const highPriorityCount = investigations.filter(
    (inv) => inv.priority === 'high' || inv.priority === 'critical'
  ).length
  const activeReviewCount = investigations.filter((inv) =>
    ACTIVE_STATUSES.includes(inv.status)
  ).length
  const totalNotes = investigations.reduce(
    (sum, inv) => sum + (inv.notes || []).length,
    0
  )

  const userName = user
    ? [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email
    : 'Investigator'
  const userEmail = user?.email || ''
  const userRole = user?.role || 'investigator'

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

        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-gray-500 uppercase">Logged in as:</label>
          <span className="text-sm font-semibold text-gray-900 bg-gray-100 px-3 py-1.5 rounded-lg">
            {userName} ({userRole})
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </span>
          <Button variant="outline" size="sm" onClick={loadInvestigations}>
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Retry
          </Button>
        </div>
      )}

      {loading && investigations.length === 0 && (
        <div className="p-8 text-center text-sm text-gray-400">Loading investigations...</div>
      )}

      {/* Investigator Profile Banner */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-primary text-white flex items-center justify-center font-bold text-xl shadow-md">
            {userName.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-gray-900">{userName}</h2>
              <span className="text-xs font-mono font-semibold bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                {userRole}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{userEmail} • Special Investigations Unit</p>
          </div>
        </div>

        <div className="flex gap-6 border-t md:border-t-0 md:border-l pt-4 md:pt-0 md:pl-6 text-sm">
          <div>
            <span className="text-xs text-gray-400 block font-medium">Assigned Cases</span>
            <span className="text-xl font-bold text-gray-900">{investigations.length}</span>
          </div>
          <div>
            <span className="text-xs text-gray-400 block font-medium">High Priority</span>
            <span className="text-xl font-bold text-red-600">{highPriorityCount}</span>
          </div>
          <div>
            <span className="text-xs text-gray-400 block font-medium">Completed</span>
            <span className="text-xl font-bold text-emerald-600">
              {investigations.filter((inv) => inv.status === 'completed' || inv.status === 'closed').length}
            </span>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Assigned Claims</p>
            <p className="text-2xl font-black text-gray-900 mt-1">{investigations.length}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <FileText className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">High-Priority Cases</p>
            <p className="text-2xl font-black text-red-600 mt-1">{highPriorityCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">In Active Review</p>
            <p className="text-2xl font-black text-amber-600 mt-1">{activeReviewCount}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Investigation Notes</p>
            <p className="text-2xl font-black text-primary mt-1">{totalNotes}</p>
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
          subtitle="Cases assigned to your account requiring SIU action"
        />
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search case #, claim #, or policyholder..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              options={[
                { value: '', label: 'All Priorities' },
                { value: 'critical', label: 'Critical' },
                { value: 'high', label: 'High Priority' },
                { value: 'medium', label: 'Medium Priority' },
                { value: 'low', label: 'Low Priority' },
              ]}
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="w-48"
            />
            <Select
              options={[
                { value: '', label: 'All Statuses' },
                { value: 'open', label: 'Open' },
                { value: 'in_progress', label: 'In Progress' },
                { value: 'pending_review', label: 'Pending Review' },
                { value: 'completed', label: 'Completed' },
                { value: 'closed', label: 'Closed' },
                { value: 'on_hold', label: 'On Hold' },
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
                  <TableHead>Case #</TableHead>
                  <TableHead>Claim Ref</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Fraud Risk</TableHead>
                  <TableHead>Investigation Status</TableHead>
                  <TableHead>Notes Count</TableHead>
                  <TableHead className="w-36 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCases.map((inv) => {
                  const notes = inv.notes || []
                  const riskLevel = inv.fraud_alert_risk_level || 'low'
                  return (
                    <TableRow key={inv.id} hover>
                      <TableCell>
                        <span className="font-mono font-bold text-gray-900">{inv.case_number}</span>
                        {inv.opened_at && (
                          <div className="text-[11px] text-gray-500">
                            Opened {formatRelativeTime(inv.opened_at)}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Link
                          to={`/claims/${inv.claim}`}
                          className="font-mono text-primary hover:underline font-semibold"
                        >
                          {inv.claim_number}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-gray-900">{inv.customer_name || '—'}</div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            inv.priority === 'critical'
                              ? 'danger'
                              : inv.priority === 'high'
                                ? 'danger'
                                : inv.priority === 'medium'
                                  ? 'warning'
                                  : 'success'
                          }
                        >
                          {PRIORITY_LABELS[inv.priority] || inv.priority || 'Medium'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className={clsx('text-sm font-bold', RISK_COLORS[riskLevel] || RISK_COLORS.low)}>
                          {(riskLevel || 'low').toUpperCase()}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            inv.status === 'completed' || inv.status === 'closed'
                              ? 'success'
                              : inv.status === 'in_progress'
                                ? 'warning'
                                : 'primary'
                          }
                        >
                          {STATUS_LABELS[inv.status] || inv.status}
                        </Badge>
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
                            onClick={() => handleOpenNotes(inv)}
                            title="Investigation Notes"
                          >
                            <MessageSquare className="w-3.5 h-3.5 mr-1" />
                            Notes
                          </Button>
                          <Link to={`/claims/${inv.claim}`}>
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
      {notesModalOpen && activeInvestigation && (
        <Modal
          isOpen={notesModalOpen}
          onClose={() => setNotesModalOpen(false)}
          title={`Investigation Log: ${activeInvestigation.case_number}`}
          size="lg"
        >
          <div className="space-y-5">
            <div className="p-3.5 bg-gray-50 rounded-xl flex items-center justify-between text-xs text-gray-600">
              <div>
                Claim: <strong className="text-gray-900 font-mono">{activeInvestigation.claim_number}</strong>
                {' • '}Customer: <strong className="text-gray-900">{activeInvestigation.customer_name || '—'}</strong>
              </div>
              <div>
                Status: <strong>{STATUS_LABELS[activeInvestigation.status] || activeInvestigation.status}</strong>
              </div>
            </div>

            {activeInvestigation.summary && (
              <div className="p-3.5 bg-blue-50/60 border border-blue-100 rounded-xl">
                <span className="text-xs font-bold text-blue-800 uppercase block mb-1">Case Summary</span>
                <p className="text-sm text-gray-700">{activeInvestigation.summary}</p>
              </div>
            )}

            {/* Note History */}
            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {(activeInvestigation.notes || []).length > 0 ? (
                (activeInvestigation.notes || []).map((note) => (
                  <div key={note.id} className="p-3.5 rounded-xl border border-gray-200 bg-white space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-gray-900 flex items-center gap-1.5">
                        <Shield className="w-3.5 h-3.5 text-primary" />
                        {note.author_name || 'Investigator'}
                        {note.is_interview && (
                          <span className="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded">
                            INTERVIEW
                          </span>
                        )}
                        {note.is_confidential && (
                          <span className="text-[10px] bg-red-100 text-red-800 px-1.5 py-0.5 rounded">
                            CONFIDENTIAL
                          </span>
                        )}
                      </span>
                      <span className="text-gray-400 font-mono">
                        {note.created_at ? formatRelativeTime(note.created_at) : ''}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed pt-1">{note.content}</p>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-gray-400 text-sm">
                  No investigation notes recorded yet for this case.
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
                <Button variant="primary" size="sm" type="submit" disabled={addingNote}>
                  <Send className="w-3.5 h-3.5 mr-1.5" />
                  {addingNote ? 'Saving...' : 'Save Note'}
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
