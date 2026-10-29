import { clsx } from 'clsx'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarController,
  BarElement,
  LineController,
  LineElement,
  ArcElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Bar, Chart, Doughnut } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarController,
  BarElement,
  LineController,
  LineElement,
  ArcElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const defaultOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: '#1e293b',
      titleColor: '#ffffff',
      bodyColor: '#ffffff',
      padding: 12,
      cornerRadius: 8,
      displayColors: false,
    },
  },
  interaction: {
    intersect: false,
    mode: 'index',
  },
}

export function ChartCard({
  title,
  subtitle,
  children,
  className = '',
  action,
  loading = false,
  error = null,
}) {
  return (
    <div className={clsx('card flex h-full min-w-0 flex-col', className)}>
      <div className="card-header gap-3">
        <div className="min-w-0">
          <h3 className="card-title">{title}</h3>
          {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      <div className="card-content flex min-w-0 flex-1 flex-col justify-center">
        {loading && (
          <div className="flex items-center justify-center h-64">
            <span className="loading-spinner loading-spinner-lg" />
          </div>
        )}
        {error && (
          <div className="flex items-center justify-center h-64 text-center text-gray-500">
            <p>{error}</p>
          </div>
        )}
        {!loading && !error && children}
      </div>
    </div>
  )
}

export function BarChart({ data, options = {}, height = 300, className = '' }) {
  const chartOptions = {
    ...defaultOptions,
    ...options,
    plugins: {
      ...defaultOptions.plugins,
      ...options.plugins,
      tooltip: { ...defaultOptions.plugins.tooltip, ...options.plugins?.tooltip },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 11 } },
      },
      y: {
        grid: { color: '#e2e8f0' },
        ticks: { color: '#94a3b8', font: { size: 11 }, precision: 0 },
        beginAtZero: true,
      },
      ...options.scales,
    },
  }

  return (
    <div style={{ height }} className={clsx('relative w-full min-w-0', className)}>
      <Bar data={data} options={chartOptions} />
    </div>
  )
}

export function DoughnutChart({ data, options = {}, height = 300, className = '' }) {
  const chartOptions = {
    ...defaultOptions,
    ...options,
    cutout: '70%',
    plugins: {
      ...defaultOptions.plugins,
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
          padding: 16,
          font: { size: 12 },
          color: '#475569',
        },
      },
      ...options.plugins,
      tooltip: { ...defaultOptions.plugins.tooltip, ...options.plugins?.tooltip },
    },
  }

  return (
    <div style={{ height }} className={clsx('relative w-full min-w-0', className)}>
      <Doughnut data={data} options={chartOptions} />
    </div>
  )
}

// Bars and lines on one chart. Give each dataset a `type` and a `yAxisID` of 'y' (left) or 'y1' (right).
export function ComboChart({ data, options = {}, height = 300, className = '' }) {
  const axis = { ticks: { color: '#94a3b8', font: { size: 11 } }, beginAtZero: true }
  const chartOptions = {
    ...defaultOptions,
    ...options,
    plugins: {
      ...defaultOptions.plugins,
      legend: {
        display: true,
        position: 'bottom',
        labels: { usePointStyle: true, padding: 16, font: { size: 12 }, color: '#475569' },
      },
      ...options.plugins,
      tooltip: { ...defaultOptions.plugins.tooltip, displayColors: true, ...options.plugins?.tooltip },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 11 }, maxRotation: 0, autoSkip: true } },
      y: { ...axis, position: 'left', grid: { color: '#e2e8f0' } },
      y1: { ...axis, position: 'right', grid: { drawOnChartArea: false } },
      ...options.scales,
    },
  }

  return (
    <div style={{ height }} className={clsx('relative w-full min-w-0', className)}>
      <Chart type="bar" data={data} options={chartOptions} />
    </div>
  )
}

// Legend rendered as HTML so every category, including zero-count ones, stays visible with its value.
export function ChartLegend({ items, className = '' }) {
  const total = items.reduce((sum, item) => sum + item.value, 0)
  return (
    <ul className={clsx('mt-4 space-y-2 text-sm', className)}>
      {items.map((item) => (
        <li key={item.label} className="flex items-center justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2 text-gray-600">
            <span className="h-3 w-3 shrink-0 rounded-sm" style={{ backgroundColor: item.color }} aria-hidden="true" />
            <span>{item.label}</span>
          </span>
          <span className="shrink-0 font-semibold tabular-nums text-gray-900">
            {item.value}
            <span className="ml-1.5 font-normal text-gray-500">({total ? Math.round((item.value / total) * 100) : 0}%)</span>
          </span>
        </li>
      ))}
    </ul>
  )
}

export default {
  ChartCard,
  BarChart,
  DoughnutChart,
  ComboChart,
  ChartLegend,
}