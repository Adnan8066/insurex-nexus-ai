import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  GitBranch,
  Brain,
  CheckCircle2,
  Cpu,
  ArrowDown,
  Sparkles,
  Bot,
  Activity,
  Play,
  Check,
  AlertCircle,
  Info,
  RefreshCw,
} from 'lucide-react'
import { clsx } from 'clsx'
import { assessmentService, claimService } from '../../services'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { formatCurrency, formatDate } from '../../utils/helpers'

const normalizeAgent = (a, idx) => ({
  id: a.id || a.agent_type || `agent-${idx}`,
  name: a.name || a.agent_type || a.title || `Agent ${idx + 1}`,
  confidence: a.confidence == null ? null : Math.round(Number(a.confidence) <= 1 ? Number(a.confidence) * 100 : Number(a.confidence)),
  processingTime: a.processing_time == null && a.processing_time_seconds == null ? null : Number(a.processing_time || a.processing_time_seconds || a.processingTime),
  input: a.input || a.input_data || {},
  output: a.output || a.output_data || {},
})

const normalizeRL = (rl) => ({
  available: rl.available ?? Boolean(rl.action || rl.recommended_action || rl.recommendation),
  optimizationScore: Math.round(Number(rl.optimization_score || rl.optimizationScore || rl.score || 0)),
  action: rl.action || rl.recommended_action || rl.recommendation || 'Not configured',
  explanation: rl.explanation || rl.rationale || rl.reason || '',
  estimatedProcessingDays: Math.round(Number(rl.estimated_processing_days || rl.estimatedProcessingDays || 0)),
  recommendedAdjuster: rl.recommended_adjuster || rl.recommendedAdjuster || rl.adjuster || 'Auto-assigned',
  investigatorRequired: Boolean(rl.investigator_required || rl.investigatorRequired || rl.siu_required),
})

const normalizeDecision = (fd, flow) => ({
  status: fd.status || fd.decision || fd.outcome || 'Pending',
  amount: Number(fd.recommended_amount || fd.amount || fd.payout_amount || fd.approved_amount || 0),
  rationale: fd.rationale || fd.reason || fd.explanation || '',
  decidedBy: fd.decided_by || fd.decidedBy || flow?.decided_by_name || 'AI Decision Engine',
  decidedAt: fd.decided_at || fd.decidedAt || flow?.decided_at || '',
})

export function AIDecisionCenter() {
  const [claims, setClaims] = useState([])
  const [flows, setFlows] = useState([])
  const [selectedClaimId, setSelectedClaimId] = useState('')
  const [isSimulating, setIsSimulating] = useState(false)
  const [simulationStep, setSimulationStep] = useState(6)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [claimsRes, flowsRes] = await Promise.all([
        claimService.getClaims(),
        assessmentService.getDecisionFlows(),
      ])
      const claimItems = Array.isArray(claimsRes) ? claimsRes : claimsRes.results || []
      const flowItems = Array.isArray(flowsRes) ? flowsRes : flowsRes.results || []
      setClaims(claimItems)
      setFlows(flowItems)
      if (!selectedClaimId && claimItems.length) {
        setSelectedClaimId(String(claimItems[0].id))
      }
    } catch (err) {
      console.error('Failed to load decision flows:', err)
      setError(err.message || 'Failed to load decision flows.')
    } finally {
      setLoading(false)
    }
  }, [selectedClaimId])

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const flow =
    flows.find((f) => String(f.claim) === String(selectedClaimId)) || null

  const agents = (flow?.agents || []).map(normalizeAgent)
  const rlRecommendation = normalizeRL(flow?.rl_recommendation || {})
  const finalDecision = normalizeDecision(flow?.final_decision || {}, flow)

  const handleSelectClaim = (id) => {
    setSelectedClaimId(id)
    setSimulationStep(6)
  }

  const handleSimulateFlow = async () => {
    if (!selectedClaimId) return
    setIsSimulating(true)
    setSimulationStep(0)
    try {
      const agentTypes = ['claim_agent', 'policy_agent', 'fraud_agent', 'damage_agent', 'settlement_agent', 'decision_agent']
      for (const [index, agentType] of agentTypes.entries()) {
        await assessmentService.runAgent(agentType, { claim_id: Number(selectedClaimId) })
        setSimulationStep(index + 1)
      }
      const flowsRes = await assessmentService.getDecisionFlows()
      setFlows(Array.isArray(flowsRes) ? flowsRes : flowsRes.results || [])
    } catch (err) {
      console.error('Agent run failed:', err)
      setError(err.response?.data?.error || err.response?.data?.detail || 'Unable to run the claim review workflow.')
      const flowsRes = await assessmentService.getDecisionFlows()
      setFlows(Array.isArray(flowsRes) ? flowsRes : flowsRes.results || [])
    } finally {
      setIsSimulating(false)
    }
  }

  const selectedAgent = agents.find((a) => a.id === 'claim-agent') || agents[0] || null

  const flowNodes = [
    { title: '1. Claim Intake', subtitle: 'Raw Claim & Telemetry Ingestion', icon: Activity },
    { title: '2. ML Predictions', subtitle: 'Cost, Fraud & Total Loss Regressors', icon: Cpu },
    { title: '3. AI Multi-Agents', subtitle: 'Autonomous Specialized Sub-Agents', icon: Bot },
    { title: '4. Decision Engine', subtitle: 'Policy Rules & Threshold Synthesis', icon: GitBranch },
    { title: '5. Settlement Estimate', subtitle: 'Predicted repair cost less policy deductible', icon: Brain },
    { title: '6. Adjuster Review', subtitle: 'Human coverage and settlement decision', icon: CheckCircle2 },
  ]

  const selectedClaim = claims.find((c) => String(c.id) === String(selectedClaimId))

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              Connected Claim Review Workflow
            </span>
          </div>
          <h1 className="page-title">AI Decision Center</h1>
          <p className="page-subtitle">
            Claim data, policy checks, model estimates, and an adjuster review recommendation
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={selectedClaimId}
            onChange={(e) => handleSelectClaim(e.target.value)}
            className="input-field text-sm font-semibold py-2 px-3 border border-gray-300 rounded-lg bg-white"
            aria-label="Select Claim"
          >
            {claims.map((c) => (
              <option key={c.id} value={c.id}>
                {c.claim_number} - {c.customer_name || c.customer_email}
              </option>
            ))}
          </select>
          <Button variant="primary" onClick={handleSimulateFlow} disabled={isSimulating || !selectedClaimId}>
            <Play className={clsx('w-4 h-4 mr-2', isSimulating && 'animate-spin')} />
            {isSimulating ? 'Running Review Workflow...' : 'Run Claim Review'}
          </Button>
          <Button asChild variant="outline"><Link to="/operations">AI Operations</Link></Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {loading && (
        <div className="p-8 text-center text-sm text-gray-400">Loading decision flows...</div>
      )}

      {!loading && !flow && selectedClaimId && (
        <div className="bg-gradient-to-r from-blue-50 via-indigo-50 to-blue-50 border border-blue-200 rounded-xl p-6 text-sm text-blue-900">
          <strong className="font-semibold block mb-1">No Decision Flow Recorded</strong>
          Run the review workflow to save claim, policy, fraud, damage, settlement, and human-review recommendations.
        </div>
      )}

      {flow && (
        <>
          {/* Decision Flow Pipeline Diagram */}
          <Card className="border-2 border-primary/10 overflow-hidden shadow-sm">
            <CardHeader
              title="Complete Decision Flow Architecture"
              subtitle={`Real-time progression for claim ${flow.claim_number || selectedClaim?.claim_number || ''}`}
            />
            <CardContent className="p-6">
              <div className="flex flex-col lg:flex-row items-center justify-between gap-3">
                {flowNodes.map((node, idx) => {
                  const isPassed = simulationStep >= idx + 1
                  const isCurrent = simulationStep === idx + 1

                  return (
                    <div key={idx} className="flex flex-col lg:flex-row items-center gap-3 w-full lg:w-auto">
                      <div
                        className={clsx(
                          'p-4 rounded-xl border flex items-center gap-3 w-full lg:w-48 transition-all duration-300',
                          isPassed
                            ? 'border-emerald-300 bg-emerald-50/70 text-emerald-900 shadow-sm'
                            : isCurrent
                              ? 'border-primary bg-primary/10 text-primary ring-2 ring-primary/20 shadow-md animate-pulse'
                              : 'border-gray-200 bg-gray-50 text-gray-400'
                        )}
                      >
                        <div
                          className={clsx(
                            'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0',
                            isPassed
                              ? 'bg-emerald-600 text-white'
                              : isCurrent
                                ? 'bg-primary text-white'
                                : 'bg-gray-200 text-gray-400'
                          )}
                        >
                          <node.icon className="w-5 h-5" />
                        </div>
                        <div className="min-w-0">
                          <h4 className="font-bold text-xs truncate text-gray-900">{node.title}</h4>
                          <p className="text-[10px] text-gray-500 truncate mt-0.5">{node.subtitle}</p>
                        </div>
                      </div>

                      {idx < flowNodes.length - 1 && (
                        <div className="text-gray-400 flex items-center justify-center">
                          <ArrowDown className="w-5 h-5 lg:hidden" />
                          <div className="hidden lg:block text-gray-300 font-bold text-sm">→</div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {/* Multi-Agent Section */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Multi-Agent Swarm</h2>
                <p className="text-sm text-gray-500">Each agent evaluates a dedicated facet of the insurance claim domain</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
              {agents.length > 0 ? (
                agents.map((agent) => {
                  const isSelected = selectedAgent?.id === agent.id
                  return (
                    <div
                      key={agent.id}
                      className={clsx(
                        'p-4 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between h-32',
                        isSelected
                          ? 'border-primary bg-primary text-white shadow-md ring-2 ring-primary/20 scale-[1.02]'
                          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50 text-gray-900'
                      )}
                    >
                      <div>
                        <Bot className={clsx('w-5 h-5 mb-2', isSelected ? 'text-white' : 'text-primary')} />
                        <h4 className="font-bold text-xs leading-tight">{agent.name}</h4>
                      </div>
                      <div className="text-[11px] opacity-80 mt-2 flex items-center justify-between">
                        <span>{agent.confidence == null ? 'Confidence not calibrated' : `${agent.confidence}% conf`}</span>
                        <span className="font-mono">{agent.processingTime == null ? 'Time n/a' : `${agent.processingTime}s`}</span>
                      </div>
                    </div>
                  )
                })
              ) : (
                <p className="text-sm text-gray-400">No agent executions recorded for this claim.</p>
              )}
            </div>

            {selectedAgent && (
              <Card className="border-t-4 border-t-primary shadow-sm">
                <CardHeader
                  title={`${selectedAgent.name} — Execution Details`}
                  subtitle={`Processing Time: ${selectedAgent.processingTime == null ? 'not recorded' : `${selectedAgent.processingTime}s`} • Confidence: ${selectedAgent.confidence == null ? 'not calibrated' : `${selectedAgent.confidence}%`}`}
                  action={<Badge variant="neutral">Saved output</Badge>}
                />
                <CardContent className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                    <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                      <span className="text-xs font-bold uppercase text-gray-500 tracking-wider block mb-2">Input Telemetry</span>
                      <pre className="font-mono text-xs text-gray-800 bg-white p-3 rounded-lg border border-gray-100 overflow-x-auto">
                        {JSON.stringify(selectedAgent.input, null, 2)}
                      </pre>
                    </div>

                    <div className="p-4 bg-blue-50/60 rounded-xl border border-blue-200">
                      <span className="text-xs font-bold uppercase text-primary tracking-wider block mb-2">Synthesized Output</span>
                      <pre className="font-mono text-xs text-blue-950 bg-white p-3 rounded-lg border border-blue-100 overflow-x-auto">
                        {JSON.stringify(selectedAgent.output, null, 2)}
                      </pre>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Model recommendation and human review */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Optional optimizer status */}
            <Card className="border-2 border-emerald-500/20">
              <CardHeader
                title="Triage Optimizer"
                subtitle="Optional model integration status"
              />
              <CardContent className="p-6 space-y-4">
                <div className="p-4 bg-amber-50 rounded-xl border border-amber-200">
                  <div className="flex items-center gap-2 font-semibold text-amber-900">
                    <Info className="w-4 h-4" />
                    {rlRecommendation.available ? rlRecommendation.action : 'No triage optimizer is configured'}
                  </div>
                  <p className="mt-2 text-sm text-amber-800">
                    {rlRecommendation.explanation || 'The current workflow uses saved claim data and supervised model predictions. It does not run a reinforcement-learning model.'}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Final Decision Engine Card */}
            <Card className="border-2 border-primary/20">
              <CardHeader
                title="Final Decision Engine Output"
                subtitle={`Synthesized output for ${flow.claim_number || selectedClaim?.claim_number || 'claim'}`}
              />
              <CardContent className="p-6 space-y-4">
                <div className="p-4 bg-primary text-white rounded-xl shadow-md">
                    <span className="text-xs font-semibold text-white/80 uppercase">Review Recommendation</span>
                  <div className="text-3xl font-black mt-0.5">{finalDecision.status}</div>
                  <div className="text-sm font-semibold text-emerald-300 mt-1">
                    Estimated payout: {formatCurrency(finalDecision.amount)}
                  </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-xl text-sm">
                  <span className="font-bold text-gray-900 block mb-1">Decision Engine Rationale</span>
                  <p className="text-gray-600 leading-relaxed text-xs">
                    {finalDecision.rationale || 'No rationale recorded.'}
                  </p>
                  <div className="mt-3 pt-3 border-t border-gray-200 text-[11px] text-gray-400 flex items-center justify-between">
                    <span>Decided By: {finalDecision.decidedBy}</span>
                    <span>
                      Timestamp:{' '}
                      {finalDecision.decidedAt ? formatDate(finalDecision.decidedAt) : '—'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {!flow && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-2 border-emerald-500/20">
            <CardHeader title="Triage Optimizer" subtitle="Optional model integration status" />
            <CardContent className="p-6">
              <p className="text-sm text-gray-500">No reinforcement-learning optimizer is configured. The review workflow uses supervised models and policy data.</p>
            </CardContent>
          </Card>
          <Card className="border-2 border-primary/20">
            <CardHeader title="Adjuster Review Recommendation" subtitle="Run the connected review workflow to generate" />
            <CardContent className="p-6">
              <p className="text-sm text-gray-400">No final decision on record for the selected claim.</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

export default AIDecisionCenter
