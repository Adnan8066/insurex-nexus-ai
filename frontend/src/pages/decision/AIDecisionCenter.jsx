import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  GitBranch,
  Brain,
  Shield,
  CheckCircle2,
  Cpu,
  ArrowDown,
  Layers,
  Sparkles,
  Bot,
  Zap,
  Activity,
  Play,
  RotateCcw,
  Check,
  TrendingUp,
  FileCheck,
} from 'lucide-react'
import { clsx } from 'clsx'
import { mockDecisionFlow } from '../../data/ai'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { formatCurrency } from '../../utils/helpers'

export function AIDecisionCenter() {
  const [selectedAgentId, setSelectedAgentId] = useState('claim-agent')
  const [isSimulating, setIsSimulating] = useState(false)
  const [simulationStep, setSimulationStep] = useState(6) // all completed by default

  const flowData = mockDecisionFlow['CLM-2024-001234']
  const agents = flowData.agents

  const handleSimulateFlow = () => {
    setIsSimulating(true)
    setSimulationStep(0)
    let current = 0
    const interval = setInterval(() => {
      current += 1
      setSimulationStep(current)
      if (current >= 6) {
        clearInterval(interval)
        setIsSimulating(false)
      }
    }, 600)
  }

  const selectedAgent = agents.find((a) => a.id === selectedAgentId) || agents[0]

  const flowNodes = [
    { title: '1. Claim Intake', subtitle: 'Raw Claim & Telemetry Ingestion', icon: Activity },
    { title: '2. ML Predictions', subtitle: 'Cost, Fraud & Total Loss Regressors', icon: Cpu },
    { title: '3. AI Multi-Agents', subtitle: '6 Autonomous Specialized Sub-Agents', icon: Bot },
    { title: '4. Decision Engine', subtitle: 'Policy Rules & Threshold Synthesis', icon: GitBranch },
    { title: '5. RL Recommendation', subtitle: 'Trained PPO Triage Optimization', icon: Brain },
    { title: '6. Recommended Action', subtitle: 'Final Executable Adjudication', icon: CheckCircle2 },
  ]

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              Autonomous Agent Orchestration
            </span>
          </div>
          <h1 className="page-title">AI Decision Center</h1>
          <p className="page-subtitle">
            Visual explainability pipeline: Multi-Agent coordination, ML predictions, and Reinforcement Learning adjudication
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            onClick={handleSimulateFlow}
            disabled={isSimulating}
          >
            <Play className={clsx('w-4 h-4 mr-2', isSimulating && 'animate-spin')} />
            {isSimulating ? 'Simulating Pipeline...' : 'Run Decision Simulation'}
          </Button>
          <Link to="/operations">
            <Button variant="outline">
              AI/RL Operations
            </Button>
          </Link>
        </div>
      </div>

      {/* Decision Flow Pipeline Diagram */}
      <Card className="border-2 border-primary/10 overflow-hidden shadow-sm">
        <CardHeader
          title="Complete Decision Flow Architecture"
          subtitle="Real-time progression from raw claim submission down to RL-optimized settlement"
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

      {/* 6 Specialized AI Agents Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Multi-Agent Swarm (6 Specialized Agents)</h2>
            <p className="text-sm text-gray-500">Each agent evaluates a dedicated facet of the insurance claim domain</p>
          </div>
        </div>

        {/* Agent Cards Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          {agents.map((agent) => {
            const isSelected = selectedAgentId === agent.id
            return (
              <button
                key={agent.id}
                type="button"
                onClick={() => setSelectedAgentId(agent.id)}
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
                  <span>{agent.confidence}% conf</span>
                  <span className="font-mono">{agent.processingTime}s</span>
                </div>
              </button>
            )
          })}
        </div>

        {/* Selected Agent Inspector Drawer/Card */}
        <Card className="border-t-4 border-t-primary shadow-sm">
          <CardHeader
            title={`${selectedAgent.name} — Execution Details`}
            subtitle={`Processing Time: ${selectedAgent.processingTime}s • Model Confidence: ${selectedAgent.confidence}%`}
            action={
              <Badge variant="success">Execution Verified</Badge>
            }
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
      </div>

      {/* RL Recommendation & Decision Engine Synthesis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RL Optimization Card */}
        <Card className="border-2 border-emerald-500/20">
          <CardHeader
            title="Reinforcement Learning Recommendation"
            subtitle="Policy Gradient optimization (Reward: +0.87)"
          />
          <CardContent className="p-6 space-y-4">
            <div className="p-4 bg-emerald-50/60 rounded-xl border border-emerald-100">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-emerald-800 uppercase">Recommended Triage Action</span>
                <Badge variant="success">RL Score: {flowData.rlRecommendation.optimizationScore}/100</Badge>
              </div>
              <h3 className="text-lg font-bold text-emerald-950">
                {flowData.rlRecommendation.action}
              </h3>
              <p className="text-xs text-emerald-800 mt-1 leading-relaxed">
                {flowData.rlRecommendation.explanation}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-500 block">Est. Processing Days</span>
                <span className="font-bold text-gray-900 text-sm">{flowData.rlRecommendation.estimatedProcessingDays} Days</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-500 block">Recommended Adjuster</span>
                <span className="font-bold text-gray-900 text-sm">{flowData.rlRecommendation.recommendedAdjuster}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-500 block">Recommended Repair Facility</span>
                <span className="font-bold text-gray-900 text-sm">{flowData.rlRecommendation.recommendedRepairShop}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-500 block">SIU Required?</span>
                <span className="font-bold text-gray-900 text-sm">
                  {flowData.rlRecommendation.investigatorRequired ? 'Yes (SIU Dispatched)' : 'No (Standard Intake)'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Final Decision Engine Card */}
        <Card className="border-2 border-primary/20">
          <CardHeader
            title="Final Decision Engine Output"
            subtitle="Synthesized output for Claim #CLM-2024-001234"
          />
          <CardContent className="p-6 space-y-4">
            <div className="p-4 bg-primary text-white rounded-xl shadow-md">
              <span className="text-xs font-semibold text-white/80 uppercase">Adjudication Outcome</span>
              <div className="text-3xl font-black mt-0.5">{flowData.finalDecision.status}</div>
              <div className="text-sm font-semibold text-emerald-300 mt-1">
                Authorized Payout: {formatCurrency(flowData.finalDecision.amount)}
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-xl text-sm">
              <span className="font-bold text-gray-900 block mb-1">Decision Engine Rationale</span>
              <p className="text-gray-600 leading-relaxed text-xs">
                {flowData.finalDecision.rationale}
              </p>
              <div className="mt-3 pt-3 border-t border-gray-200 text-[11px] text-gray-400 flex items-center justify-between">
                <span>Decided By: {flowData.finalDecision.decidedBy}</span>
                <span>Timestamp: {flowData.finalDecision.decidedAt}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default AIDecisionCenter
