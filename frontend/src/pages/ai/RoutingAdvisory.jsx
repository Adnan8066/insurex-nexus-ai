import { useEffect, useState } from 'react'
import { AlertTriangle, Brain, LoaderCircle, Sparkles, Users } from 'lucide-react'
import { assessmentService } from '../../services'
import { formatApiError } from '../../services/api'

const initialClaim = {
  complexity_score: 0.7,
  severity_score: 0.6,
  processing_difficulty: 0.5,
}

const initialAgents = [
  { id: 'agent-1', queue_length: 2, workload: 12, skill_tier: 4, available: true },
  { id: 'agent-2', queue_length: 1, workload: 8, skill_tier: 3, available: true },
  { id: 'agent-3', queue_length: 4, workload: 18, skill_tier: 5, available: true },
]

const claimFields = [
  ['complexity_score', 'Complexity score'],
  ['severity_score', 'Severity score'],
  ['processing_difficulty', 'Processing difficulty'],
]

export function RoutingAdvisory() {
  const [claim, setClaim] = useState(initialClaim)
  const [agents, setAgents] = useState(initialAgents)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [liveAgents, setLiveAgents] = useState([])
  const [liveClaims, setLiveClaims] = useState([])
  const [selectedLiveAgentIds, setSelectedLiveAgentIds] = useState([])
  const [agentSource, setAgentSource] = useState('sample')
  const [selectedClaimId, setSelectedClaimId] = useState('')
  const [reviewNotes, setReviewNotes] = useState('')
  const [reviewSaved, setReviewSaved] = useState(false)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [modelStatus, setModelStatus] = useState(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      assessmentService.getRoutingAgents(),
      assessmentService.getRoutingClaims(),
      assessmentService.getRoutingModelStatus(),
    ]).then(([roster, claims, status]) => {
      if (cancelled) return
      setLiveAgents(roster.agents || [])
      setSelectedLiveAgentIds((roster.agents || []).length <= 5 ? (roster.agents || []).map((agent) => agent.id) : [])
      setLiveClaims(Array.isArray(claims) ? claims : [])
      setModelStatus(status)
    }).catch((requestError) => {
      if (!cancelled) {
        setError(formatApiError(requestError, 'Live routing data could not be loaded. You can still try the clearly marked sample values.'))
      }
    })
    return () => { cancelled = true }
  }, [])

  const selectedClaim = liveClaims.find((item) => String(item.id) === String(selectedClaimId))
  const agentDisplayName = (id) => agents.find((agent) => String(agent.id) === String(id))?.name || id
  const activeClaimData = selectedClaim?.claim_data || Object.fromEntries(
    Object.entries(claim).map(([key, value]) => [key, Number(value)]),
  )

  const useLiveRoster = () => {
    const selectedAgents = liveAgents.filter((agent) => selectedLiveAgentIds.includes(agent.id))
    if (selectedAgents.length < 3 || selectedAgents.length > 5) {
      setError(`Select between 3 and 5 of the ${liveAgents.length} configured agents for this advisory comparison.`)
      return
    }
    setError('')
    setAgents(selectedAgents)
    setAgentSource('live')
  }

  const useSampleRoster = () => {
    setError('')
    setAgents(initialAgents)
    setAgentSource('sample')
  }

  const updateAgent = (index, key, value) => {
    setAgents((current) => current.map((agent, i) => (
      i === index ? { ...agent, [key]: value } : agent
    )))
  }

  const getRecommendations = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    setReviewSaved(false)
    try {
      const advice = await assessmentService.getRoutingRecommendation(
        activeClaimData,
        agents.map((agent) => ({
          ...agent,
          queue_length: Number(agent.queue_length),
          workload: Number(agent.workload),
          skill_tier: Number(agent.skill_tier),
        })),
        selectedClaim?.id ?? null,
      )
      setResult(advice)
    } catch (requestError) {
      setError(formatApiError(requestError, 'Could not get routing advice. Please try again in a moment.'))
    } finally {
      setLoading(false)
    }
  }

  const saveHumanReview = async (decision) => {
    if (!result?.recommendation_id) return
    setReviewLoading(true)
    setError('')
    try {
      await assessmentService.reviewRoutingRecommendation({
        recommendation_id: result.recommendation_id,
        claim_id: result.claim_id,
        decision,
        notes: reviewNotes,
        claim_data: activeClaimData,
        active_agents_status: agents,
        recommendation: result,
      })
      setReviewSaved(true)
    } catch (requestError) {
      setError(formatApiError(requestError, 'Could not save the human review. Please try again.'))
    } finally {
      setReviewLoading(false)
    }
  }

  return (
    <main className="page max-w-7xl mx-auto space-y-6">
      <header className="page-header">
        <div className="flex items-center gap-2 mb-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
            <Brain className="h-4 w-4" /> RL routing simulator
          </span>
        </div>
        <h1 className="page-title">Suggest Adjuster</h1>
        <p className="page-subtitle">See which agent is best placed to handle a claim, based on skills and current workload.</p>
      </header>

      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
        <div className="flex gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <p><strong>Advisory only.</strong> This tool never assigns a claim. Queue length is counted from active assigned claims; workload and wait are simulator estimates, not measured time. Staff must review every recommendation.</p>
        </div>
      </div>

      {modelStatus && !modelStatus.ready && <div role="status" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        RL model is not ready on this backend: {modelStatus.detail || 'Required inference packages are missing.'}
      </div>}
      {modelStatus?.ready && modelStatus.dataset_pretraining && <div role="status" className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
        Routing model warm-started from {modelStatus.dataset_pretraining.transitions?.toLocaleString() || 'synthetic'} transition records using behavior cloning, then trained in the simulator. The agent values below are current advisory inputs; they are not identities or outcomes from the training dataset.
      </div>}
      {modelStatus?.ready && !modelStatus.qualified_for_advisory_pilot && <div role="status" className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
        This model has not passed the multi-seed comparison gate against the least-workload heuristic. Treat results as experimental advice only.
      </div>}

      <form onSubmit={getRecommendations} className="space-y-6">
        <section className="card p-5 md:p-6">
          <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="card-title">Claim details</h2>
              <p className="mt-1 text-sm text-gray-500">Select an unassigned open claim to derive normalized simulator features, or use sample inputs.</p>
            </div>
            {liveClaims.length > 0 && <select className="input-field sm:max-w-xs" aria-label="Choose open claim" value={selectedClaimId} onChange={(event) => setSelectedClaimId(event.target.value)}>
              <option value="">Use manually entered sample features</option>
              {liveClaims.map((item) => <option key={item.id} value={item.id}>{item.claim_number}</option>)}
            </select>}
          </div>
          {selectedClaim ? <p className="mb-3 rounded-md bg-blue-50 p-3 text-sm text-blue-800">Using claim {selectedClaim.claim_number}. Claim attributes are converted to normalized simulator inputs.</p> : <div className="mb-4 grid gap-4 sm:grid-cols-3">
            {claimFields.map(([key, label]) => (
              <label key={key} className="block text-sm font-medium text-gray-700">
                {label} <span className="font-normal text-gray-500">(0–1)</span>
                <input
                  className="input-field mt-1"
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  required
                  value={claim[key]}
                  onChange={(event) => setClaim((current) => ({ ...current, [key]: event.target.value }))}
                />
              </label>
            ))}
          </div>}
        </section>

        <section className="card p-5 md:p-6">
          <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="card-title mb-1">Agent status</h2>
              <p className="text-sm text-gray-500">{agentSource === 'live' ? 'Application roster loaded; queue counts come from active claims. Workload is an estimate.' : 'Using editable sample agent inputs for this demo recommendation.'}</p>
            </div>
            {agentSource === 'live' && <button className="btn btn-secondary" type="button" onClick={useSampleRoster}>Use sample data</button>}
          </div>
          {liveAgents.length > 0 && <div className="mb-4 rounded-lg border border-gray-200 p-3">
            <p className="mb-2 text-sm text-gray-600">Choose 3–5 staff candidates. The model currently scores at most five agents per comparison.</p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {liveAgents.map((agent) => <label key={agent.id} className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={selectedLiveAgentIds.includes(agent.id)} onChange={(event) => setSelectedLiveAgentIds((current) => event.target.checked ? [...current, agent.id] : current.filter((id) => id !== agent.id))} />
                {agent.name}{agent.is_demo && <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-800">Demo</span>} · queue {agent.queue_length} · tier {agent.skill_tier}{agent.available ? '' : ' · unavailable'}
              </label>)}
            </div>
            <button className="btn btn-secondary mt-3" type="button" onClick={useLiveRoster} disabled={selectedLiveAgentIds.length < 3 || selectedLiveAgentIds.length > 5}>
              <Users className="h-4 w-4" /><span>Use selected staff ({selectedLiveAgentIds.length})</span>
            </button>
          </div>}
          <div className="grid gap-4 lg:grid-cols-3">
            {agents.map((agent, index) => (
              <div key={agent.id} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <p className="mb-3 font-semibold text-gray-800">{agent.name || agent.id} {agent.is_demo && <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-800">Demo</span>} {agent.role && <span className="text-xs font-normal capitalize text-gray-500">({agent.role})</span>}</p>
                <div className="grid grid-cols-2 gap-3">
                  <label className="text-sm font-medium text-gray-700">Queue length
                    <input className="input-field mt-1" type="number" min="0" step="1" required value={agent.queue_length} onChange={(event) => updateAgent(index, 'queue_length', event.target.value)} />
                  </label>
                  <label className="text-sm font-medium text-gray-700">Workload
                    <input className="input-field mt-1" type="number" min="0" step="0.1" required value={agent.workload} onChange={(event) => updateAgent(index, 'workload', event.target.value)} />
                  </label>
                  <label className="text-sm font-medium text-gray-700">Skill tier (1–5)
                    <input className="input-field mt-1" type="number" min="1" max="5" step="1" required value={agent.skill_tier} onChange={(event) => updateAgent(index, 'skill_tier', event.target.value)} />
                  </label>
                  <label className="flex items-center gap-2 self-end pb-3 text-sm font-medium text-gray-700">
                    <input type="checkbox" checked={agent.available} onChange={(event) => updateAgent(index, 'available', event.target.checked)} /> Available
                  </label>
                </div>
              </div>
            ))}
          </div>
          <button className="btn btn-primary mt-5" type="submit" disabled={loading}>
            {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            <span>{loading ? 'Getting advice…' : 'Get routing advice'}</span>
          </button>
        </section>
      </form>

      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      {result && (
        <section className="card p-5 md:p-6" aria-live="polite">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Suggested for human review</p>
              <h2 className="mt-1 text-2xl font-bold text-gray-900">{result.recommended_agent_id == null ? 'No available agent' : agentDisplayName(result.recommended_agent_id)}</h2>
              <p className="mt-2 text-sm text-gray-600">{result.workload_impact_summary}</p>
            </div>
            {result.confidence && <div className="rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-800">Relative model preference: <strong>{result.confidence.percentage}%</strong><br /><span className="text-xs">Not a calibrated success probability</span></div>}
          </div>
          {result.predicted_wait_time != null && <p className="mt-4 text-sm text-gray-700">Estimated simulated wait: <strong>{result.predicted_wait_time}</strong> time units</p>}
          <p className="mt-2 text-xs text-gray-500">{result.wait_time_basis}</p>
          {result.ranked_options?.length > 0 && (
            <div className="mt-5 overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead><tr className="text-xs uppercase text-gray-500"><th className="px-3 py-2">Rank</th><th className="px-3 py-2">Agent</th><th className="px-3 py-2">Relative match</th><th className="px-3 py-2">Wait</th><th className="px-3 py-2">Skill</th><th className="px-3 py-2">Workload after</th></tr></thead>
                <tbody className="divide-y divide-gray-200">
                  {result.ranked_options.map((option) => (
                    <tr key={option.agent_id} className="text-gray-700">
                      <td className="px-3 py-3">{option.rank}</td><td className="px-3 py-3 font-semibold">{agentDisplayName(option.agent_id)}</td><td className="px-3 py-3">{option.match_percentage}%</td><td className="px-3 py-3">{option.predicted_wait_time}</td><td className="px-3 py-3">{option.skill_match ? 'Match' : 'Review tier'}</td><td className="px-3 py-3">{option.estimated_workload_after_assignment}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-6 border-t border-gray-200 pt-5">
            {reviewSaved ? <p className="rounded-md bg-emerald-50 p-3 text-sm font-medium text-emerald-800">Your feedback was saved. No claim assignment was changed.</p> : <>
              <label className="block text-sm font-medium text-gray-700" htmlFor="routing-review-notes">Optional review note</label>
              <textarea id="routing-review-notes" className="input-field mt-1 min-h-20" maxLength={2000} value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder="What should the team know about this recommendation?" />
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="btn btn-primary" type="button" disabled={reviewLoading} onClick={() => saveHumanReview('accepted')}>{reviewLoading ? 'Saving…' : 'Useful for review'}</button>
                <button className="btn btn-secondary" type="button" disabled={reviewLoading} onClick={() => saveHumanReview('rejected')}>Not useful</button>
              </div>
              <p className="mt-2 text-xs text-gray-500">Feedback is logged for evaluation only; “useful” does not assign a claim.</p>
            </>}
          </div>
        </section>
      )}
    </main>
  )
}

export default RoutingAdvisory
