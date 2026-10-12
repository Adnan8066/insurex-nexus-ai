import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Brain,
  Cpu,
  Zap,
  Activity,
  Layers,
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
import { clsx } from 'clsx'
import { mockRLOptimization, mockModelPerformance } from '../../data/ai'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ChartCard, LineChart, BarChart } from '../../components/charts/ChartComponents'

export function AIOperations() {
  const [optimizing, setOptimizing] = useState(false)
  const rlData = mockRLOptimization
  const perf = mockModelPerformance

  const triggerReOptimize = () => {
    setOptimizing(true)
    setTimeout(() => {
      setOptimizing(false)
    }, 700)
  }

  // Reward curve data
  const rewardCurveData = {
    labels: ['Ep 10k', 'Ep 20k', 'Ep 30k', 'Ep 40k', 'Ep 50k'],
    datasets: [
      {
        label: 'Mean Episode Reward',
        data: [0.42, 0.61, 0.73, 0.82, 0.87],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.35,
      },
      {
        label: 'Policy Loss',
        data: [0.48, 0.32, 0.22, 0.15, 0.12],
        borderColor: '#ef4444',
        backgroundColor: 'transparent',
        tension: 0.35,
      },
    ],
  }

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <Zap className="w-3.5 h-3.5 text-emerald-600" />
              Reinforcement Learning Triage Policy
            </span>
          </div>
          <h1 className="page-title">AI & RL Operations Console</h1>
          <p className="page-subtitle">
            Autonomous policy optimization for claim triage, investigator matching, facility allocation, and turnaround minimization
          </p>
        </div>

        <div className="flex gap-2">
          <Button variant="primary" onClick={triggerReOptimize} loading={optimizing}>
            <RefreshCw className={clsx('w-4 h-4 mr-2', optimizing && 'animate-spin')} />
            Run RL Policy Optimizer
          </Button>
          <Link to="/ai-decision">
            <Button variant="outline">
              Decision Center
            </Button>
          </Link>
        </div>
      </div>

      {/* Mandatory Notice */}
      <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3.5 shadow-sm">
        <Info className="w-5 h-5 text-emerald-700 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-emerald-950">
          <strong className="font-semibold block mb-0.5">Simulated Reinforcement Learning (RL) Policy Recommendations</strong>
          These recommendations are produced by our simulated Proximal Policy Optimization (PPO) model trained across 50,000 historical episodes. The actions optimize for minimal turnaround times, high customer retention, and maximum fraud interception.
        </div>
      </div>

      {/* Overall Optimization Score Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-primary text-white p-6 rounded-2xl shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-white/80 uppercase tracking-wider block">Global Optimization Score</span>
            <div className="text-4xl font-black mt-2">{rlData.overallOptimizationScore} / 100</div>
          </div>
          <div className="text-xs text-white/70 mt-4 flex items-center justify-between">
            <span>Model: {rlData.modelVersion}</span>
            <span className="bg-white/20 px-2 py-0.5 rounded">Active PPO</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Claim Triage Queue</span>
            <div className="text-3xl font-black text-gray-900 mt-1">{rlData.claimPrioritization.length} cases</div>
            <span className="text-xs text-emerald-600 font-medium">100% Policy-Alighed</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Investigator Allocation</span>
            <div className="text-3xl font-black text-gray-900 mt-1">{rlData.investigatorAssignment.length} matches</div>
            <span className="text-xs text-gray-500">Based on resolution rates</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <UserCheck className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Avg Turnaround Gain</span>
            <div className="text-3xl font-black text-emerald-600 mt-1">-4.2 Days</div>
            <span className="text-xs text-gray-500">Cycle time reduction</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <TrendingUp className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Grid of the 4 Key Operations Modules (as requested by prompt) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Module 1: Claim Priority Optimization */}
        <Card>
          <CardHeader
            title="1. Claim Priority Optimization"
            subtitle="Automated priority escalation based on fraud indicators and severity"
          />
          <CardContent className="p-6">
            <div className="space-y-3">
              {rlData.claimPrioritization.map((cp, idx) => (
                <div key={idx} className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <Link to={`/claims/${cp.claimId}`} className="font-mono font-bold text-primary hover:underline text-sm">
                      {cp.claimId}
                    </Link>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">Current: {cp.currentPriority}</span>
                      <span className="text-gray-400">→</span>
                      <Badge variant={cp.recommendedPriority === 'Critical' ? 'danger' : cp.recommendedPriority === 'High' ? 'warning' : 'primary'}>
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
              ))}
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
              {rlData.investigatorAssignment.map((ia, idx) => (
                <div key={idx} className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <Link to={`/claims/${ia.claimId}`} className="font-mono font-bold text-primary hover:underline text-sm">
                      {ia.claimId}
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
              ))}
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
              {rlData.repairShopRecommendation.map((rs, idx) => (
                <div key={idx} className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <Link to={`/claims/${rs.claimId}`} className="font-mono font-bold text-primary hover:underline text-sm">
                      {rs.claimId}
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
              ))}
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
              {rlData.processingTimeEstimates.map((pe, idx) => (
                <div key={idx} className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <Link to={`/claims/${pe.claimId}`} className="font-mono font-bold text-primary hover:underline text-sm">
                      {pe.claimId}
                    </Link>
                    <div className="flex items-center gap-1.5 font-bold text-gray-900 text-sm">
                      <Clock className="w-4 h-4 text-primary" />
                      {pe.estimatedDays} Business Days
                    </div>
                  </div>
                  <div className="flex gap-1.5 flex-wrap">
                    {pe.factors.map((f, i) => (
                      <span key={i} className="text-[10px] bg-white border border-gray-200 px-2 py-0.5 rounded text-gray-600">
                        {f}
                      </span>
                    ))}
                  </div>
                  <div className="text-[11px] text-gray-500 pt-1 border-t border-gray-100 flex justify-between">
                    <span>Model Confidence:</span>
                    <strong className="text-gray-800">{pe.confidence}%</strong>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* RL Training Curve & Convergence */}
      <ChartCard
        title="Reinforcement Learning Convergence Curve (PPO Agent)"
        subtitle="Average episode reward versus policy loss across 50k training iterations"
      >
        <LineChart data={rewardCurveData} height={260} />
      </ChartCard>
    </div>
  )
}

export default AIOperations
