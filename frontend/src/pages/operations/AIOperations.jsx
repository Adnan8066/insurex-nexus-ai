import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Brain,
  Cpu,
  Activity,
  Sparkles,
  UserCheck,
  Wrench,
  Clock,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  BarChart3,
  RefreshCw,
  Info,
} from 'lucide-react'
import {
  assessmentService,
  claimService,
  investigationService,
  repairService,
} from '../../services'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ChartCard, BarChart } from '../../components/charts/ChartComponents'

export function AIOperations() {
  const [models, setModels] = useState([])
  const [agentOutputs, setAgentOutputs] = useState([])
  const [assessments, setAssessments] = useState([])
  const [claims, setClaims] = useState([])
  const [fraudAlerts, setFraudAlerts] = useState([])
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const results = await Promise.allSettled([
        assessmentService.getModelStatus(),
        assessmentService.getAgentOutputs(),
        assessmentService.getAssessments(),
        claimService.getClaims(),
        investigationService.getFraudAlerts(),
        repairService.getJobs(),
      ])
      const unwrap = (r) =>
        r.status === 'fulfilled'
          ? Array.isArray(r.value) ? r.value : r.value.results || []
          : []
      const status = results[0].status === 'fulfilled' ? results[0].value : null
      const artifactByModel = {
        insurance_fraud: 'fraud_risk_model',
        repair_cost: 'repair_cost_model',
        total_loss: 'total_loss_model',
        fraud_oracle_fraud: 'fraud_oracle_model',
      }
      const reportMetrics = status?.metrics || []
      setModels(Object.entries(artifactByModel)
        .filter(([name, artifactKey]) => status?.models?.[artifactKey] || reportMetrics.some((metric) => metric.model === name))
        .map(([name, artifactKey]) => {
          const metric = reportMetrics.find((item) => item.model === name) || {}
          return {
            ...metric,
            id: name,
            model_type: name,
            f1_score: metric.f1 ?? metric.f1_score,
            auc: metric.roc_auc ?? metric.auc,
            version: status?.trained_at ? status.trained_at.slice(0, 10) : 'artifact available',
            is_active: Boolean(status?.models?.[artifactKey]),
          }
        }))
      setAgentOutputs(unwrap(results[1]))
      setAssessments(unwrap(results[2]))
      setClaims(unwrap(results[3]))
      setFraudAlerts(unwrap(results[4]))
      setJobs(unwrap(results[5]))
    } catch (err) {
      console.error('Failed to load AI operations data:', err)
      setError(err.message || 'Failed to load AI operations data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const claimsMap = {}
  claims.forEach((c) => {
    claimsMap[String(c.id)] = c
  })

  // Module 1: Claim Priority Optimization (assessments vs current claim priority)
  const priorityOptimizations = assessments
    .filter((a) => {
      const claim = claimsMap[String(a.claim)]
      return claim && claim.priority && a.claim_priority && claim.priority !== a.claim_priority
    })
    .slice(0, 6)
    .map((a) => {
      const claim = claimsMap[String(a.claim)]
      return {
        claimId: claim.id,
        claimNumber: claim.claim_number,
        currentPriority: claim.priority,
        recommendedPriority: a.claim_priority,
        reason: a.ai_recommendation || `AI assessment recommends ${a.claim_priority} priority based on risk scoring.`,
      score: a.confidence == null ? null : Math.round(Number(a.confidence) * 100),
      }
    })

  // Module 2: Investigator Assignment (fraud alerts with assigned investigators)
  const investigatorAssignments = fraudAlerts
    .filter((f) => f.assigned_investigator_name)
    .slice(0, 6)
    .map((f) => ({
      claimId: f.claim,
      claimNumber: f.claim_number,
      matchScore: Math.round(Number(f.risk_score) || 0),
      recommendedInvestigator: f.assigned_investigator_name,
      reason: f.ai_recommendation || 'Matched based on fraud risk profile and SIU specialty.',
    }))

  // Module 3: Repair Shop Recommendation (repair jobs)
  const shopRecommendations = jobs
    .filter((j) => j.repair_shop_name)
    .slice(0, 6)
    .map((j) => ({
      claimId: j.claim,
      claimNumber: j.claim_number,
      matchScore: j.quality_score ? Math.round(Number(j.quality_score)) : 85,
      recommendedShop: j.repair_shop_name,
      reason: `Assigned for ${j.repair_stage || 'repair'} — estimated ${j.estimated_cost ? `$${Number(j.estimated_cost).toLocaleString()}` : 'N/A'}.`,
    }))

  // Module 4: Processing Time Estimates (assessments with repair_time_estimate_days)
  const processingEstimates = assessments
    .filter((a) => a.repair_time_estimate_days != null)
    .slice(0, 6)
    .map((a) => ({
      claimId: a.claim,
      claimNumber: a.claim_number,
      estimatedDays: Math.round(Number(a.repair_time_estimate_days) || 0),
      factors: (a.risk_factors || []).slice(0, 3).map((f) => (typeof f === 'string' ? f : f.factor || f.name || 'factor')),
      confidence: a.confidence == null ? null : Math.round(Number(a.confidence) * 100),
    }))

  // Held-out evaluation metrics from the backend training report.
  const modelChartData = {
    labels: models.map((m) => `${m.model_type || 'model'} v${m.version || '?'}`),
    datasets: [
      {
        label: 'Accuracy',
        data: models.map((m) => m.accuracy == null ? null : Math.round(Number(m.accuracy) * 100)),
        backgroundColor: '#1e3a5f',
        borderRadius: 4,
      },
      {
        label: 'F1 Score',
        data: models.map((m) => m.f1_score == null ? null : Math.round(Number(m.f1_score) * 100)),
        backgroundColor: '#00c896',
        borderRadius: 4,
      },
    ],
  }

  const activeModels = models.filter((m) => m.is_active).length
  const completedAgentRuns = agentOutputs.filter((a) => a.status === 'completed').length

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <Brain className="w-3.5 h-3.5 text-emerald-600" />
              Live model and workflow data
            </span>
          </div>
          <h1 className="page-title">AI Operations Console</h1>
          <p className="page-subtitle">
            Current model availability, assessments, fraud reviews, and repair workflow activity
          </p>
        </div>

        <div className="flex gap-2">
          <Button variant="primary" onClick={loadData} disabled={loading}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh Data
          </Button>
          <Link to="/ai-decision">
            <Button variant="outline">Decision Center</Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="bg-gradient-to-r from-red-50 to-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3.5 shadow-sm">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-red-900">{error}</div>
        </div>
      )}

      {loading && (
        <div className="p-8 text-center text-sm text-gray-400">Loading AI operations...</div>
      )}

      {/* Model Registry Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-primary text-white p-6 rounded-2xl shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-white/80 uppercase tracking-wider block">Registered Models</span>
            <div className="text-4xl font-black mt-2">{models.length}</div>
          </div>
          <div className="text-xs text-white/70 mt-4 flex items-center justify-between">
            <span>Production Registry</span>
            <span className="bg-white/20 px-2 py-0.5 rounded">{activeModels} Active</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Agent Executions</span>
            <div className="text-3xl font-black text-gray-900 mt-1">{agentOutputs.length} runs</div>
            <span className="text-xs text-emerald-600 font-medium">{completedAgentRuns} completed</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Claim Assessments</span>
            <div className="text-3xl font-black text-gray-900 mt-1">{assessments.length}</div>
            <span className="text-xs text-gray-500">Inference records</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <Cpu className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Fraud Alerts Triage</span>
            <div className="text-3xl font-black text-amber-600 mt-1">{fraudAlerts.length}</div>
            <span className="text-xs text-gray-500">SIU queue</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Grid of the 4 Key Operations Modules */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Module 1: Claim Priority Optimization */}
        <Card>
          <CardHeader
            title="1. Claim Priority Optimization"
            subtitle="Automated priority escalation based on fraud indicators and severity"
          />
          <CardContent className="p-6">
            <div className="space-y-3">
              {priorityOptimizations.length > 0 ? (
                priorityOptimizations.map((cp, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 space-y-2">
                    <div className="flex items-center justify-between">
                      <Link to={`/claims/${cp.claimId}`} className="font-mono font-bold text-primary hover:underline text-sm">
                        {cp.claimNumber}
                      </Link>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">Current: {cp.currentPriority}</span>
                        <span className="text-gray-400">→</span>
                        <Badge variant={cp.recommendedPriority === 'critical' || cp.recommendedPriority === 'high' ? 'danger' : cp.recommendedPriority === 'medium' ? 'warning' : 'primary'}>
                          {cp.recommendedPriority}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-xs text-gray-600">{cp.reason}</p>
                    <div className="flex justify-between items-center text-[11px] text-gray-400 pt-1 border-t border-gray-100">
                      <span>Optimization Match Score:</span>
                      <strong className="text-gray-800">{cp.score}/100</strong>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-400">No priority escalations recommended at this time.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Module 2: Investigator Assignment */}
        <Card>
          <CardHeader
            title="2. Investigator Assignment"
            subtitle="Skillset & specialty mapping matching case risk to SIU officers"
          />
          <CardContent className="p-6">
            <div className="space-y-3">
              {investigatorAssignments.length > 0 ? (
                investigatorAssignments.map((ia, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 space-y-2">
                    <div className="flex items-center justify-between">
                      <Link to={`/claims/${ia.claimId}`} className="font-mono font-bold text-primary hover:underline text-sm">
                        {ia.claimNumber}
                      </Link>
                      <span className="font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full text-xs">
                        {ia.matchScore}% Match
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                      <UserCheck className="w-4 h-4 text-primary" />
                      Recommended: {ia.recommendedInvestigator}
                    </div>
                    <p className="text-xs text-gray-600">{ia.reason}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-400">No investigator assignments on record.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Module 3: Repair Shop Recommendation */}
        <Card>
          <CardHeader
            title="3. Repair Shop Recommendation"
            subtitle="OEM certified capacity and historical turnaround optimization"
          />
          <CardContent className="p-6">
            <div className="space-y-3">
              {shopRecommendations.length > 0 ? (
                shopRecommendations.map((rs, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 space-y-2">
                    <div className="flex items-center justify-between">
                      <Link to={`/claims/${rs.claimId}`} className="font-mono font-bold text-primary hover:underline text-sm">
                        {rs.claimNumber}
                      </Link>
                      <span className="font-semibold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full text-xs">
                        {rs.matchScore}% Optimal Fit
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                      <Wrench className="w-4 h-4 text-primary" />
                      Recommended: {rs.recommendedShop}
                    </div>
                    <p className="text-xs text-gray-600">{rs.reason}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-400">No repair shop assignments on record.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Module 4: Estimated Processing Time */}
        <Card>
          <CardHeader
            title="4. Estimated Processing Time Predictions"
            subtitle="Predictive duration modeled from document intake and shop load"
          />
          <CardContent className="p-6">
            <div className="space-y-3">
              {processingEstimates.length > 0 ? (
                processingEstimates.map((pe, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 space-y-2">
                    <div className="flex items-center justify-between">
                      <Link to={`/claims/${pe.claimId}`} className="font-mono font-bold text-primary hover:underline text-sm">
                        {pe.claimNumber}
                      </Link>
                      <div className="flex items-center gap-1.5 font-bold text-gray-900 text-sm">
                        <Clock className="w-4 h-4 text-primary" />
                        {pe.estimatedDays} Business Days
                      </div>
                    </div>
                    <div className="flex gap-1.5 flex-wrap">
                      {pe.factors.length > 0 ? (
                        pe.factors.map((f, i) => (
                          <span key={i} className="text-[10px] bg-white border border-gray-200 px-2 py-0.5 rounded text-gray-600">
                            {f}
                          </span>
                        ))
                      ) : (
                        <span className="text-[10px] text-gray-400">No factors recorded</span>
                      )}
                    </div>
                    <div className="text-[11px] text-gray-500 pt-1 border-t border-gray-100 flex justify-between">
                      <span>Model Confidence:</span>
                      <strong className="text-gray-800">{pe.confidence == null ? 'Not calibrated' : `${pe.confidence}%`}</strong>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-400">No processing time estimates on record.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Model Performance Registry */}
      <Card>
        <CardHeader
          title="Model Performance Registry"
          subtitle="Model artifacts and held-out evaluation metrics from the training report"
        />
        <CardContent className="p-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-gray-500 border-b border-gray-200">
                  <th className="pb-2 pr-4">Model</th>
                  <th className="pb-2 pr-4">Version</th>
                  <th className="pb-2 pr-4">Accuracy</th>
                  <th className="pb-2 pr-4">Precision</th>
                  <th className="pb-2 pr-4">Recall</th>
                  <th className="pb-2 pr-4">F1 Score</th>
                  <th className="pb-2 pr-4">AUC</th>
                  <th className="pb-2 pr-4">MAE</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {models.length > 0 ? (
                  models.map((m) => (
                    <tr key={m.id} className="border-b border-gray-100">
                      <td className="py-2.5 pr-4 font-semibold text-gray-900">{m.model_type}</td>
                      <td className="py-2.5 pr-4 font-mono text-gray-600">{m.version}</td>
                      <td className="py-2.5 pr-4">{m.accuracy == null ? '—' : `${Math.round(Number(m.accuracy) * 100)}%`}</td>
                      <td className="py-2.5 pr-4">{m.precision == null ? '—' : `${Math.round(Number(m.precision) * 100)}%`}</td>
                      <td className="py-2.5 pr-4">{m.recall == null ? '—' : `${Math.round(Number(m.recall) * 100)}%`}</td>
                      <td className="py-2.5 pr-4">{m.f1_score == null ? '—' : `${Math.round(Number(m.f1_score) * 100)}%`}</td>
                      <td className="py-2.5 pr-4">{m.auc != null ? Math.round(Number(m.auc) * 100) / 100 : '—'}</td>
                      <td className="py-2.5 pr-4">{m.mae != null ? Number(m.mae).toFixed(2) : '—'}</td>
                      <td className="py-2.5">
                        <Badge variant={m.is_active ? 'success' : 'neutral'}>
                          {m.is_active ? 'Active' : 'Archived'}
                        </Badge>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="9" className="py-6 text-center text-gray-400">
                      No training report metrics are available. Run the model training command to generate them.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Model Accuracy Comparison */}
      {models.length > 0 && (
        <ChartCard
          title="Model Accuracy Comparison"
          subtitle="Validation accuracy and F1 score across registered models"
        >
          <BarChart data={modelChartData} height={260} />
        </ChartCard>
      )}
    </div>
  )
}

export default AIOperations
