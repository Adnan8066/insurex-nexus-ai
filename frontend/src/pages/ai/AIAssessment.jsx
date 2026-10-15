import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import {
  DollarSign,
  AlertTriangle,
  TrendingDown,
  Cpu,
  Sparkles,
  Info,
  RefreshCw,
  AlertCircle,
  Play,
} from 'lucide-react'
import { clsx } from 'clsx'
import { assessmentService, claimService } from '../../services'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { ChartCard, BarChart, DoughnutChart } from '../../components/charts/ChartComponents'
import { formatCurrency, formatDate } from '../../utils/helpers'

const PRIORITY_LABELS = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

const normalizeFactors = (factors) => {
  if (!Array.isArray(factors)) return []
  return factors.map((f) => {
    if (typeof f === 'string') {
      return { factor: f, description: '', weight: 0, impact: 'neutral' }
    }
    if (f && typeof f === 'object') {
      return {
        factor: f.factor || f.name || f.title || 'Contributing factor',
        description: f.description || '',
        weight: Number(f.weight || f.importance || 0),
        impact: f.impact || 'neutral',
      }
    }
    return { factor: String(f), description: '', weight: 0, impact: 'neutral' }
  })
}

export function AIAssessment() {
  const [searchParams, setSearchParams] = useSearchParams()
  const claimParam = searchParams.get('claim') || ''

  const [claims, setClaims] = useState([])
  const [assessments, setAssessments] = useState([])
  const [selectedClaimId, setSelectedClaimId] = useState(claimParam)
  const [assessment, setAssessment] = useState(null)
  const [claim, setClaim] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [claimsRes, assessmentsRes] = await Promise.all([
        claimService.getClaims(),
        assessmentService.getAssessments(),
      ])
      const claimItems = Array.isArray(claimsRes) ? claimsRes : claimsRes.results || []
      const assessmentItems = Array.isArray(assessmentsRes)
        ? assessmentsRes
        : assessmentsRes.results || []
      setClaims(claimItems)
      setAssessments(assessmentItems)
      if (!selectedClaimId && claimItems.length) {
        setSelectedClaimId(String(claimItems[0].id))
      }
    } catch (err) {
      console.error('Failed to load AI assessment data:', err)
      setError(err.message || 'Failed to load assessments. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [selectedClaimId])

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const targetClaim = claims.find((c) => String(c.id) === String(selectedClaimId)) || claims[0] || null
    setClaim(targetClaim || null)
    const targetId = targetClaim ? String(targetClaim.id) : String(selectedClaimId)
    const match = assessments.find((a) => String(a.claim) === targetId) || null
    setAssessment(match)
  }, [selectedClaimId, claims, assessments])

  const handleSelectClaim = (id) => {
    setSelectedClaimId(id)
    setSearchParams({ claim: id })
  }

  const triggerReAnalysis = async () => {
    if (!selectedClaimId) return
    setAnalyzing(true)
    try {
      await assessmentService.assessClaim({ claim_id: Number(selectedClaimId) })
      const assessmentsRes = await assessmentService.getAssessments()
      setAssessments(Array.isArray(assessmentsRes) ? assessmentsRes : assessmentsRes.results || [])
    } catch (err) {
      console.error('Failed to run AI assessment:', err)
      setError(err.message || 'Failed to run AI assessment.')
    } finally {
      setAnalyzing(false)
    }
  }

  const predictedRepairCost = Number(assessment?.predicted_repair_cost) || 0
  const fraudRiskScore = Number(assessment?.fraud_risk_score) || 0
  const totalLossProbability = Number(assessment?.total_loss_probability) || 0
  const claimAmount = Number(claim?.claim_amount) || 0
  const costBreakdown = assessment?.cost_breakdown || {}
  const parts = Number(costBreakdown.parts || costBreakdown.parts_total || 0)
  const labor = Number(costBreakdown.labor || costBreakdown.labor_total || 0)
  const paint = Number(costBreakdown.paint || costBreakdown.paint_total || 0)
  const other = Number(costBreakdown.other || costBreakdown.other_total || 0)
  const factors = normalizeFactors(assessment?.contributing_factors)

  const costData = {
    labels: ['Parts', 'Labor', 'Paint', 'Other'],
    datasets: [
      {
        data: [parts, labor, paint, other],
        backgroundColor: ['#1e3a5f', '#007bff', '#00c896', '#94a3b8'],
        borderWidth: 0,
      },
    ],
  }

  const comparisonData = {
    labels: ['Customer Estimate', 'AI Predicted Cost'],
    datasets: [
      {
        label: 'Amount ($)',
        data: [claimAmount, predictedRepairCost],
        backgroundColor: ['#94a3b8', '#1e3a5f'],
        borderRadius: 6,
      },
    ],
  }

  const costVariance =
    claimAmount > 0 && predictedRepairCost > 0
      ? Math.abs(Math.round(((predictedRepairCost - claimAmount) / claimAmount) * 100))
      : 0

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">
              <Sparkles className="w-3.5 h-3.5 text-purple-600" />
              Machine Learning Inference Engine
            </span>
          </div>
          <h1 className="page-title">AI Claim Assessment Dashboard</h1>
          <p className="page-subtitle">
            Automated deep damage analysis, cost prediction, fraud detection, and triage recommendation
          </p>
        </div>

        {/* Claim Selector & Action */}
        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={selectedClaimId}
            onChange={(e) => handleSelectClaim(e.target.value)}
            className="input-field text-sm font-semibold py-2 px-3 border border-gray-300 rounded-lg bg-white"
            aria-label="Select Claim to Analyze"
          >
            {claims.map((c) => (
              <option key={c.id} value={c.id}>
                {c.claim_number} - {c.customer_name || c.customer_email} ({c.incident_type})
              </option>
            ))}
          </select>

          <Button variant="primary" onClick={triggerReAnalysis} disabled={analyzing || !selectedClaimId}>
            <RefreshCw className={clsx('w-4 h-4 mr-2', analyzing && 'animate-spin')} />
            {analyzing ? 'Running Inference...' : 'Re-run Inference'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {loading && (
        <div className="p-8 text-center text-sm text-gray-400">Loading AI assessments...</div>
      )}

      {!loading && !assessment && selectedClaimId && (
        <div className="bg-gradient-to-r from-blue-50 via-indigo-50 to-blue-50 border border-blue-200 rounded-xl p-6 flex items-start gap-3.5 shadow-sm">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900">
            <strong className="font-semibold block mb-1">No AI Assessment on Record</strong>
            This claim has not been processed by the inference engine yet. Run inference to generate
            cost prediction, fraud scoring, and triage recommendation.
            <div className="mt-3">
              <Button variant="primary" size="sm" onClick={triggerReAnalysis} disabled={analyzing}>
                <Play className="w-3.5 h-3.5 mr-1" />
                Run AI Assessment
              </Button>
            </div>
          </div>
        </div>
      )}

      {assessment && (
        <>
          {/* Primary 4 AI KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Predicted Repair Cost */}
            <Card className="border-t-4 border-t-primary shadow-sm">
              <CardContent className="p-6">
                <div className="flex items-center justify-between text-gray-500 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider">Predicted Repair Cost</span>
                  <DollarSign className="w-4 h-4 text-primary" />
                </div>
                <div className="text-3xl font-extrabold text-gray-900">
                  {formatCurrency(predictedRepairCost)}
                </div>
                <div className="mt-2 flex items-center text-xs text-gray-600">
                  <span className="text-emerald-600 font-semibold mr-1">
                    {predictedRepairCost < claimAmount ? '↓' : '↑'} {costVariance}%
                  </span>
                  <span>vs customer filed amount</span>
                </div>
              </CardContent>
            </Card>

            {/* 2. Fraud Risk Score */}
            <Card className="border-t-4 border-t-amber-500 shadow-sm">
              <CardContent className="p-6">
                <div className="flex items-center justify-between text-gray-500 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider">Fraud Risk Score</span>
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-gray-900">
                    {Math.round(fraudRiskScore)}%
                  </span>
                  <Badge
                    variant={
                      fraudRiskScore > 60
                        ? 'danger'
                        : fraudRiskScore > 30
                          ? 'warning'
                          : 'success'
                    }
                  >
                    {fraudRiskScore > 60
                      ? 'High Risk'
                      : fraudRiskScore > 30
                        ? 'Moderate Risk'
                        : 'Low Risk'}
                  </Badge>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-3 overflow-hidden">
                  <div
                    className={clsx(
                      'h-2 rounded-full transition-all duration-500',
                      fraudRiskScore > 60 ? 'bg-red-500' : fraudRiskScore > 30 ? 'bg-amber-500' : 'bg-emerald-500'
                    )}
                    style={{ width: `${Math.min(fraudRiskScore, 100)}%` }}
                  />
                </div>
              </CardContent>
            </Card>

            {/* 3. Total Loss Probability */}
            <Card className="border-t-4 border-t-purple-600 shadow-sm">
              <CardContent className="p-6">
                <div className="flex items-center justify-between text-gray-500 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider">Total Loss Probability</span>
                  <TrendingDown className="w-4 h-4 text-purple-600" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-gray-900">
                    {Math.round(totalLossProbability)}%
                  </span>
                  <span className="text-xs text-gray-500">
                    {totalLossProbability > 50 ? 'Constructive Loss' : 'Repairable'}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-3 overflow-hidden">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(totalLossProbability, 100)}%` }}
                  />
                </div>
              </CardContent>
            </Card>

            {/* 4. Claim Priority */}
            <Card className="border-t-4 border-t-blue-600 shadow-sm">
              <CardContent className="p-6">
                <div className="flex items-center justify-between text-gray-500 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider">Triage Priority</span>
                  <Cpu className="w-4 h-4 text-blue-600" />
                </div>
                <div className="text-3xl font-extrabold text-gray-900">
                  {PRIORITY_LABELS[assessment.claim_priority] || assessment.claim_priority || 'Medium'}
                </div>
                <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
                  <span>Model Confidence:</span>
                  <strong className="text-gray-800">{Math.round(Number(assessment.confidence || 0))}%</strong>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* AI Recommendation Spotlight Card */}
          <div className="bg-white border-2 border-primary/20 rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-primary text-white flex items-center justify-center flex-shrink-0 shadow-md">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-primary">
                    AI Recommendation & Action Plan
                  </span>
                  <h3 className="text-xl font-bold text-gray-900 mt-0.5">
                    {assessment.ai_recommendation || 'Approve with standard processing'}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Model version:{' '}
                    <span className="font-mono text-gray-800">{assessment.model_version || 'N/A'}</span>
                    {' • '}
                    {assessment.assessed_at ? `Evaluated ${formatDate(assessment.assessed_at)}` : 'Pending evaluation'}
                    {assessment.reviewed_by_name ? ` • Reviewed by ${assessment.reviewed_by_name}` : ''}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Link to="/ai-decision">
                  <Button variant="outline">Inspect Decision Flow</Button>
                </Link>
                <Link to="/fraud">
                  <Button variant="secondary">Fraud Center</Button>
                </Link>
              </div>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Cost Comparison */}
            <div className="lg:col-span-2">
              <ChartCard
                title="Claim Estimate vs AI Prediction"
                subtitle="Side-by-side cost reconciliation against customer filed amount"
              >
                <BarChart data={comparisonData} height={280} />
              </ChartCard>
            </div>

            {/* Cost Breakdown Doughnut */}
            <div>
              <ChartCard
                title="Predicted Cost Composition"
                subtitle="Labor, OEM parts, and refinishing breakdown"
              >
                <DoughnutChart data={costData} height={280} />
              </ChartCard>
            </div>
          </div>

          {/* Detailed Factors Table & Diagnostics */}
          <Card>
            <CardHeader
              title="Inference Contributing Factors"
              subtitle="Feature importance weights computed by the explainable AI assessment pipeline"
            />
            <CardContent className="p-6">
              <div className="space-y-3">
                {factors.length > 0 ? (
                  factors.map((f, idx) => (
                    <div
                      key={idx}
                      className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 hover:bg-gray-50 transition gap-2"
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={clsx(
                            'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold mt-0.5',
                            f.impact === 'positive'
                              ? 'bg-emerald-100 text-emerald-700'
                              : f.impact === 'negative'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-gray-200 text-gray-700'
                          )}
                        >
                          {f.impact === 'positive' ? '✓' : f.impact === 'negative' ? '!' : '•'}
                        </div>
                        <div>
                          <h5 className="font-semibold text-gray-900 text-sm">{f.factor}</h5>
                          <p className="text-xs text-gray-600 mt-0.5">
                            {f.description || 'Feature contribution calculated from claim telemetry and claim history.'}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 justify-end flex-shrink-0">
                        <span className="text-xs font-mono font-medium text-gray-600">
                          Weight: {(f.weight * 100).toFixed(0)}%
                        </span>
                        <Badge
                          variant={
                            f.impact === 'positive' ? 'success' : f.impact === 'negative' ? 'danger' : 'neutral'
                          }
                        >
                          {String(f.impact).toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-400">No contributing factors recorded for this assessment.</p>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

export default AIAssessment
