import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import {
  Brain,
  DollarSign,
  AlertTriangle,
  TrendingDown,
  ShieldCheck,
  CheckCircle2,
  Cpu,
  BarChart3,
  Sparkles,
  Info,
  Layers,
  ArrowRight,
  RefreshCw,
  Sliders,
} from 'lucide-react'
import { clsx } from 'clsx'
import { mockClaims } from '../../data/claims'
import { mockAIAssessments } from '../../data/ai'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge, StatusBadge } from '../../components/ui/Badge'
import { ChartCard, BarChart, DoughnutChart } from '../../components/charts/ChartComponents'
import { formatCurrency, formatDate } from '../../utils/helpers'

export function AIAssessment() {
  const [searchParams, setSearchParams] = useSearchParams()
  const claimParam = searchParams.get('claim') || 'CLM-2024-001234'

  const [selectedClaimId, setSelectedClaimId] = useState(claimParam)
  const [assessment, setAssessment] = useState(null)
  const [claim, setClaim] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    const targetClaim = mockClaims.find((c) => c.id === selectedClaimId) || mockClaims[0]
    setClaim(targetClaim)
    const aiData = mockAIAssessments[targetClaim.id] || targetClaim.aiAssessment || mockAIAssessments['CLM-2024-001234']
    setAssessment(aiData)
  }, [selectedClaimId])

  const handleSelectClaim = (id) => {
    setSelectedClaimId(id)
    setSearchParams({ claim: id })
  }

  const triggerReAnalysis = () => {
    setAnalyzing(true)
    setTimeout(() => {
      setAnalyzing(false)
    }, 600)
  }

  // Cost breakdown chart data
  const costBreakdown = assessment?.costBreakdown || { parts: 4200, labor: 2800, paint: 1200, other: 0 }
  const costData = {
    labels: ['Parts', 'Labor', 'Paint', 'Other'],
    datasets: [
      {
        data: [costBreakdown.parts, costBreakdown.labor, costBreakdown.paint, costBreakdown.other],
        backgroundColor: ['#1e3a5f', '#007bff', '#00c896', '#94a3b8'],
        borderWidth: 0,
      },
    ],
  }

  // Model comparison bar data
  const comparisonData = {
    labels: ['Customer Estimate', 'AI Predicted Cost', 'Local Market Benchmark'],
    datasets: [
      {
        label: 'Amount ($)',
        data: [
          claim?.claimAmount || 8500,
          assessment?.predictedRepairCost || 8200,
          Math.round((assessment?.predictedRepairCost || 8200) * 0.98),
        ],
        backgroundColor: ['#94a3b8', '#1e3a5f', '#00c896'],
        borderRadius: 6,
      },
    ],
  }

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
            {mockClaims.map((c) => (
              <option key={c.id} value={c.id}>
                {c.claimNumber} - {c.customerName} ({c.incidentType})
              </option>
            ))}
          </select>

          <Button variant="primary" onClick={triggerReAnalysis} loading={analyzing}>
            <RefreshCw className={clsx('w-4 h-4 mr-2', analyzing && 'animate-spin')} />
            Re-run Inference
          </Button>
        </div>
      </div>

      {/* Demo Disclaimer Banner */}
      <div className="bg-gradient-to-r from-blue-50 via-indigo-50 to-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3.5 shadow-sm">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-900">
          <strong className="font-semibold block mb-0.5">Simulated AI / Machine Learning Demo Predictions</strong>
          Predictions below are generated using mock inference outputs modeled after gradient-boosted cost regressors and neural fraud embeddings. Backend Django DRF and ONNX/PyTorch model endpoints will connect directly to this interface.
        </div>
      </div>

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
              {formatCurrency(assessment?.predictedRepairCost || 8500)}
            </div>
            <div className="mt-2 flex items-center text-xs text-gray-600">
              <span className="text-emerald-600 font-semibold mr-1">
                {assessment?.predictedRepairCost < (claim?.claimAmount || 8500) ? '↓' : '↑'}{' '}
                {Math.abs(Math.round(((assessment?.predictedRepairCost - (claim?.claimAmount || 8500)) / (claim?.claimAmount || 8500)) * 100))}%
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
                {assessment?.fraudRiskScore || 23}%
              </span>
              <Badge
                variant={
                  (assessment?.fraudRiskScore || 23) > 60
                    ? 'danger'
                    : (assessment?.fraudRiskScore || 23) > 30
                    ? 'warning'
                    : 'success'
                }
              >
                {(assessment?.fraudRiskScore || 23) > 60
                  ? 'High Risk'
                  : (assessment?.fraudRiskScore || 23) > 30
                  ? 'Moderate Risk'
                  : 'Low Risk'}
              </Badge>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-3 overflow-hidden">
              <div
                className={clsx(
                  'h-2 rounded-full transition-all duration-500',
                  (assessment?.fraudRiskScore || 23) > 60 ? 'bg-red-500' : (assessment?.fraudRiskScore || 23) > 30 ? 'bg-amber-500' : 'bg-emerald-500'
                )}
                style={{ width: `${assessment?.fraudRiskScore || 23}%` }}
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
                {assessment?.totalLossProbability || 5}%
              </span>
              <span className="text-xs text-gray-500">
                {(assessment?.totalLossProbability || 5) > 50 ? 'Constructive Loss' : 'Repairable'}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-3 overflow-hidden">
              <div
                className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${assessment?.totalLossProbability || 5}%` }}
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
              {assessment?.claimPriority || 'Medium'}
            </div>
            <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
              <span>Model Confidence:</span>
              <strong className="text-gray-800">{assessment?.confidence || 87}%</strong>
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
                {assessment?.aiRecommendation || 'Approve with standard processing'}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Model version: <span className="font-mono text-gray-800">{assessment?.modelVersion || 'claim-assessment-v2.3.1'}</span> • Evaluated {formatDate(assessment?.assessedAt || new Date().toISOString())}
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
            subtitle="Side-by-side cost reconciliation against local repair shop benchmarks"
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
            {assessment?.factors?.map((f, idx) => (
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
                    <p className="text-xs text-gray-600 mt-0.5">{f.description || 'Feature contribution calculated from claim telemetry and claim history.'}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 justify-end flex-shrink-0">
                  <span className="text-xs font-mono font-medium text-gray-600">Weight: {(f.weight * 100).toFixed(0)}%</span>
                  <Badge variant={f.impact === 'positive' ? 'success' : f.impact === 'negative' ? 'danger' : 'neutral'}>
                    {f.impact.toUpperCase()}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default AIAssessment
