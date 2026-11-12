import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield,
  Search,
  AlertTriangle,
  Clock,
  FileText,
  Send,
  MessageSquare,
  Play,
  CheckCircle2,
  Paperclip,
  Star,
} from 'lucide-react'
import { clsx } from 'clsx'
import { investigationService } from '../../services'
import { formatApiError } from '../../services/api'
import { useAuth } from '../../context/useAuth'
import { useToast } from '../../components/ui/toastHooks'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Textarea, Select } from '../../components/forms/FormFields'
import { Modal } from '../../components/ui/Modal'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/tables/DataTable'
import { formatRelativeTime } from '../../utils/helpers'
import { Alert } from '../../components/ui/Alert'
import { LoadingState } from '../../components/ui/LoadingSpinner'

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
// Mirrors STARTABLE_STATUSES / COMPLETABLE_STATUSES in apps/investigations/views.py.
const STARTABLE_STATUSES = ['open', 'on_hold', 'pending_review']
const COMPLETABLE_STATUSES = ['in_progress', 'pending_review']
const CLOSED_STATUSES = ['completed', 'closed']

const EVIDENCE_TYPES = [
  { value: 'document', label: 'Document' },
  { value: 'photo', label: 'Photo' },
  { value: 'video', label: 'Video' },
  { value: 'audio', label: 'Audio' },
  { value: 'statement', label: 'Statement' },
  { value: 'surveillance', label: 'Surveillance' },
  { value: 'digital', label: 'Digital forensics' },
  { value: 'financial', label: 'Financial record' },
  { value: 'medical', label: 'Medical record' },
  { value: 'other', label: 'Other' },
]
const EVIDENCE_TYPE_LABELS = Object.fromEntries(EVIDENCE_TYPES.map((t) => [t.value, t.label]))
// Same allow-list and size limit as common/uploads.py (EVIDENCE_EXTENSIONS, MAX_UPLOAD_BYTES).
const EVIDENCE_ACCEPT = '.jpg,.jpeg,.png,.webp,.bmp,.pdf,.mp4,.mov,.m4a,.mp3,.wav'
const MAX_EVIDENCE_BYTES = 25 * 1024 * 1024

const EMPTY_EVIDENCE = { evidence_type: 'document', title: '', description: '', source: '', is_key_evidence: false }
const EMPTY_COMPLETION = { findings: '', conclusion: '', recommendation: '' }

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

  const toast = useToast()
  const [startingId, setStartingId] = useState(null)

  // Evidence modal state
  const [evidenceCase, setEvidenceCase] = useState(null)
  const [evidenceForm, setEvidenceForm] = useState(EMPTY_EVIDENCE)
  const [evidenceFile, setEvidenceFile] = useState(null)
  const [evidenceError, setEvidenceError] = useState(null)
  const [savingEvidence, setSavingEvidence] = useState(false)
  const [fileInputKey, setFileInputKey] = useState(0)

  // Complete modal state
  const [completeCase, setCompleteCase] = useState(null)
  const [completionForm, setCompletionForm] = useState(EMPTY_COMPLETION)
  const [completionError, setCompletionError] = useState(null)
  const [completing, setCompleting] = useState(false)

  const loadInvestigations = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await investigationService.getInvestigations()
      setInvestigations(Array.isArray(data) ? data : data.results || [])
    } catch (err) {
      setError(formatApiError(err, 'Failed to load investigations. Please try again.'))
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
      setError(formatApiError(err, 'Failed to save note.'))
    } finally {
      setAddingNote(false)
    }
  }

  const replaceInvestigation = (updated) => {
    setInvestigations((prev) => prev.map((inv) => (inv.id === updated.id ? updated : inv)))
  }

  const handleStart = async (investigation) => {
    setStartingId(investigation.id)
    try {
      const updated = await investigationService.startInvestigation(investigation.id)
      replaceInvestigation(updated)
      toast.success(`${investigation.case_number} is now in progress.`)
    } catch (err) {
      toast.error(formatApiError(err, 'Could not start the investigation.'))
    } finally {
      setStartingId(null)
    }
  }

  const handleOpenEvidence = (investigation) => {
    setEvidenceCase(investigation)
    setEvidenceForm(EMPTY_EVIDENCE)
    setEvidenceFile(null)
    setEvidenceError(null)
    setFileInputKey((k) => k + 1)
  }

  const handleEvidenceFile = (e) => {
    const file = e.target.files?.[0] || null
    if (file && file.size > MAX_EVIDENCE_BYTES) {
      setEvidenceError('File is too large. The maximum size is 25 MB.')
      setEvidenceFile(null)
      setFileInputKey((k) => k + 1)
      return
    }
    setEvidenceError(null)
    setEvidenceFile(file)
  }

  const handleAddEvidence = async (e) => {
    e.preventDefault()
    if (!evidenceCase || !evidenceForm.title.trim()) return
    setSavingEvidence(true)
    setEvidenceError(null)
    try {
      const formData = new FormData()
      formData.append('evidence_type', evidenceForm.evidence_type)
      formData.append('title', evidenceForm.title.trim())
      formData.append('description', evidenceForm.description.trim())
      formData.append('source', evidenceForm.source.trim())
      formData.append('is_key_evidence', evidenceForm.is_key_evidence ? 'true' : 'false')
      if (evidenceFile) formData.append('file', evidenceFile)
      await investigationService.addEvidence(evidenceCase.id, formData)
      const updated = await investigationService.getInvestigation(evidenceCase.id)
      replaceInvestigation(updated)
      setEvidenceCase(updated)
      setEvidenceForm(EMPTY_EVIDENCE)
      setEvidenceFile(null)
      setFileInputKey((k) => k + 1)
      toast.success('Evidence added to the case.')
    } catch (err) {
      setEvidenceError(formatApiError(err, 'Could not save the evidence.'))
    } finally {
      setSavingEvidence(false)
    }
  }

  const handleOpenComplete = (investigation) => {
    setCompleteCase(investigation)
    setCompletionForm({
      findings: investigation.findings || '',
      conclusion: investigation.conclusion || '',
      recommendation: investigation.recommendation || '',
    })
    setCompletionError(null)
  }

  const handleComplete = async (e) => {
    e.preventDefault()
    if (!completeCase || !completionForm.findings.trim()) return
    setCompleting(true)
    setCompletionError(null)
    try {
      const updated = await investigationService.completeInvestigation(completeCase.id, {
        findings: completionForm.findings.trim(),
        conclusion: completionForm.conclusion.trim(),
        recommendation: completionForm.recommendation.trim(),
      })
      replaceInvestigation(updated)
      setCompleteCase(null)
      toast.success(`${completeCase.case_number} is complete. The claim can now go for an approval decision.`)
    } catch (err) {
      setCompletionError(formatApiError(err, 'Could not complete the investigation.'))
    } finally {
      setCompleting(false)
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
          <h1 className="page-title">Investigation Cases</h1>
          <p className="page-subtitle">
            Fraud cases being investigated, case notes, and the warning signs on each claim
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-bold text-gray-500 uppercase">Logged in as:</label>
          <span className="text-sm font-semibold text-gray-900 bg-gray-100 px-3 py-1.5 rounded-lg">
            {userName} ({userRole})
          </span>
        </div>
      </div>

      {error && (
        <Alert onRetry={loadInvestigations}>{error}</Alert>
      )}

      {loading && investigations.length === 0 && (
        <LoadingState label="Loading investigations…" />
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
          subtitle="Cases waiting for investigation"
        />
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="flex-1">
              <Input
                placeholder="Search case #, claim #, or policyholder..."
                aria-label="Search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                leftIcon={<Search className="w-4 h-4 text-gray-400" />}
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
                  <TableHead className="text-right">Actions</TableHead>
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
                          className="whitespace-nowrap font-mono font-semibold text-primary hover:underline"
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
                        <div className="flex items-center justify-end gap-1.5 whitespace-nowrap">
                          {STARTABLE_STATUSES.includes(inv.status) && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleStart(inv)}
                              disabled={startingId === inv.id}
                            >
                              <Play className="w-3.5 h-3.5 mr-1" />
                              {startingId === inv.id ? 'Starting…' : 'Start'}
                            </Button>
                          )}
                          {COMPLETABLE_STATUSES.includes(inv.status) && (
                            <Button variant="primary" size="sm" onClick={() => handleOpenComplete(inv)}>
                              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                              Complete
                            </Button>
                          )}
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleOpenEvidence(inv)}
                          >
                            <Paperclip className="w-3.5 h-3.5 mr-1" />
                            Evidence ({(inv.evidence || []).length})
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleOpenNotes(inv)}
                            title="Investigation Notes"
                          >
                            <MessageSquare className="w-3.5 h-3.5 mr-1" />
                            Notes
                          </Button>
                          <Button asChild variant="outline" size="sm"><Link to={`/claims/${inv.claim}`}>Details</Link></Button>
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
                  {addingNote ? 'Saving…' : 'Save note'}
                </Button>
              </div>
            </form>
          </div>
        </Modal>
      )}

      {/* Evidence Modal */}
      {evidenceCase && (
        <Modal
          isOpen={!!evidenceCase}
          onClose={() => setEvidenceCase(null)}
          title={`Evidence: ${evidenceCase.case_number}`}
          size="lg"
        >
          <div className="space-y-5">
            <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
              {(evidenceCase.evidence || []).length > 0 ? (
                evidenceCase.evidence.map((item) => (
                  <div key={item.id} className="p-3.5 rounded-xl border border-gray-200 bg-white space-y-1">
                    <div className="flex items-center justify-between gap-3 text-xs">
                      <span className="font-bold text-gray-900 flex items-center gap-1.5">
                        {item.title}
                        <span className="text-[10px] bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">
                          {(EVIDENCE_TYPE_LABELS[item.evidence_type] || item.evidence_type).toUpperCase()}
                        </span>
                        {item.is_key_evidence && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded inline-flex items-center gap-0.5">
                            <Star className="w-3 h-3" /> KEY
                          </span>
                        )}
                      </span>
                      <span className="text-gray-400 font-mono shrink-0">
                        {item.collected_at ? formatRelativeTime(item.collected_at) : ''}
                      </span>
                    </div>
                    {item.description && <p className="text-sm text-gray-700">{item.description}</p>}
                    <div className="flex flex-wrap gap-x-4 text-xs text-gray-500">
                      {item.source && <span>Source: {item.source}</span>}
                      {item.collected_by_name && <span>Added by {item.collected_by_name}</span>}
                      {item.file && (
                        <a href={item.file} target="_blank" rel="noreferrer" className="text-primary font-semibold hover:underline">
                          Open file
                        </a>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-gray-400 text-sm">No evidence recorded yet for this case.</div>
              )}
            </div>

            {CLOSED_STATUSES.includes(evidenceCase.status) ? (
              <p className="text-xs text-gray-500 pt-3 border-t">This case is {STATUS_LABELS[evidenceCase.status].toLowerCase()}, so no more evidence can be added here.</p>
            ) : (
              <form onSubmit={handleAddEvidence} className="space-y-3 pt-3 border-t">
                {evidenceError && <Alert>{evidenceError}</Alert>}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Select
                    label="Type"
                    options={EVIDENCE_TYPES}
                    value={evidenceForm.evidence_type}
                    onChange={(e) => setEvidenceForm((f) => ({ ...f, evidence_type: e.target.value }))}
                  />
                  <Input
                    label="Title"
                    placeholder="e.g. Repair invoice from garage"
                    value={evidenceForm.title}
                    onChange={(e) => setEvidenceForm((f) => ({ ...f, title: e.target.value }))}
                    maxLength={200}
                    required
                  />
                </div>
                <Textarea
                  label="Description"
                  rows={2}
                  placeholder="What this shows and why it matters"
                  value={evidenceForm.description}
                  onChange={(e) => setEvidenceForm((f) => ({ ...f, description: e.target.value }))}
                />
                <Input
                  label="Source"
                  placeholder="e.g. Customer, police station, CCTV"
                  value={evidenceForm.source}
                  onChange={(e) => setEvidenceForm((f) => ({ ...f, source: e.target.value }))}
                  maxLength={200}
                />
                <div>
                  <label htmlFor="evidence-file" className="input-label">File (optional)</label>
                  <input
                    key={fileInputKey}
                    id="evidence-file"
                    type="file"
                    accept={EVIDENCE_ACCEPT}
                    onChange={handleEvidenceFile}
                    className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-gray-100 file:px-3 file:py-1.5 file:text-sm file:font-semibold"
                  />
                  <p className="text-xs text-gray-400 mt-1">Images, PDF, video or audio, up to 25 MB.</p>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={evidenceForm.is_key_evidence}
                      onChange={(e) => setEvidenceForm((f) => ({ ...f, is_key_evidence: e.target.checked }))}
                    />
                    Key evidence
                  </label>
                  <Button variant="primary" size="sm" type="submit" disabled={savingEvidence || !evidenceForm.title.trim()}>
                    <Paperclip className="w-3.5 h-3.5 mr-1.5" />
                    {savingEvidence ? 'Saving…' : 'Add evidence'}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </Modal>
      )}

      {/* Complete Investigation Modal */}
      {completeCase && (
        <Modal
          isOpen={!!completeCase}
          onClose={() => setCompleteCase(null)}
          title={`Complete ${completeCase.case_number}`}
          size="lg"
        >
          <form onSubmit={handleComplete} className="space-y-4">
            <p className="text-sm text-gray-600">
              Completing the case records your findings on claim{' '}
              <strong className="font-mono text-gray-900">{completeCase.claim_number}</strong>. For a high-risk
              claim, this is what allows an employee to approve or reject it.
            </p>
            {completionError && <Alert>{completionError}</Alert>}
            <Textarea
              label="Findings (required)"
              rows={4}
              placeholder="What you checked and what you found"
              value={completionForm.findings}
              onChange={(e) => setCompletionForm((f) => ({ ...f, findings: e.target.value }))}
              required
            />
            <Textarea
              label="Conclusion"
              rows={2}
              placeholder="e.g. Claim is genuine / evidence of an inflated repair bill"
              value={completionForm.conclusion}
              onChange={(e) => setCompletionForm((f) => ({ ...f, conclusion: e.target.value }))}
            />
            <Textarea
              label="Recommendation"
              rows={2}
              placeholder="e.g. Approve, approve a reduced amount, or reject"
              value={completionForm.recommendation}
              onChange={(e) => setCompletionForm((f) => ({ ...f, recommendation: e.target.value }))}
            />
            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button variant="outline" size="sm" type="button" onClick={() => setCompleteCase(null)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" disabled={completing || !completionForm.findings.trim()}>
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                {completing ? 'Completing…' : 'Complete investigation'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

export default InvestigatorDashboard
