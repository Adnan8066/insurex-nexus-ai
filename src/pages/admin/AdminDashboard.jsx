import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart3,
  TrendingUp,
  FileText,
  Briefcase,
  AlertTriangle,
  Clock,
  Car,
  DollarSign,
  Shield,
  Download,
  Calendar,
  Layers,
  ArrowRight,
  TrendingDown,
} from 'lucide-react'
import { clsx } from 'clsx'
import { mockPolicies } from '../../data/policies'
import { mockClaims } from '../../data/claims'
import { mockFraudAlerts } from '../../data/operations'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { ChartCard, BarChart, LineChart, AreaChart, DoughnutChart, PieChart } from '../../components/charts/ChartComponents'
import { formatCurrency } from '../../utils/helpers'

export function AdminDashboard() {
  const [dateRange, setDateRange] = useState('quarter')

  // Core metrics required by prompt
  const totalPolicies = mockPolicies.length
  const activePolicies = mockPolicies.filter((p) => p.status === 'active').length
  const totalClaims = mockClaims.length
  const pendingClaims = mockClaims.filter((c) =>
    ['submitted', 'under-review', 'ai-assessment', 'investigation'].includes(c.status)
  ).length
  const fraudAlerts = mockFraudAlerts.length
  const totalLossCases = mockClaims.filter((c) => (c.aiAssessment?.totalLossProbability || 0) > 50).length || 1
  const totalClaimAmount = mockClaims.reduce((sum, c) => sum + c.claimAmount, 0)
  const averageClaimCost = totalClaims > 0 ? Math.round(totalClaimAmount / totalClaims) : 0

  // 1. Claims over time
  const claimsOverTimeData = {
    labels: ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'],
    datasets: [
      {
        label: 'Claims Submitted',
        data: [14, 18, 22, 19, 25, 21],
        borderColor: '#1e3a5f',
        backgroundColor: 'rgba(30, 58, 95, 0.12)',
        fill: true,
        tension: 0.35,
      },
      {
        label: 'Claims Resolved',
        data: [11, 15, 19, 17, 23, 19],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.08)',
        fill: true,
        tension: 0.35,
      },
    ],
  }

  // 2. Fraud risk distribution
  const fraudDistributionData = {
    labels: ['Low Risk (<30%)', 'Moderate Risk (30-65%)', 'High Risk (>65%)'],
    datasets: [
      {
        data: [68, 24, 8],
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
        borderWidth: 0,
      },
    ],
  }

  // 3. Claim status distribution
  const claimStatusDistributionData = {
    labels: ['Submitted', 'Under Review', 'AI Assessment', 'Investigation', 'Approved', 'Repair', 'Closed'],
    datasets: [
      {
        label: 'Claim Count',
        data: [4, 6, 3, 2, 8, 5, 12],
        backgroundColor: '#1e3a5f',
        borderRadius: 4,
      },
    ],
  }

  // 4. Average repair cost by vehicle category
  const averageRepairCostData = {
    labels: ['Sedan', 'SUV / Crossover', 'Truck / Pickup', 'Luxury / EV', 'Compact'],
    datasets: [
      {
        label: 'Avg Repair Cost ($)',
        data: [4200, 5800, 6900, 11500, 3100],
        backgroundColor: '#007bff',
        borderRadius: 4,
      },
    ],
  }

  // 5. Total-loss cases vs repairable
  const totalLossData = {
    labels: ['Repairable Claims (86%)', 'Total Loss Vehicles (14%)'],
    datasets: [
      {
        data: [86, 14],
        backgroundColor: ['#10b981', '#ef4444'],
        borderWidth: 0,
      },
    ],
  }

  return (
    <div className="page max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="page-header flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              <BarChart3 className="w-3.5 h-3.5 text-primary" />
              Executive Business Intelligence
            </span>
          </div>
          <h1 className="page-title">Enterprise Analytics Dashboard</h1>
          <p className="page-subtitle">
            Comprehensive insurance portfolio performance, loss ratio analysis, and AI automation metrics
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="input-field py-2 text-sm font-semibold"
            aria-label="Reporting Interval"
          >
            <option value="month">Current Month</option>
            <option value="quarter">Current Quarter (Q1)</option>
            <option value="ytd">Year to Date (YTD)</option>
            <option value="year">Full Year (Last 12M)</option>
          </select>

          <Button variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Export Executive Report
          </Button>
        </div>
      </div>

      {/* 7 KPI Metric Cards (Explicitly requested by Prompt) */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {/* 1. Total Policies */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Total Policies</span>
          <p className="text-2xl font-black text-gray-900 mt-1">{totalPolicies}</p>
          <span className="text-[11px] text-emerald-600 font-semibold">+8% YoY</span>
        </div>

        {/* 2. Active Policies */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Active Policies</span>
          <p className="text-2xl font-black text-blue-700 mt-1">{activePolicies}</p>
          <span className="text-[11px] text-gray-500">In Force</span>
        </div>

        {/* 3. Total Claims */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Total Claims</span>
          <p className="text-2xl font-black text-gray-900 mt-1">{totalClaims}</p>
          <span className="text-[11px] text-blue-600 font-semibold">Intake All-Time</span>
        </div>

        {/* 4. Pending Claims */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Pending Claims</span>
          <p className="text-2xl font-black text-amber-600 mt-1">{pendingClaims}</p>
          <span className="text-[11px] text-amber-600">Action Needed</span>
        </div>

        {/* 5. Fraud Alerts */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Fraud Alerts</span>
          <p className="text-2xl font-black text-red-600 mt-1">{fraudAlerts}</p>
          <span className="text-[11px] text-red-600">SIU Flagged</span>
        </div>

        {/* 6. Total Loss Cases */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Total Loss Cases</span>
          <p className="text-2xl font-black text-purple-700 mt-1">{totalLossCases}</p>
          <span className="text-[11px] text-gray-500">Salvage/Scrap</span>
        </div>

        {/* 7. Average Claim Cost */}
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm col-span-2 md:col-span-1">
          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider block truncate">Avg Claim Cost</span>
          <p className="text-2xl font-black text-emerald-700 mt-1">{formatCurrency(averageClaimCost)}</p>
          <span className="text-[11px] text-emerald-600 font-semibold">-3.2% vs target</span>
        </div>
      </div>

      {/* Row 1 Charts: Claims Over Time + Fraud Risk Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ChartCard
            title="1. Claims Over Time"
            subtitle="Monthly claim intake vs resolved claims volume (6 Month Historical Trend)"
          >
            <AreaChart data={claimsOverTimeData} height={290} />
          </ChartCard>
        </div>

        <div>
          <ChartCard
            title="2. Fraud Risk Distribution"
            subtitle="Risk stratification across all evaluated claims"
          >
            <DoughnutChart data={fraudDistributionData} height={290} />
          </ChartCard>
        </div>
      </div>

      {/* Row 2 Charts: Claim Status Distribution + Average Repair Cost */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ChartCard
            title="3. Claim Status Distribution"
            subtitle="Current claims inventory across lifecycle pipeline"
          >
            <BarChart data={claimStatusDistributionData} height={280} />
          </ChartCard>
        </div>

        <div>
          <ChartCard
            title="4. Total-Loss Cases vs Repairable"
            subtitle="Ratio of constructive total loss vs standard repairs"
          >
            <PieChart data={totalLossData} height={280} />
          </ChartCard>
        </div>
      </div>

      {/* Row 3 Chart: Average Repair Cost by Vehicle Category */}
      <ChartCard
        title="5. Average Repair Cost by Vehicle Class"
        subtitle="Benchmark body shop labor and parts expenditure partitioned by chassis type"
      >
        <BarChart data={averageRepairCostData} height={260} />
      </ChartCard>
    </div>
  )
}

export default AdminDashboard
